# Destiny Frontier — heartbeat stability repair

2026-10-04 UTC (2026-10-03 evening America/New_York). New source package; original archives/attachments remain unchanged. No games launched, DLL compiled, native bridge modified or live service contacted.

## Source provenance and runtime milestone

Inspected every supplied file in DestinyFrontier_Work_Handoff_2026-10-03(1).zip, plus HANDOFF(1).md. After the first guarded dry-run correctly refused the reconstructed NMS adapter hash, the user supplied the actually loaded frontier_nms_probe.py. This corrected package now guards against that exact actual-source SHA-256, preserves its adjacent runtime-validation.json fallback, frontier_pulse.trigger support, nanite hook and exact speed-target/baseline/applied logging, and layers the heartbeat diagnostics/fix on top. Any further mismatch still requires actual source review.

The user's Windows runtime milestone is recorded as VERIFIED: both actual game processes were live; manual NMS-process pulse routed through Core changed visible Sunrise phase 3 to 4; Sunrise region events routed through Core changed NMS GroundWalkSpeed from 4.400000095367432 to 5.5000001192092896 for odd targets and baseline for even targets. This does not independently verify a natural nanite-award event, restart/native-save reconciliation, arbitrary hooks, same-space Guardian integration or gameplay. The new heartbeat fix itself has not been run on Windows/games here.

## Exact timing from supplied source

| Participant | Publication cadence | Qualification |
|---|---|---|
| NMS | update callback, throttled to at least 100 ms between attempts | Successful exchange publishes heartbeat; skipped lock/header failures do not. Frame pauses add delay |
| Sunrise Lua | start/load poll; 500 ms timer restarted after each poll; region-change exchange also attempts publication | Timer is rescheduled, not a guaranteed fixed-rate clock. Skipped locks and scheduler pauses add delay |
| Core | successful critical section publishes heartbeat; loop sleeps 20 ms afterward | SQLite transactions and logging run inside the shared mutex; iteration/hold time was not measured |
| Core adapter check | age >=0 and <2000 ms, nonzero incarnation, ready==1 | At exactly 2000 ms adapter is stale |
| Python client core check | age >=0 and <=2000 ms, valid magic/version/nonzero epoch | At exactly 2000 ms core still passes; this original boundary is retained |
| Sunrise native core check | rejects future heartbeat or age >2000 ms | Same inclusive core boundary |

A roughly 100 ms **effect interruption** does not imply a 100 ms heartbeat gap. In the supplied Python client, a single zero-wait mutex miss returned None. NMS treated that identically to invalid/stale core state and applied target 0. The next successful NMS update, typically >=100 ms later, reapplied the valid target. This mechanism is proven by source and isolated reproduction; the supplied timestamped speed logs alone do not prove every reported episode had this cause. A real >=2 second publication gap or ready/command transition could also produce a short visible interruption on recovery.

## Selected correction

No arbitrary timeout adjustment, extra sleep, retry or new grace interval. Mapping.exchange retains its existing tuple/None API and protocol 1/192-byte native ABI.

- On a successful locked read, validate header, command and the opposite adapter's actual heartbeat/incarnation/ready state. A fresh core cannot keep a stale peer alive via an old live command.
- Cache a LIVE response with the actual core and peer publication timestamps, keyed by role/incarnation.
- Only on a missed mutex acquisition may a cached response be reused, and only while local readiness remains true and the ORIGINAL core age is <=2000 ms and ORIGINAL peer age is <2000 ms. Cached responses and missed polls never refresh timestamps. An already 1500-ms-old peer provides <500 ms of remaining eligibility, not a new two seconds.
- No initial sample, expired/future timestamp, invalid header, explicit live=false or unready peer restores baseline. Invalid command/Win32 errors retain the existing exception and baseline-restoration path. A known disconnect is never debounced.
- Pending sequence/ack publication is deferred until a successful mutex acquisition, with no invented new event or lost counter delta. A cached return is continued application of an earlier validated absolute command, not a newly received command or new heartbeat publication.

Unobservable peer/core exit during lock contention cannot be known instantaneously. Continuation is bounded by last verified heartbeat expiry, as the existing heartbeat detector already is. Do not extend this TEST absolute-setter technique to additive campaign rewards.

## Changes

Production: Core/frontier/ipc.py (bounded cached exchange, peer freshness validation, status/age diagnostics); Core/frontier/probe.py (age/readiness/incarnation/reason in existing adapter-status transition logs); Adapters/NMS/frontier_nms_probe.py (diagnostic transition logs, scoped description/version; pulse and speed logs preserved).

Added Tests/test_liveness.py: 13 deterministic tests, including real file-backed lock contention on a different thread and actual adapter methods compiled with fake engine/framework state, not imported hooks. Added Tests/test_patch_install.py: read-only refusal against disposable fake installation. Added Tools/apply_heartbeat_fix.py: SHA-guarded three-file Python updater with verified source backups. No hook installation, DLL replacement, process launching or build.

Updated README, BUILD, INSTALL, COMPATIBILITY, PROTOCOL, KNOWN_ISSUES, CHANGELOG, DEVELOPMENT_JOURNAL and current test/acceptance records. Historical WINDOWS_FIXES.md is retained and marked as superseded for current evidence. Sunrise .h/.lua, Store, source lock, runtime-validation template and previous tests remain unchanged.

## Validation and limitations

Linux CPython 3.12.14: 47 tests discovered, 45 passed, two native Windows kernel tests skipped. compileall and Python 3.10 grammar parsing pass. ResourceWarning treated as error. New tests cover single/repeated mutex misses, original deadline boundaries, old publication timestamps, no-cache startup, local/peer unready state, role/incarnation isolation, invalid epoch/version/future clock, explicit disconnect, stale command, event publication on recovery, actual adapter speed restoration/recovery, manual pulse and logs. Updater was exercised separately against disposable copies of the supplied handoff, with backups and exact replacement hashes verified.

Skipped: NativeWindowsTests.test_named_mapping_views_and_close and test_real_abandoned_mutex_released_and_refused. They automatically run on Windows; no intentional Windows skip. No native Windows/Python 3.10/game execution of this new repair occurred here. Do not conflate previously runtime-verified bridge actuation with validation of this changed Python code. Actual reason for each old log episode remains unconfirmed.

The native Sunrise binding still collapses a missed poll into connected=false, but Lua does not reset phase for that return. It retains phase and reschedules its timer. Changing it is unnecessary for the NMS speed symptom and would require native rebuild work. Native phase rollback/disconnect semantics are not newly implemented. Long callback stalls and SQLite-held mutex contention remain measurable runtime concerns.

## Install and next Windows checks

Extract DestinyFrontier-heartbeat-fixed.zip into a NEW folder. Do not copy an entire old/full package over your working installation. Run lightweight tests from the new DestinyFrontier folder using ordinary PowerShell:

```powershell
$env:PYTHONPATH = Join-Path $PWD.Path 'Core'
python -m compileall -q Core Adapters Tools Tests
python -m unittest discover -s Tests -v
```

Expected on Windows for this corrected package: 47 discovered, OK, no intentional skips. The user already observed the pre-correction 46-test heartbeat package pass completely on native Windows; the added 47th test statically verifies preservation of the actually loaded adapter's adjacent validation fallback, but this corrected package has not yet been rerun on Windows.

Read INSTALL.md for the guarded dry-run/update commands. Supply the existing Core project root and the ACTUALLY LOADED NMS mod path, not a spare packaged adapter copy. Stop Core and fully close NMS/offline Destiny before applying; do not hot-reload the mod because its baseline must be captured fresh. Only three Python files are replaced, with source backups. No Sunrise rebuild or Lua/header installation is needed. The guarded NMS source hash now matches the actually loaded adapter supplied after the first refusal. A future hash mismatch still means STOP and supply the actual file; there is no force option. Do not delete/migrate existing canonical DB or native saves.

After restart with the same known test setup, reproduce both directions; observe target/speed logs plus Frontier IPC status logs and Core adapter_status reasons. busy_cached should retain a boost. busy_expired, core_stale, peer_stale, peer_not_ready or command_not_live should restore baseline. A single cached miss is not a disconnect. Then orderly-stop Sunrise/test activity and separately Core on disposable test state; confirm baseline restoration at the existing heartbeat expiry (or next eligible NMS update after expiry). Record elapsed timestamps; no new Windows timing claim is made. Do not kill a process while it owns the mutex; abandonment refusal is separately tested.

## Next low-risk same-space feasibility gate

Read-only spatial telemetry: first inspect currently supported source/API seams for position/orientation, world/activity identity and availability on each engine. Add one narrow read-only stream per side only where fields/hooks are verified; do not guess offsets or native coordinate systems. Record axis directions, units, origin behavior, callback/thread/lifetime, update frequency and travel transitions. Validate known controlled movements without writing transforms or teleporting either player. A neutral diagnostics view can compare traces; both engines keep their existing movement/physics authority.

This establishes whether a reliable coordinate/context mapping is feasible. It does not render a Guardian in NMS or demonstrate cross-world collision. Only after that evidence should an isolated camera/transform experiment be designed. No native rebuild is justified until the source inspection shows a necessary missing read seam.
