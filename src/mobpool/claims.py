"""TTL-based ownership leases and external owner detection."""

from __future__ import annotations

from dataclasses import dataclass
import glob
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Callable

from mobpool.config import MobpoolConfig


_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class ClaimRecord:
    device_id: str
    platform: str
    owner: str
    workspace: str
    created_at: float
    updated_at: float
    expires_at: float
    ttl_sec: int

    def remaining_sec(self, now: float | None = None) -> int:
        current = time.time() if now is None else now
        return max(0, int(self.expires_at - current))

    def to_dict(self) -> dict[str, object]:
        return {
            "device_id": self.device_id,
            "platform": self.platform,
            "owner": self.owner,
            "workspace": self.workspace,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "ttl_sec": self.ttl_sec,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ClaimRecord":
        return cls(
            device_id=str(data["device_id"]),
            platform=str(data.get("platform", "unknown")),
            owner=str(data.get("owner", "session")),
            workspace=str(data.get("workspace", "")),
            created_at=float(data.get("created_at", 0.0)),
            updated_at=float(data.get("updated_at", 0.0)),
            expires_at=float(data.get("expires_at", 0.0)),
            ttl_sec=int(data.get("ttl_sec", 0)),
        )


@dataclass(frozen=True)
class OwnerInfo:
    source: str
    label: str
    is_self: bool
    expires_in_sec: int | None = None

    def display(self) -> str:
        suffix = ""
        if self.expires_in_sec is not None:
            mins = max(1, (self.expires_in_sec + 59) // 60)
            suffix += f" ({mins}m left)"
        if self.is_self:
            suffix += " (self)"
        return f"{self.source}:{self.label}{suffix}"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _safe_id(device_id: str) -> str:
    return _SAFE_FILENAME_RE.sub("_", device_id)


def claim_path(cfg: MobpoolConfig, device_id: str) -> Path:
    return cfg.claims_dir / f"{_safe_id(device_id)}.json"


def _default_owner_label(cfg: MobpoolConfig) -> str:
    if cfg.owner_label:
        return cfg.owner_label
    name = cfg.workspace.name.strip()
    return name or "session"


def _workspace_matches(cfg: MobpoolConfig, path_str: str) -> bool:
    if not path_str:
        return False
    try:
        target = Path(path_str).resolve()
    except OSError:
        return False
    current = cfg.workspace
    return current == target or target in current.parents


def _atomic_write_json(target: Path, data: dict[str, object]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, indent=2) + "\n"
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            tmp_path = fh.name
            fh.write(raw)
        os.replace(tmp_path, target)
    except Exception:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


def write_claim(
    cfg: MobpoolConfig,
    device_id: str,
    platform: str,
    owner: str | None = None,
    ttl_sec: int | None = None,
    now: float | None = None,
    workspace: str | None = None,
) -> ClaimRecord:
    current = time.time() if now is None else now
    ttl = cfg.default_ttl_sec if ttl_sec is None else max(60, int(ttl_sec))
    label = (owner or "").strip() or _default_owner_label(cfg)
    resolved_workspace = str(cfg.workspace) if workspace is None else workspace
    record = ClaimRecord(
        device_id=device_id,
        platform=platform,
        owner=label,
        workspace=resolved_workspace,
        created_at=current,
        updated_at=current,
        expires_at=current + ttl,
        ttl_sec=ttl,
    )
    target = claim_path(cfg, device_id)
    _atomic_write_json(target, record.to_dict())
    return record


def read_active_claim(
    cfg: MobpoolConfig,
    device_id: str,
    now: float | None = None,
) -> ClaimRecord | None:
    target = claim_path(cfg, device_id)
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        record = ClaimRecord.from_dict(data)
    except Exception:
        return None
    current = time.time() if now is None else now
    if record.expires_at <= current:
        return None
    return record


def renew_claim(
    cfg: MobpoolConfig,
    device_id: str,
    ttl_sec: int | None = None,
    now: float | None = None,
) -> ClaimRecord | None:
    existing = read_active_claim(cfg, device_id, now=now)
    if existing is None:
        return None
    current = time.time() if now is None else now
    ttl = existing.ttl_sec if ttl_sec is None else max(60, int(ttl_sec))
    updated = ClaimRecord(
        device_id=existing.device_id,
        platform=existing.platform,
        owner=existing.owner,
        workspace=existing.workspace,
        created_at=existing.created_at,
        updated_at=current,
        expires_at=current + ttl,
        ttl_sec=ttl,
    )
    target = claim_path(cfg, device_id)
    _atomic_write_json(target, updated.to_dict())
    return updated


def remove_claim(cfg: MobpoolConfig, device_id: str) -> bool:
    target = claim_path(cfg, device_id)
    try:
        target.unlink()
        return True
    except OSError:
        return False


def prune_expired_claims(cfg: MobpoolConfig, now: float | None = None) -> int:
    if not cfg.claims_dir.is_dir():
        return 0
    current = time.time() if now is None else now
    removed = 0
    for path in cfg.claims_dir.glob("*.json"):
        try:
            record = ClaimRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
        if record.expires_at <= current:
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass
    return removed


def _rb_owner(
    cfg: MobpoolConfig, device_id: str, *, match_workspace: bool = True
) -> OwnerInfo | None:
    if cfg.rb_claims_dir is None:
        return None
    owner_file = cfg.rb_claims_dir / device_id / "owner"
    try:
        owner_path = owner_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not owner_path or not os.path.isdir(owner_path):
        return None
    return OwnerInfo(
        source="rb",
        label=Path(owner_path).name or owner_path,
        is_self=_workspace_matches(cfg, owner_path) if match_workspace else False,
    )


def _legacy_sg_owner(
    cfg: MobpoolConfig, device_id: str, now: float, *, match_workspace: bool = True
) -> OwnerInfo | None:
    path = cfg.legacy_sg_claims_dir / f"{device_id}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    pid = int(data.get("ownerPid", 0) or 0)
    ts = float(data.get("ts", 0.0) or 0.0)
    if not pid or not _pid_alive(pid) or (now - ts) > 86400:
        return None
    workspace = str(data.get("workspace", ""))
    label = f"{Path(workspace).name or 'session'}@{pid}"
    return OwnerInfo(
        source="sg",
        label=label,
        is_self=_workspace_matches(cfg, workspace) if match_workspace else False,
    )


def _legacy_ad_owner(
    cfg: MobpoolConfig, device_id: str, *, match_workspace: bool = True
) -> OwnerInfo | None:
    if not cfg.legacy_ad_claims_dir.is_dir():
        return None
    for raw_path in sorted(glob.glob(str(cfg.legacy_ad_claims_dir / "*.json"))):
        try:
            data = json.loads(Path(raw_path).read_text(encoding="utf-8"))
        except Exception:
            continue
        pid = int(data.get("ownerPid", 0) or 0)
        did = (data.get("device") or {}).get("id")
        if did == device_id and pid and _pid_alive(pid):
            workspace = str(data.get("workspace", ""))
            return OwnerInfo(
                source="agent-device",
                label=Path(workspace).name or "session",
                is_self=_workspace_matches(cfg, workspace) if match_workspace else False,
            )
    return None


def resolve_owner(
    cfg: MobpoolConfig,
    device_id: str,
    app_running_fn: Callable[[str], bool] | None = None,
    now: float | None = None,
    match_workspace: bool = True,
    self_owners: set[str] | None = None,
) -> OwnerInfo | None:
    current = time.time() if now is None else now

    record = read_active_claim(cfg, device_id, now=current)
    if record is not None:
        owner_match = (
            record.owner in self_owners
            if self_owners is not None
            else (bool(cfg.owner_label) and record.owner == cfg.owner_label)
        )
        is_self = owner_match or (
            match_workspace and _workspace_matches(cfg, record.workspace)
        )
        return OwnerInfo(
            source="mobpool",
            label=record.owner,
            is_self=is_self,
            expires_in_sec=record.remaining_sec(current),
        )

    for detector in (
        lambda: _rb_owner(cfg, device_id, match_workspace=match_workspace),
        lambda: _legacy_sg_owner(cfg, device_id, current, match_workspace=match_workspace),
        lambda: _legacy_ad_owner(cfg, device_id, match_workspace=match_workspace),
    ):
        found = detector()
        if found is not None:
            return found

    if cfg.app_id and app_running_fn is not None:
        try:
            if app_running_fn(device_id):
                return OwnerInfo(source="app", label=cfg.app_id, is_self=False)
        except Exception:
            pass

    return None
