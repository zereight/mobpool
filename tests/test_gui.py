from __future__ import annotations

import http.client
import io
import json
from pathlib import Path
import re
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout

from mobpool.claims import write_claim
from mobpool.gui import create_gui_server, serve_gui, validate_bind_host
from mobpool.gui_assets import APP_JS, render_index_html
from mobpool.platforms.base import DeviceInfo
from tests.test_claims import make_cfg
from tests.test_cli import FakeAdapter


class SlowBootAdapter(FakeAdapter):
    def __init__(self, platform: str, devices: list[DeviceInfo], gate: threading.Event) -> None:
        super().__init__(platform, devices)
        self.gate = gate
        self.started = threading.Event()

    def boot_and_slim(self, device_id: str) -> str:
        self.started.set()
        self.gate.wait(timeout=5.0)
        return super().boot_and_slim(device_id)


class CountingAdapter(FakeAdapter):
    def __init__(self, platform: str, devices: list[DeviceInfo]) -> None:
        super().__init__(platform, devices)
        self.list_calls = 0

    def list_available(self) -> list[DeviceInfo]:
        self.list_calls += 1
        return super().list_available()


def _request(
    port: int,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> tuple[int, dict[str, str], bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        req_headers = {"Host": f"127.0.0.1:{port}"}
        if headers:
            req_headers.update(headers)
        conn.request(method, path, body=body, headers=req_headers)
        resp = conn.getresponse()
        raw = resp.read()
        resp_headers = {k.lower(): v for k, v in resp.getheaders()}
        return resp.status, resp_headers, raw
    finally:
        conn.close()


def _wait_job(port: int, job_id: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status, _, raw = _request(port, "GET", f"/api/jobs/{job_id}")
        if status == 200:
            job = json.loads(raw.decode("utf-8"))["job"]
            if job["status"] != "running":
                return job
        time.sleep(0.02)
    raise AssertionError(f"Job {job_id} did not finish within {timeout}s")


class TestGUI(unittest.TestCase):
    def test_app_js_element_ids_exist_in_html(self) -> None:
        html_text = render_index_html("token", "mobpool-gui")
        html_ids = set(re.findall(r'\bid="([^"]+)"', html_text))
        js_ids = set(re.findall(r'getElementById\("([^"]+)"\)', APP_JS))
        self.assertTrue(js_ids)
        self.assertEqual(js_ids - html_ids, set())

    def test_app_js_reads_state_keys_the_server_sends(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = make_cfg(Path(tmp))
            ios = FakeAdapter(
                "ios",
                [DeviceInfo("ios", "SIM-A", "iPhone 17", "Booted", "27.2", runtime_id="SIM-A")],
            )
            write_claim(cfg, "SIM-A", "ios", owner="someone", ttl_sec=600)
            server = create_gui_server(
                cfg,
                adapters={"ios": ios, "android": FakeAdapter("android", [])},
                free_pct_fn=lambda: 70,
                port=0,
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, _, raw = _request(server.actual_port, "GET", "/api/state")
            finally:
                server.shutdown()
                server.server_close()
            self.assertEqual(status, 200)
            state = json.loads(raw.decode("utf-8"))
            self.assertIsInstance(state["in_flight"], list)
            self.assertIsInstance(state["recent_jobs"], list)
            self.assertIn("default_ttl_sec", state["config"])
            owner = {d["device_id"]: d for d in state["devices"]}["SIM-A"]["owner"]
            self.assertIsInstance(owner["expires_in_sec"], int)

        for needed in ("state.in_flight", "recent_jobs", "owner.expires_in_sec", "config.default_ttl_sec"):
            self.assertTrue(needed in APP_JS, f"APP_JS does not read {needed}")
        for stale in ("state.jobs", "owner.remaining_sec"):
            self.assertFalse(stale in APP_JS, f"APP_JS still reads {stale}, which the server never sends")

    def test_validate_bind_host_allows_loopback_only(self) -> None:
        self.assertEqual(validate_bind_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(validate_bind_host("localhost"), "localhost")
        self.assertEqual(validate_bind_host("::1"), "::1")
        with self.assertRaises(ValueError):
            validate_bind_host("0.0.0.0")
        with self.assertRaises(ValueError):
            validate_bind_host("192.168.1.10")

    def test_static_assets_csp_and_security_rejections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = make_cfg(root, owner_label="gui-test")
            adapters = {
                "ios": FakeAdapter("ios", [DeviceInfo("ios", "SIM-1", "iPhone 18 Pro", "Shutdown", "27.2")]),
                "android": FakeAdapter("android", [DeviceInfo("android", "Pixel_9", "Pixel_9", "Shutdown", "Android 15")]),
            }
            server = create_gui_server(cfg, adapters=adapters, free_pct_fn=lambda: 65, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                port = server.actual_port
                token = server.controller.csrf_token
                origin = f"http://127.0.0.1:{port}"

                # Index page embeds CSRF token and strict CSP
                status, headers, raw = _request(port, "GET", "/")
                self.assertEqual(status, 200)
                self.assertIn("default-src 'self'", headers["content-security-policy"])
                self.assertEqual(headers["x-content-type-options"], "nosniff")
                self.assertIn(token, raw.decode("utf-8"))
                html_text = raw.decode("utf-8")
                self.assertIn("Start iOS", html_text)
                self.assertIn("Start Android", html_text)
                self.assertIn("Quick-start", html_text)
                self.assertIn("Other installed devices", html_text)
                self.assertNotIn("settings-panel", html_text)
                self.assertNotIn("onclick=", html_text)

                # CSS & JS assets served cleanly
                status, _, css = _request(port, "GET", "/styles.css")
                self.assertEqual(status, 200)
                self.assertIn("--bg", css.decode("utf-8"))
                status, _, js = _request(port, "GET", "/app.js")
                self.assertEqual(status, 200)
                self.assertIn("X-Mobpool-Token", js.decode("utf-8"))
                status, _, _ = _request(port, "GET", "/favicon.ico")
                self.assertEqual(status, 204)

                # Host header DNS rebinding rejected
                status, _, _ = _request(port, "GET", "/api/state", headers={"Host": "evil.example:8765"})
                self.assertEqual(status, 403)

                # Missing CSRF token rejected
                status, _, _ = _request(
                    port,
                    "POST",
                    "/api/init",
                    headers={"Origin": origin, "Content-Type": "application/json"},
                    body=b'{"platform":"all"}',
                )
                self.assertEqual(status, 403)

                # Wrong Origin rejected
                status, _, _ = _request(
                    port,
                    "POST",
                    "/api/init",
                    headers={
                        "Origin": "http://evil.example",
                        "X-Mobpool-Token": token,
                        "Content-Type": "application/json",
                    },
                    body=b'{"platform":"all"}',
                )
                self.assertEqual(status, 403)

                # Cross-site Sec-Fetch-Site rejected
                status, _, _ = _request(
                    port,
                    "POST",
                    "/api/init",
                    headers={
                        "Origin": origin,
                        "X-Mobpool-Token": token,
                        "Sec-Fetch-Site": "cross-site",
                        "Content-Type": "application/json",
                    },
                    body=b'{"platform":"all"}',
                )
                self.assertEqual(status, 403)

                # Wrong Content-Type rejected (415)
                status, _, _ = _request(
                    port,
                    "POST",
                    "/api/init",
                    headers={
                        "Origin": origin,
                        "X-Mobpool-Token": token,
                        "Content-Type": "text/plain",
                    },
                    body=b'{"platform":"all"}',
                )
                self.assertEqual(status, 415)

                # Invalid JSON rejected (400)
                status, _, _ = _request(
                    port,
                    "POST",
                    "/api/init",
                    headers={
                        "Origin": origin,
                        "X-Mobpool-Token": token,
                        "Content-Type": "application/json",
                    },
                    body=b"{not-json",
                )
                self.assertEqual(status, 400)

                # Unknown job returns 404
                status, _, _ = _request(port, "GET", "/api/jobs/doesnotexist")
                self.assertEqual(status, 404)
            finally:
                server.shutdown()
                server.server_close()

    def test_end_to_end_gui_lifecycle_ownership_and_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Pretend CLI agent owns SIM-FOREIGN in the SAME workspace directory as GUI
            cfg_same_ws = make_cfg(root, owner_label="mobpool-gui", workspace=root / "shared-ws")
            ios = CountingAdapter(
                "ios",
                [
                    DeviceInfo("ios", "SIM-FOREIGN", "iPhone 17", "Booted", "27.2", runtime_id="SIM-FOREIGN"),
                    DeviceInfo("ios", "SIM-POOL", "iPhone 18 Pro", "Shutdown", "27.2"),
                ],
            )
            android = FakeAdapter(
                "android",
                [DeviceInfo("android", "Pixel_9_Bot", "Pixel_9_Bot", "Shutdown", "Android 15")],
            )
            write_claim(cfg_same_ws, "SIM-FOREIGN", "ios", owner="cli-agent", ttl_sec=600)

            server = create_gui_server(
                cfg_same_ws,
                adapters={"ios": ios, "android": android},
                free_pct_fn=lambda: 70,
                port=0,
                cache_ttl_sec=10.0,
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                port = server.actual_port
                auth = {
                    "Origin": f"http://127.0.0.1:{port}",
                    "X-Mobpool-Token": server.controller.csrf_token,
                    "Sec-Fetch-Site": "same-origin",
                    "Content-Type": "application/json",
                }

                # State caches within TTL, refresh=1 bypasses cache
                status, _, raw1 = _request(port, "GET", "/api/state")
                self.assertEqual(status, 200)
                calls_after_first = ios.list_calls
                status, _, _ = _request(port, "GET", "/api/state")
                self.assertEqual(status, 200)
                self.assertEqual(ios.list_calls, calls_after_first)
                status, _, _ = _request(port, "GET", "/api/state?refresh=1")
                self.assertEqual(status, 200)
                self.assertGreater(ios.list_calls, calls_after_first)

                state = json.loads(raw1.decode("utf-8"))
                by_id = {d["device_id"]: d for d in state["devices"]}
                # GUI must NOT treat cli-agent's claim in the same workspace as self
                self.assertFalse(by_id["SIM-FOREIGN"]["owner"]["is_self"])

                # Releasing SIM-FOREIGN without force fails cleanly in async job
                status, _, raw = _request(
                    port,
                    "POST",
                    "/api/release",
                    headers=auth,
                    body=json.dumps({"device_id": "SIM-FOREIGN", "force": False}).encode(),
                )
                self.assertEqual(status, 202)
                job = _wait_job(port, json.loads(raw.decode())["job"]["id"])
                self.assertEqual(job["status"], "failed")
                self.assertTrue(job["data"].get("requires_force"))

                # Slimming booted SIM-FOREIGN without force is also blocked
                status, _, raw = _request(
                    port,
                    "POST",
                    "/api/slim",
                    headers=auth,
                    body=json.dumps({"device_id": "SIM-FOREIGN", "platform": "ios", "force": False}).encode(),
                )
                self.assertEqual(status, 202)
                job = _wait_job(port, json.loads(raw.decode())["job"]["id"])
                self.assertEqual(job["status"], "failed")
                self.assertTrue(job["data"].get("requires_force"))

                # Adding same-workspace CLI claimed device (booted or shutdown) to pool is blocked
                write_claim(cfg_same_ws, "SIM-FOREIGN-OFF", "ios", owner="cli-agent", ttl_sec=600)
                ios.devices["SIM-FOREIGN-OFF"] = DeviceInfo(
                    "ios", "SIM-FOREIGN-OFF", "iPhone 16", "Shutdown", "27.2"
                )
                for foreign_id in ("SIM-FOREIGN", "SIM-FOREIGN-OFF"):
                    status, _, raw = _request(
                        port,
                        "POST",
                        "/api/pool",
                        headers=auth,
                        body=json.dumps(
                            {"platform": "ios", "device_id": foreign_id, "in_pool": True, "prepare": True}
                        ).encode(),
                    )
                    self.assertEqual(status, 202)
                    job = _wait_job(port, json.loads(raw.decode())["job"]["id"])
                    self.assertEqual(job["status"], "failed")
                    self.assertIn("BLOCKED", job["message"])
                self.assertEqual(ios.prepared, [])

                # Add SIM-POOL to pool, then acquire it through GUI
                status, _, raw = _request(
                    port,
                    "POST",
                    "/api/pool",
                    headers=auth,
                    body=json.dumps({"platform": "ios", "device_id": "SIM-POOL", "in_pool": True}).encode(),
                )
                self.assertEqual(status, 202)
                job = _wait_job(port, json.loads(raw.decode())["job"]["id"])
                self.assertEqual(job["status"], "succeeded")

                status, _, raw = _request(
                    port,
                    "POST",
                    "/api/acquire",
                    headers=auth,
                    body=json.dumps({"platform": "ios", "owner": "custom-gui-owner", "ttl_sec": 900}).encode(),
                )
                self.assertEqual(status, 202)
                job = _wait_job(port, json.loads(raw.decode())["job"]["id"])
                self.assertEqual(job["status"], "succeeded")
                self.assertEqual(job["data"]["device_id"], "SIM-POOL")

                # Renew SIM-POOL synchronously
                status, _, raw = _request(
                    port,
                    "POST",
                    "/api/renew",
                    headers=auth,
                    body=json.dumps({"device_id": "SIM-POOL", "ttl_sec": 1800}).encode(),
                )
                self.assertEqual(status, 200)
                self.assertTrue(json.loads(raw.decode())["ok"])

                # GUI remembers custom-gui-owner as self, so release succeeds without force
                status, _, raw = _request(
                    port,
                    "POST",
                    "/api/release",
                    headers=auth,
                    body=json.dumps({"device_id": "SIM-POOL", "keep_apps": True, "force": False}).encode(),
                )
                self.assertEqual(status, 202)
                job = _wait_job(port, json.loads(raw.decode())["job"]["id"])
                self.assertEqual(job["status"], "succeeded")
                self.assertEqual(ios.released, [("SIM-POOL", True)])
            finally:
                server.shutdown()
                server.server_close()

    def test_conflicting_in_flight_job_returns_409(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = make_cfg(root)
            gate = threading.Event()
            ios = SlowBootAdapter(
                "ios",
                [DeviceInfo("ios", "SIM-1", "iPhone 18 Pro", "Shutdown", "27.2")],
                gate,
            )
            adapters = {"ios": ios, "android": FakeAdapter("android", [])}
            server = create_gui_server(cfg, adapters=adapters, free_pct_fn=lambda: 70, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                port = server.actual_port
                auth = {
                    "Origin": f"http://127.0.0.1:{port}",
                    "X-Mobpool-Token": server.controller.csrf_token,
                    "Content-Type": "application/json",
                }
                status, _, raw = _request(
                    port,
                    "POST",
                    "/api/acquire",
                    headers=auth,
                    body=json.dumps({"platform": "ios", "device_id": "SIM-1", "allow_non_pool": True}).encode(),
                )
                self.assertEqual(status, 202)
                job_id = json.loads(raw.decode())["job"]["id"]
                self.assertTrue(ios.started.wait(timeout=3.0))

                # Second overlapping acquire on iOS returns 409 Conflict
                status, _, _ = _request(
                    port,
                    "POST",
                    "/api/acquire",
                    headers=auth,
                    body=json.dumps({"platform": "ios"}).encode(),
                )
                self.assertEqual(status, 409)

                # Release on same device while boot is in flight also returns 409 Conflict
                status, _, _ = _request(
                    port,
                    "POST",
                    "/api/release",
                    headers=auth,
                    body=json.dumps({"device_id": "SIM-1"}).encode(),
                )
                self.assertEqual(status, 409)

                # Pinning a device with prepare=True on the same platform while acquire is running also returns 409
                status, _, _ = _request(
                    port,
                    "POST",
                    "/api/pool",
                    headers=auth,
                    body=json.dumps(
                        {"platform": "ios", "device_id": "SIM-1", "in_pool": True, "prepare": True}
                    ).encode(),
                )
                self.assertEqual(status, 409)

                gate.set()
                job = _wait_job(port, job_id)
                self.assertEqual(job["status"], "succeeded")
            finally:
                gate.set()
                server.shutdown()
                server.server_close()

    def test_serve_gui_rejects_non_loopback_and_port_in_use(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = make_cfg(Path(tmp))
            adapters = {
                "ios": FakeAdapter("ios", []),
                "android": FakeAdapter("android", []),
            }
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = serve_gui(cfg, adapters=adapters, host="0.0.0.0", port=0, open_browser=False)
            self.assertEqual(rc, 2)
            self.assertIn("non-loopback", buf.getvalue())

            # Occupy a port and confirm serve_gui returns exit code 1 cleanly
            holder = create_gui_server(cfg, adapters=adapters, host="127.0.0.1", port=0)
            try:
                buf2 = io.StringIO()
                with redirect_stdout(buf2):
                    rc2 = serve_gui(
                        cfg,
                        adapters=adapters,
                        host="127.0.0.1",
                        port=holder.actual_port,
                        open_browser=False,
                    )
                self.assertEqual(rc2, 1)
                self.assertIn("already in use", buf2.getvalue())
            finally:
                holder.server_close()


if __name__ == "__main__":
    unittest.main()
