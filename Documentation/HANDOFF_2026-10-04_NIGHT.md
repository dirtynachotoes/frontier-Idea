# Destiny Frontier: Night Handoff (2026-10-04, ~23:30 ET)

Continues `Destiny_Frontier_Master_Handoff_2026-10-04.md`. Read that first for project goals, paths and rules.

## TL;DR

* **Background Guardian locomotion works.** NMS in front + F9 armed + W held → offline Destiny reads the keys while in the background and the real Guardian walks. Proven: `scan_reads` 0 → 7,000+, measured displacement grows smoothly and stops on release.
* **NMS following the Guardian works for pace but not for height yet.** The current NMS adapter (`f6cb0a1`) is deployed but **untested in-game**. The previous run had correct pace but floated the player straight up. The fix is in `f6cb0a1`.
* Branch: **`focus-lease`** on `dirtynachotoes/frontier-Idea` (main untouched). Installed native build: **`d608985`** (CI run 37254430427, DLL sha256 `24bfd72e…34d5`).

## What changed tonight (commits on `focus-lease`)

| Commit | What |
|---|---|
| `f6610e0` | Native **focus lease** (`Native/frontier_focus.cpp`). While the motion lease is valid, game-image callers get the game window from GetForegroundWindow/GetActiveWindow/GetFocus; game SetCursorPos/ClipCursor are suppressed; deactivation messages are held back. Also adds watchers and launchers (below). |
| `d608985` | Lease start posts the full activation sequence (WM_ACTIVATEAPP/NCACTIVATE/ACTIVATE/SETFOCUS) and logs which activation messages the window gets. **This is what made Destiny read keys in the background.** WM_ACTIVATEAPP alone (`f6610e0`) did not. |
| `b3c23be` | Docs: runtime result recorded in `Documentation/FOCUS_LEASE.md`. |
| `263858e` | NMS adapter: tried writing `cTkHavokCharacterController.mTargetVelocity`. **No effect** (NMS overwrites it), so this approach was abandoned. |
| `3d5c39a` | NMS adapter: closed-loop SetToPosition anchor with a measured offset (offset converged to `(0,-8192,-1024)`, error ≈ 0). |
| `240e1c6` | Removed vertical-velocity feedback (it launched the player up at ~20 m/s). |
| `2a411d3` | **Current (deployed, sha256 prefix `6cd439d2`).** Holds NMS height while armed. Runtime on `f6cb0a1`: NMS adds ~+0.5 m/frame along up after every SetToPosition regardless of placement height, so the lift saturated and walking floated the player. Guardian drives horizontal only; slopes and ledges aren't followed while armed. |
| `f6cb0a1` | Superseded. Learns NMS's ground push-out (~0.5 m/frame) as a bounded "lift" while the Guardian is idle, and follows NMS vertical only while moving. Deployed to `MODS\frontier_spatial_probe.py` (sha256 prefix `e8e22b81`). |

Earlier bugs found:
* The original fall out of the Space Anomaly was caused by the 5ee/handoff adapter. It re-based every frame on the pre-update `mGraphicsMatrix.pos` + `SetToPosition` with zero velocity. That drifts even with zero Guardian motion, because graphics and SetToPosition spaces differ by `(0,-8192,-1024)` plus physics push-out.
* The direction mapping is fine. NMS published `fwd` matches the vanilla walking direction (dot ≈ 1.0).

## How to run a session (canonical root `C:\Users\Me yo\Downloads\DestinyFrontier-research-probe-windows-fixed\DestinyFrontier`)

1. `FrontierSession.cmd`: preflight (refuses a 2nd Core), then Core (`StartGuardianLocomotion.cmd`), plus readiness and motion watchers.
2. Launch `D:\Games\Destiny 2\destiny2.exe`. Load a destination (EDZ Trostland works) and walk 2–3 s once. **Set Destiny to Windowed on the second monitor.** Fullscreen on the same monitor makes Destiny grab the front when the lease posts activation, which also causes the ~2 s NMS freezes.
3. `StartNMS.cmd` (pyMHF `run nmspy` from `.venv-nms` with Core on PYTHONPATH). Load the save and stand on flat ground. NMS menus need the user's mouse (the in-game cursor doesn't follow automation).
4. In NMS: F9 (arm), hold W, release, F9 (disarm).

## Logs and tools

* `Saves\Guardian_Test\Logs\motion-watch-*.jsonl`: host arm/keys, `scan_reads`, Guardian displacement (`Tools/watch_motion.py`).
* `Saves\Guardian_Test\Logs\readiness-watch-*.jsonl`: native readiness bits (`Tools/watch_readiness.py`).
* `Saves\Guardian_Test\Logs\nms-motion.jsonl`: NMS adapter trace every 0.2 s (`step, velocity, before, after, anchor, offset, error, lift`). Previous attempts were rotated to `nms-motion-*-attempt.jsonl`.
* `D:\Games\Destiny 2\Sunrise\logs\sunrise.log`: `ev=frontier_readiness`, `ev=frontier_focus` (key_calls, fg answered/calls, posted, swallowed), `ev=frontier_focus_msgs`. Enabled via `Sunrise\settings.json` (`file_sink=true`, `client=info`). The original is saved as `settings.json.before-frontier-diag`.
* `CheckRunning.cmd` writes running Frontier/game processes to `Saves\Guardian_Test\Logs\running.txt`.
* Installer receipts and backups: `Backups\native-guest-3095d51c…` (f6610e0 install), `Backups\native-guest-0fff1d0d…` (d608985 install). The old teleport adapter is in `Backups\frontier_spatial_probe.py.teleport-version` and `MODS\frontier_spatial_probe.py.teleport-version.bak`.

## Build/download path

* CI: `gh workflow run build-sunrise-spatial.yml --ref focus-lease`. The artifact can't be downloaded from the cloud container or the PC sandbox (blob storage is blocked). What worked: get a signed URL via `curl -w '%{redirect_url}' -H "Authorization: Bearer $(gh auth token)" https://api.github.com/repos/dirtynachotoes/frontier-Idea/actions/artifacts/<id>/zip`, open it in the desktop **built-in browser** (approve the blob host once), and it lands in `Downloads`. Verify sha256 against the artifact `digest`, extract to `Downloads\DestinyFrontier-Windows-x64-<sha>`, and run the `InstallFrontier.bat` placed there (exact install command; needs Core, destiny2.exe and NMS closed).
* Python-only adapter changes need no CI. Copy `Adapters/NMS/frontier_spatial_probe.py` to `MODS` and restart NMS. **Use a fresh staged filename when pushing files to the PC.** Re-using a staged path sent a stale cached copy once.

## Open issues (priority order)

1. **Verify `2a411d3` in-game** (height held). Then the real follow-up: find why NMS adds ~0.5 m/frame upward after SetToPosition (likely its fall/ground state reset), so slopes and gravity can come back. Old note on `f6cb0a1`: Expect: idle armed → stays put (lift converges in 1–2 frames). W → walks on the ground at the Guardian's pace and stops on release. Check `nms-motion.jsonl`: `lift` ≈ 0.5, `after-before` ≈ 0 when idle, `error` ≈ 0. If the player still floats, the push-out isn't constant; consider holding vertical fixed while armed (`anchor` vertical never follows) as a fallback.
2. **Destiny inactivity kick** returns the Guardian to orbit ~2 min after landing (seen twice). Sunrise's existing Anti-AFK isn't preventing it; investigate `hooks::inactivity`.
3. **Destiny steals the foreground while the lease posts activation** (fullscreen same monitor). Windowed on a second monitor is the workaround. A proper fix would be suppressing game-caller SetForegroundWindow/SetWindowPos topmost during the lease.
4. **NMS ~2 s freezes** while armed. Likely NMS pausing when it loses focus to Destiny (#3). Re-check after windowed Destiny.
5. Housekeeping: `Documentation/CANDIDATE_HASHES.json` in the installed root no longer matches the hot-copied adapter. Rebuild a candidate once the adapter is accepted. The handoff rule "no foreground spoofing" was knowingly relaxed by the user (option chosen: "Focus override").
6. Some files appeared that this handoff's author didn't write (`WatchSpatial.cmd`, `Tools/watch_spatial.py`, commit `d608985` came from a parallel turn of the same session). They're harmless diagnostics.
