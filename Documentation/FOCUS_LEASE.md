# Focus lease (2026-10-04)

## Evidence
Runtime session on the 5ee57985 candidate (Core epoch 5211440380451269922, Sunrise incarnation 58050940792829):

* Guardian readiness came up at landing in the EDZ Gulch and stayed up while idle and while Destiny was unfocused (no repeat of the earlier post-ready drop in this session).
* NMS live, host ready, F9 armed, W held in NMS: Core routed `W`, native result `valid=1`, but `scan_reads=0` and displacement `[0,0,0]` for the whole hold (`motion-watch-*.jsonl`).
* With valid motion keys published, every game-image polled read of an authored key is answered and counted. Zero means the backgrounded guest performed no game-image polled key reads at all: Destiny gates its keyboard scan on focus.

This answers the first open locomotion question in GUARDIAN_LOCOMOTION.md: background authored-input scanning does **not** happen by itself.

## Change
`Native/frontier_focus.cpp` (+ one window-procedure line in `Sunrise.patch`):

* Lease = the existing motion lease exactly (`focusLeaseUntil=resultValid?nextKeys.until:0`): host armed with F9, NMS focused, both peers live, fresh heartbeats, bounded expiry even if ticks stop.
* While leased, only callers inside the game image get the game window from `GetForegroundWindow` / `GetActiveWindow` / `GetFocus`; game `SetCursorPos` and non-null `ClipCursor` are not applied to the shared desktop.
* While leased, `WM_ACTIVATEAPP(FALSE)`, `WM_ACTIVATE(WA_INACTIVE)` and `WM_KILLFOCUS` are held back from the game. One `WM_ACTIVATEAPP(TRUE)` is posted at lease start; `WM_ACTIVATEAPP(FALSE)` is posted at lease end unless the game really is in front.
* No `SetForegroundWindow`, `SendInput`, OS-wide injection or new engine signature. Sunrise/ImGui and the OS see real state.
* `ev=frontier_focus` lines (client channel, info) report game call counts per API, answers, held-back messages and total game polled-key calls (`key_calls`) at lease start/end and every 2 s while leased.

## Acceptance
Same as RUNTIME_ACCEPTANCE.md, plus run `FrontierSession.cmd` (Core + readiness + motion watchers) and `StartNMS.cmd`. Success = `scans` rising and nonzero `disp` in the motion watcher while W is held in NMS. If `key_calls` stays flat, the gate is not one of these seams; the `fg/active/focus` counts show which focus APIs the guest actually uses.
