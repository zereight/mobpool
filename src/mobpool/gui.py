"""Zero-dependency local web GUI server for unified iOS & Android management."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import errno
import hmac
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import socket
import threading
import time
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse
import uuid
import webbrowser

from mobpool.config import MobpoolConfig
from mobpool.gui_assets import APP_JS, STYLES_CSS, render_index_html
from mobpool.memory import mac_free_memory_pct
from mobpool.platforms.base import PlatformAdapter
from mobpool.service import (
    ServiceResult,
    acquire_device,
    collect_dashboard_state,
    default_adapters,
    init_pools,
    release_device,
    renew_device,
    set_pool_membership,
    slim_device,
)

ALLOWED_BIND_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
MAX_BODY_BYTES = 65536
CSP_HEADER = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
)


class JobConflictError(RuntimeError):
    """Raised when a conflicting mutating job is already in flight."""


@dataclass
class JobRecord:
    id: str
    action: str
    label: str
    platform: str
    device_id: str
    conflict_keys: tuple[str, ...]
    status: str = "running"
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    message: str = ""
    exit_code: int | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "label": self.label,
            "platform": self.platform,
            "device_id": self.device_id,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "message": self.message,
            "exit_code": self.exit_code,
            "data": self.data,
        }


def validate_bind_host(host: str) -> str:
    cleaned = host.strip()
    if cleaned not in ALLOWED_BIND_HOSTS:
        allowed = ", ".join(sorted(ALLOWED_BIND_HOSTS))
        raise ValueError(
            f"Refusing to bind non-loopback host '{host}'. "
            f"Only loopback hosts are allowed: {allowed}."
        )
    return cleaned


def _format_url_host(host: str) -> str:
    return f"[{host}]" if ":" in host else host


def _allowed_hosts_and_origins(host: str, port: int) -> tuple[frozenset[str], frozenset[str]]:
    if host == "::1":
        hosts = frozenset({f"[::1]:{port}", f"localhost:{port}"})
    else:
        hosts = frozenset({f"127.0.0.1:{port}", f"localhost:{port}"})
    origins = frozenset({f"http://{item}" for item in hosts})
    return hosts, origins


class MobpoolDashboardController:
    """Coordinates single-flight state snapshots, async jobs, and GUI ownership."""

    def __init__(
        self,
        cfg: MobpoolConfig,
        adapters: dict[str, PlatformAdapter] | None = None,
        free_pct_fn: Callable[[], int | None] = mac_free_memory_pct,
        *,
        cache_ttl_sec: float = 3.0,
        csrf_token: str | None = None,
    ) -> None:
        self.cfg = cfg
        self.adapters = adapters or default_adapters(cfg)
        self.free_pct_fn = free_pct_fn
        self.cache_ttl_sec = max(0.0, float(cache_ttl_sec))
        self.csrf_token = csrf_token or secrets.token_urlsafe(32)
        self.default_owner = cfg.owner_label or "mobpool-gui"

        self._state_lock = threading.Lock()
        self._cached_state: dict[str, Any] | None = None
        self._cached_at: float = 0.0
        self._collecting_event: threading.Event | None = None

        self._jobs_lock = threading.Lock()
        self._jobs_by_id: dict[str, JobRecord] = {}
        self._in_flight: dict[str, JobRecord] = {}
        self._recent_jobs: deque[JobRecord] = deque(maxlen=30)
        self._self_owners: set[str] = {self.default_owner}

    def snapshot_self_owners(self) -> set[str]:
        with self._jobs_lock:
            return set(self._self_owners)

    def register_self_owner(self, owner: str) -> None:
        cleaned = owner.strip()
        if not cleaned:
            return
        with self._jobs_lock:
            self._self_owners.add(cleaned)

    def invalidate_cache(self) -> None:
        with self._state_lock:
            self._cached_state = None
            self._cached_at = 0.0

    def get_state(self, force_refresh: bool = False) -> dict[str, Any]:
        while True:
            wait_event: threading.Event | None = None
            is_leader = False
            with self._state_lock:
                now = time.monotonic()
                if (
                    not force_refresh
                    and self._cached_state is not None
                    and (now - self._cached_at) < self.cache_ttl_sec
                ):
                    base = dict(self._cached_state)
                    break
                if self._collecting_event is not None:
                    wait_event = self._collecting_event
                else:
                    self._collecting_event = threading.Event()
                    is_leader = True

            if wait_event is not None:
                wait_event.wait(timeout=30.0)
                force_refresh = False
                continue

            if is_leader:
                try:
                    fresh = collect_dashboard_state(
                        self.cfg,
                        self.adapters,
                        self.free_pct_fn,
                        match_workspace=False,
                        self_owners=self.snapshot_self_owners(),
                    )
                    with self._state_lock:
                        self._cached_state = fresh
                        self._cached_at = time.monotonic()
                        ev = self._collecting_event
                        self._collecting_event = None
                        if ev is not None:
                            ev.set()
                    base = dict(fresh)
                    break
                except Exception:
                    with self._state_lock:
                        ev = self._collecting_event
                        self._collecting_event = None
                        if ev is not None:
                            ev.set()
                    raise

        with self._jobs_lock:
            base["in_flight"] = [job.to_dict() for job in self._in_flight.values()]
            base["recent_jobs"] = [job.to_dict() for job in self._recent_jobs]
            base["gui_owner"] = self.default_owner
        return base

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._jobs_lock:
            job = self._jobs_by_id.get(job_id)
            return job.to_dict() if job is not None else None

    def _has_conflict_locked(self, keys: tuple[str, ...]) -> JobRecord | None:
        key_set = set(keys)
        for running in self._in_flight.values():
            running_keys = set(running.conflict_keys)
            if "global:init" in key_set or "global:init" in running_keys:
                return running
            if key_set & running_keys:
                return running
        return None

    def start_job(
        self,
        *,
        action: str,
        label: str,
        platform: str,
        device_id: str,
        conflict_keys: tuple[str, ...],
        runner: Callable[[], ServiceResult],
        on_success: Callable[[ServiceResult], None] | None = None,
    ) -> dict[str, Any]:
        job = JobRecord(
            id=uuid.uuid4().hex[:12],
            action=action,
            label=label,
            platform=platform,
            device_id=device_id,
            conflict_keys=conflict_keys,
        )
        with self._jobs_lock:
            conflict = self._has_conflict_locked(conflict_keys)
            if conflict is not None:
                raise JobConflictError(
                    f"Another operation is already running: {conflict.label}"
                )
            self._in_flight[job.id] = job
            self._jobs_by_id[job.id] = job
            self._recent_jobs.appendleft(job)

        self.invalidate_cache()

        def _worker() -> None:
            try:
                result = runner()
                if result.ok and on_success is not None:
                    on_success(result)
                with self._jobs_lock:
                    job.status = "succeeded" if result.ok else "failed"
                    job.message = result.message
                    job.exit_code = result.exit_code
                    job.data = dict(result.data)
                    job.finished_at = time.time()
                    self._in_flight.pop(job.id, None)
            except Exception as exc:
                with self._jobs_lock:
                    job.status = "failed"
                    job.message = f"ERROR: {exc}"
                    job.exit_code = 1
                    job.finished_at = time.time()
                    self._in_flight.pop(job.id, None)
            finally:
                self.invalidate_cache()

        thread = threading.Thread(
            target=_worker, name=f"mobpool-job-{job.id}", daemon=True
        )
        thread.start()
        return job.to_dict()

    def record_sync_event(
        self,
        *,
        action: str,
        label: str,
        platform: str,
        device_id: str,
        result: ServiceResult,
    ) -> None:
        now = time.time()
        job = JobRecord(
            id=uuid.uuid4().hex[:12],
            action=action,
            label=label,
            platform=platform,
            device_id=device_id,
            conflict_keys=(),
            status="succeeded" if result.ok else "failed",
            started_at=now,
            finished_at=now,
            message=result.message,
            exit_code=result.exit_code,
            data=dict(result.data),
        )
        with self._jobs_lock:
            self._jobs_by_id[job.id] = job
            self._recent_jobs.appendleft(job)
        self.invalidate_cache()

    def action_acquire(self, payload: dict[str, Any]) -> dict[str, Any]:
        platform = str(payload.get("platform", "")).strip()
        if platform not in ("ios", "android"):
            raise ValueError("platform must be 'ios' or 'android'.")
        device_id_raw = payload.get("device_id")
        device_id = str(device_id_raw).strip() if device_id_raw else None
        allow_non_pool = bool(payload.get("allow_non_pool", False))
        owner_raw = str(payload.get("owner") or "").strip()
        owner = owner_raw or self.default_owner
        ttl_raw = payload.get("ttl_sec")
        ttl_sec: int | None = None
        if ttl_raw is not None and ttl_raw != "":
            if isinstance(ttl_raw, bool) or not isinstance(ttl_raw, int):
                raise ValueError("ttl_sec must be an integer.")
            ttl_sec = max(60, ttl_raw)

        keys = [f"acquire:{platform}"]
        if device_id:
            keys.append(f"device:{device_id}")
        label = (
            f"Boot & Claim {platform} ({device_id})"
            if device_id
            else f"Acquire {platform}"
        )

        def _run() -> ServiceResult:
            return acquire_device(
                self.cfg,
                self.adapters,
                platform=platform,
                ttl_sec=ttl_sec,
                owner=owner,
                free_pct_fn=self.free_pct_fn,
                device_id=device_id,
                allow_non_pool=allow_non_pool,
                match_workspace=False,
                self_owners=self.snapshot_self_owners(),
                claim_workspace="",
            )

        def _on_ok(res: ServiceResult) -> None:
            claimed_owner = str(res.data.get("owner") or owner)
            self.register_self_owner(claimed_owner)

        return self.start_job(
            action="acquire",
            label=label,
            platform=platform,
            device_id=device_id or "",
            conflict_keys=tuple(keys),
            runner=_run,
            on_success=_on_ok,
        )

    def action_renew(self, payload: dict[str, Any]) -> ServiceResult:
        device_id = str(payload.get("device_id") or "").strip()
        if not device_id:
            raise ValueError("device_id is required.")
        ttl_raw = payload.get("ttl_sec")
        ttl_sec: int | None = None
        if ttl_raw is not None and ttl_raw != "":
            if isinstance(ttl_raw, bool) or not isinstance(ttl_raw, int):
                raise ValueError("ttl_sec must be an integer.")
            ttl_sec = max(60, ttl_raw)

        with self._jobs_lock:
            conflict = self._has_conflict_locked((f"device:{device_id}",))
            if conflict is not None:
                raise JobConflictError(
                    f"Another operation is already running: {conflict.label}"
                )

        result = renew_device(self.cfg, self.adapters, device_id, ttl_sec)
        self.record_sync_event(
            action="renew",
            label=f"Renew {device_id}",
            platform="",
            device_id=device_id,
            result=result,
        )
        return result

    def action_release(self, payload: dict[str, Any]) -> dict[str, Any]:
        device_id = str(payload.get("device_id") or "").strip()
        if not device_id:
            raise ValueError("device_id is required.")
        keep_apps = bool(payload.get("keep_apps", False))
        force = bool(payload.get("force", False))
        label = f"{'Force Release' if force else 'Release'} {device_id}"

        return self.start_job(
            action="release",
            label=label,
            platform="",
            device_id=device_id,
            conflict_keys=(f"device:{device_id}",),
            runner=lambda: release_device(
                self.cfg,
                self.adapters,
                device_id,
                keep_apps=keep_apps,
                force=force,
                match_workspace=False,
                self_owners=self.snapshot_self_owners(),
            ),
        )

    def action_slim(self, payload: dict[str, Any]) -> dict[str, Any]:
        device_id = str(payload.get("device_id") or "").strip()
        if not device_id:
            raise ValueError("device_id is required.")
        plat_raw = payload.get("platform")
        platform = str(plat_raw).strip() if plat_raw else None
        if platform is not None and platform not in ("ios", "android"):
            raise ValueError("platform must be 'ios' or 'android'.")
        force = bool(payload.get("force", False))
        label = f"{'Force Slim' if force else 'Slim'} {device_id}"

        return self.start_job(
            action="slim",
            label=label,
            platform=platform or "",
            device_id=device_id,
            conflict_keys=(f"device:{device_id}",),
            runner=lambda: slim_device(
                self.cfg,
                self.adapters,
                device_id,
                platform=platform,
                force=force,
                match_workspace=False,
                self_owners=self.snapshot_self_owners(),
            ),
        )

    def action_pool(self, payload: dict[str, Any]) -> dict[str, Any]:
        platform = str(payload.get("platform") or "").strip()
        if platform not in ("ios", "android"):
            raise ValueError("platform must be 'ios' or 'android'.")
        device_id = str(payload.get("device_id") or "").strip()
        if not device_id:
            raise ValueError("device_id is required.")
        if "in_pool" not in payload or not isinstance(payload["in_pool"], bool):
            raise ValueError("in_pool must be a boolean.")
        in_pool = payload["in_pool"]
        prepare = bool(payload.get("prepare", True))
        label = (
            f"Add {device_id} to {platform} pool"
            if in_pool
            else f"Remove {device_id} from {platform} pool"
        )
        return self.start_job(
            action="pool",
            label=label,
            platform=platform,
            device_id=device_id,
            conflict_keys=(f"device:{device_id}", f"pool:{platform}"),
            runner=lambda: set_pool_membership(
                self.cfg,
                self.adapters,
                platform=platform,
                device_or_runtime_id=device_id,
                in_pool=in_pool,
                prepare=prepare,
            ),
        )

    def action_init(self, payload: dict[str, Any]) -> dict[str, Any]:
        platform = str(payload.get("platform") or "all").strip()
        if platform not in ("ios", "android", "all"):
            raise ValueError("platform must be 'ios', 'android', or 'all'.")
        count_raw = payload.get("count")
        count: int | None = None
        if count_raw is not None and count_raw != "":
            if isinstance(count_raw, bool) or not isinstance(count_raw, int) or count_raw < 1:
                raise ValueError("count must be a positive integer.")
            count = count_raw
        return self.start_job(
            action="init",
            label=f"Init Pool ({platform})",
            platform=platform,
            device_id="",
            conflict_keys=("global:init",),
            runner=lambda: init_pools(
                self.cfg,
                self.adapters,
                platform_sel=platform,
                count=count,
                match_workspace=False,
                self_owners=self.snapshot_self_owners(),
            ),
        )


class MobpoolHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        controller: MobpoolDashboardController,
        bind_host: str,
    ) -> None:
        self.address_family = socket.AF_INET6 if ":" in bind_host else socket.AF_INET
        self.controller = controller
        self.bind_host = bind_host
        super().__init__(server_address, _MobpoolRequestHandler)
        actual_port = int(self.server_address[1])
        self.actual_port = actual_port
        self.allowed_hosts, self.allowed_origins = _allowed_hosts_and_origins(
            bind_host, actual_port
        )
        self.url = f"http://{_format_url_host(bind_host)}:{actual_port}/"


class _MobpoolRequestHandler(BaseHTTPRequestHandler):
    server: MobpoolHTTPServer

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        content_type: str,
        *,
        include_csp: bool = False,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if include_csp:
            self.send_header("Content-Security-Policy", CSP_HEADER)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self._send_bytes(status, raw, "application/json; charset=utf-8")

    def _verify_host(self) -> bool:
        host = (self.headers.get("Host") or "").strip().lower()
        if host not in self.server.allowed_hosts:
            self._send_json(
                HTTPStatus.FORBIDDEN,
                {"error": "Forbidden Host header."},
            )
            return False
        return True

    def _verify_mutation_security(self) -> dict[str, Any] | None:
        if not self._verify_host():
            return None

        token = (self.headers.get("X-Mobpool-Token") or "").strip()
        if not token or not hmac.compare_digest(token, self.server.controller.csrf_token):
            self._send_json(
                HTTPStatus.FORBIDDEN,
                {"error": "Missing or invalid CSRF token."},
            )
            return None

        origin = (self.headers.get("Origin") or "").strip().lower()
        if origin not in self.server.allowed_origins:
            self._send_json(
                HTTPStatus.FORBIDDEN,
                {"error": "Forbidden Origin header."},
            )
            return None

        sec_fetch = (self.headers.get("Sec-Fetch-Site") or "").strip().lower()
        if sec_fetch and sec_fetch != "same-origin":
            self._send_json(
                HTTPStatus.FORBIDDEN,
                {"error": "Cross-site requests are not allowed."},
            )
            return None

        content_type = (self.headers.get("Content-Type") or "").strip().lower()
        if not content_type.startswith("application/json"):
            self._send_json(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                {"error": "Content-Type must be application/json."},
            )
            return None

        raw_len = (self.headers.get("Content-Length") or "").strip()
        if not raw_len:
            length = 0
        else:
            try:
                length = int(raw_len)
            except ValueError:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Invalid Content-Length header."},
                )
                return None
            if length < 0:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Invalid Content-Length header."},
                )
                return None
            if length > MAX_BODY_BYTES:
                self._send_json(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    {"error": f"Request body exceeds {MAX_BODY_BYTES} bytes."},
                )
                return None

        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            parsed = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Request body must be valid JSON."},
            )
            return None
        if not isinstance(parsed, dict):
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Request body must be a JSON object."},
            )
            return None
        return parsed

    def do_GET(self) -> None:
        if not self._verify_host():
            return
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            html_body = render_index_html(
                self.server.controller.csrf_token,
                self.server.controller.default_owner,
            ).encode("utf-8")
            self._send_bytes(
                HTTPStatus.OK,
                html_body,
                "text/html; charset=utf-8",
                include_csp=True,
            )
            return

        if path == "/styles.css":
            self._send_bytes(
                HTTPStatus.OK,
                STYLES_CSS.encode("utf-8"),
                "text/css; charset=utf-8",
            )
            return

        if path == "/app.js":
            self._send_bytes(
                HTTPStatus.OK,
                APP_JS.encode("utf-8"),
                "application/javascript; charset=utf-8",
            )
            return

        if path == "/api/state":
            qs = parse_qs(parsed.query)
            force = qs.get("refresh", ["0"])[0] in ("1", "true", "yes")
            try:
                state = self.server.controller.get_state(force_refresh=force)
            except Exception as exc:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": f"Failed to collect state: {exc}"},
                )
                return
            self._send_json(HTTPStatus.OK, state)
            return

        if path.startswith("/api/jobs/"):
            job_id = path.removeprefix("/api/jobs/").strip()
            job = self.server.controller.get_job(job_id)
            if job is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Job not found."})
                return
            self._send_json(HTTPStatus.OK, {"job": job})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

    def do_POST(self) -> None:
        payload = self._verify_mutation_security()
        if payload is None:
            return
        path = urlparse(self.path).path
        controller = self.server.controller

        try:
            if path == "/api/acquire":
                job = controller.action_acquire(payload)
                self._send_json(HTTPStatus.ACCEPTED, {"job": job})
                return
            if path == "/api/renew":
                result = controller.action_renew(payload)
                status = HTTPStatus.OK if result.ok else HTTPStatus.BAD_REQUEST
                self._send_json(
                    status,
                    {
                        "ok": result.ok,
                        "message": result.message,
                        "data": result.data,
                        **({} if result.ok else {"error": result.message}),
                    },
                )
                return
            if path == "/api/release":
                job = controller.action_release(payload)
                self._send_json(HTTPStatus.ACCEPTED, {"job": job})
                return
            if path == "/api/slim":
                job = controller.action_slim(payload)
                self._send_json(HTTPStatus.ACCEPTED, {"job": job})
                return
            if path == "/api/pool":
                job = controller.action_pool(payload)
                self._send_json(HTTPStatus.ACCEPTED, {"job": job})
                return
            if path == "/api/init":
                job = controller.action_init(payload)
                self._send_json(HTTPStatus.ACCEPTED, {"job": job})
                return
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except JobConflictError as exc:
            self._send_json(HTTPStatus.CONFLICT, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})


def create_gui_server(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter] | None = None,
    free_pct_fn: Callable[[], int | None] = mac_free_memory_pct,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    cache_ttl_sec: float = 3.0,
) -> MobpoolHTTPServer:
    bind_host = validate_bind_host(host)
    if port < 0 or port > 65535:
        raise ValueError("port must be between 0 and 65535.")
    controller = MobpoolDashboardController(
        cfg,
        adapters=adapters,
        free_pct_fn=free_pct_fn,
        cache_ttl_sec=cache_ttl_sec,
    )
    return MobpoolHTTPServer((bind_host, port), controller, bind_host=bind_host)


def serve_gui(
    cfg: MobpoolConfig,
    adapters: dict[str, PlatformAdapter] | None = None,
    free_pct_fn: Callable[[], int | None] = mac_free_memory_pct,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> int:
    try:
        server = create_gui_server(
            cfg,
            adapters=adapters,
            free_pct_fn=free_pct_fn,
            host=host,
            port=port,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            print(
                f"ERROR: port {port} on {host} is already in use. "
                "Try another port (e.g. --port 8766) or --port 0 for an automatic free port."
            )
            return 1
        print(f"ERROR: failed to bind {host}:{port}: {exc}")
        return 1

    print(f"mobpool GUI running at {server.url}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    if open_browser:
        try:
            webbrowser.open(server.url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping mobpool GUI...")
    finally:
        server.server_close()
    return 0
