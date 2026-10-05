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

## Run 2 result (f6610e0) and change
Lease ran 11 times with host W routed and native result valid. `ev=frontier_focus`: `key_calls=2025409` and `fg=0/42853` frozen for every lease, `posted=11`, `swallowed=0`. The guest polls GetForegroundWindow about once per frame and scans keys only while it believes it is active; once deactivated it stops both, so the API answers are never asked. A posted `WM_ACTIVATEAPP(TRUE)` alone did not reactivate it.

Next candidate posts the full Windows activation sequence (`WM_ACTIVATEAPP`, `WM_NCACTIVATE`, `WM_ACTIVATE(WA_ACTIVE)`, `WM_SETFOCUS`) to the subclassed window and its top-level root at lease start (reverse at lease end), and logs `ev=frontier_focus_msgs` with the activation messages the subclassed procedure actually receives.

## Runtime result on d608985 (2026-10-04 22:45 ET)
Core epoch from `probe-5457201421769021220.jsonl`; Sunrise in EDZ Trostland, NMS host live, F9 armed, NMS foreground.

* Lease engaged; the guest received the posted activation (`seen_activate=3`, `last_activate_word=1`) and resumed polling: `fg` answered 119 → 424 and `key_calls` rose ~5k/s while backgrounded.
* Motion watcher: `scan_reads` 0 → 7680 across two W holds; `result valid=1`; measured Guardian displacement grew smoothly (e.g. `[0.39, 13.38, -6.82]`, later `[-2.13, 31.34, -11.93]` in host basis) and **stopped on release**.
* This passes the first open question in GUARDIAN_LOCOMOTION.md (background authored-input scanning) with the focus lease. f6610e0 (WM_ACTIVATEAPP alone) did not.

Not yet accepted: the NMS player was underwater (swim orientation), so smooth on-foot actuation still needs a flat-ground check. Destiny's own inactivity timer returned the Guardian to orbit ~2 min after landing in two sessions, and the NMS adapter heartbeat goes stale for ~2 s every 30–40 s (lease ends/restarts each time). Both are separate follow-ups.
