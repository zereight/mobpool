---
name: mobpool
description: Guardrails and unified pool/lease manager for AI agents using iOS simulators and Android emulators. Use before booting, building to, running on, tapping through, or screenshotting any iOS simulator or Android emulator.
---

# mobpool

Use `mobpool` before booting or shutting down any iOS simulator or Android emulator, so parallel agent sessions do not melt the Mac or kill each other's devices.

## Golden rules

1. **Never boot directly** with `xcrun simctl boot` or raw `emulator -avd`. Always go through `mobpool acquire --platform ios|android`.
2. **Always audit first** (`mobpool audit`) to see if you already own a booted device you can reuse.
3. **Never shut down `[claimed:...]` devices** owned by another session or worktree.
4. **Renew long sessions** with `mobpool renew <id>` before the TTL expires (default 60m).
5. **Release when done** with `mobpool release <id>` (pass `--keep-apps` if you want installed apps preserved).
6. **Use Argent for UI interaction** against the `UDID` (iOS) or `emulator-XXXX` serial (Android) returned by `mobpool acquire`.

## Commands

```bash
mobpool audit                                  # inspect booted devices, RAM/CPU, owners
mobpool preflight --platform ios               # check caps & Mac free memory
mobpool acquire --platform ios --owner <task>  # boot slim pool sim & record TTL lease
mobpool acquire --platform android --owner <task>
mobpool renew <id> --ttl 3600                  # extend lease (heartbeat)
mobpool release <id>                           # clean apps, shut down, unclaim
mobpool owners                                 # list all claimed devices
```
