# mobpool

Unified iOS simulator and Android emulator pool, TTL lease, cap, and slimming manager for AI coding agents.

`mobpool` owns **device lifecycle** (pool selection, concurrency caps, host memory floor, TTL leases, and slim booting) and delegates **UI interaction** to Argent.

## Why

- **One CLI for iOS + Android**: same `init`, `audit`, `preflight`, `acquire`, `renew`, `release`, `owners`, `slim` workflow across `simctl`/`simslim` and `adb`/`emulator`/`avdslim`.
- **TTL + heartbeat leases**: claims survive short-lived agent tool-call subprocesses instead of vanishing when a transient PID exits.
- **External owner awareness**: detects external worktree claims, legacy `sim-guard` / `agent-device` claims, and live app processes so parallel agents never kill each other's devices.
- **Atomic boot lock**: `mkdir`-based lock with stale-lock recovery prevents two agents from racing past the device cap.

## Quick start

```bash
# Initialize iOS and Android pools (skips owned devices)
./bin/mobpool init --platform all

# Check running devices, RAM/CPU, slim status, and leases
./bin/mobpool audit

# Acquire a slim iOS simulator or Android emulator (1h TTL by default)
./bin/mobpool acquire --platform ios --owner my-task
./bin/mobpool acquire --platform android --owner my-task --ttl 1800

# Extend an active lease
./bin/mobpool renew <udid-or-avd-or-serial> --ttl 3600

# Clean up apps, shut down, and release lease
./bin/mobpool release <udid-or-avd-or-serial>
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `MOBPOOL_IOS_CAP` | `2` | Max booted iOS simulators |
| `MOBPOOL_ANDROID_CAP` | `1` | Max booted Android emulators |
| `MOBPOOL_TOTAL_CAP` | `2` | Max booted virtual devices machine-wide |
| `MOBPOOL_MIN_FREE_PCT` | `25` | Minimum macOS free memory % before booting |
| `MOBPOOL_CLAIM_TTL` | `3600` | Default lease duration in seconds |
| `MOBPOOL_OWNER` | workspace basename | Default owner label for leases |
| `MOBPOOL_ANDROID_FLAGS` | `-no-audio -no-boot-anim -gpu host -no-snapshot-save` | Lightweight Android emulator boot flags |
| `SIMSLIM_EXCEPT` | `store,web` | `simslim` categories kept enabled on iOS |
| `MOBPOOL_APP_ID` | unset | Optional bundle/package ID treated as an active owner while running |
| `MOBPOOL_WORKTREE_CLAIMS_DIR` | unset | Optional directory of `<device_id>/owner` worktree claim files |
| `MOBPOOL_FORCE_RELEASE` | `0` | Set `1` to bypass non-self owner block on release |

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
