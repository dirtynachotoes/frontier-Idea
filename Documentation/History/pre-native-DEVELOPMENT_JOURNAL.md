# Development journal / handoff

## Scope and environment

Objective: real offline Sunrise/Destiny systems in real NMS universe, both processes alive; real loop before content expansion. No alternative replacing combat with approximate NMS guns was selected.

Execution environment: Linux scratch workspace, no game files, Windows SDK/compiler, Wine or GPU game-testing setup. Source/network retrieval worked. Real-game experimentation and Windows packaging could not be performed. This is an environment blocker, not proof the game concept is impossible.

## Work and evidence

1. Cloned and inspected current SkyCraft, Sunrise, SunriseMissions, SunriseLauncher, Sundial/Parhelion, NMSpy, NoMansSky.API, ReNMS, MBINCompiler, AMUMSS, libNOM.io, tiger-pkg, Reloaded-II and live gear editor research inputs. Record commits in SOURCE_LOCK.json.
2. Verified source distinction between SkyCraft's draft GPU-texture-sharing design and current mesh/texture export + pixel-readback implementation. Identified collision, proxy and camera/input seams needed beyond IPC.
3. Found Sunrise mission sandbox lacks direct IO/network/native imports. Rejected plain Lua file/socket polling; created a bounded Win32 shared-memory native binding registration instead. Candidate never touches native saves.
4. Chose NMSpy as the freshest inspected NMS hook candidate. Older C# API is from 2023; ReNMS explicitly targets Fractal 4.13. Did not select an old NMS build as if it were current.
5. Implemented a 192-byte absolute-setter/counter TEST probe. NMS positive AwardNanites observations control Sunrise diagnostics phase; Sunrise region events control NMS baseline/1.25x walking speed. No reward self-trigger loop or item library.
6. Implemented separate canonical observation database with transaction-safe delta updates, sequence deduplication, future-schema refusal, corruption refusal and SQLite snapshot backups. This is not a campaign/native-save consistency system.
7. Prepared an isolated pinned Sunrise source checkout with the binding. It was not compiled into a Windows DLL. Initial Lua include wrapper was corrected to match Sunrise's C++ Lua linkage after source review.
8. Source check showed controller paths are generated activity-name directories, not arbitrary files. Install documentation explicitly leaves actual SDK/activity attachment as a runtime gate.
9. Ran five Python tests: persistence restart/dedup/regression/backups, future schema, corruption, ABI/stale-header rejection, and isolated fake-packet bidirectional routing/core singleton/restart/crash recovery. All passed. POSIX mode is explicitly a test backend.
10. Built upstream vendored Lua as C++ on Linux and executed the candidate controller contract using a fake context. Passed. Native Win32 calls, actual Lua sandbox registration and real mission commit were not exercised.
11. Added a local binary/framework validation record gate before NMS hook registration. A hash record is not semantic compatibility proof; manual hook validation remains essential.

## Retrieval failures / corrections

The guessed MetaIdea/AMUMSS repository was unavailable; the maintained HolterPhylo repository was resolved via current documentation. Several indexed GitHub file pages could not be opened through web retrieval; full git source checkouts provided the actual files. No conclusions rely on search snippets where code was available.

## Decisions

- Hold the original two-process vision. No launcher/content expansion while major engine seams are unverified.
- Use existing Sunrise Lua/intents and NMSpy declarations; no guessed addresses/protocol packets/native save layouts.
- Tiny shared memory/mutex probe is provisional, not a measured production IPC selection.
- Explicit TEST-only candidates; no final executable representing partial work as a game.
- A small event probe pass does not unlock Phase 3; add a same-space collision/target/render/input feasibility gate first.

## Next developer actions

1. Obtain Windows test execution with legitimate pinned games. Fingerprint binaries.
2. Build the modified Sunrise DLL; validate sandbox binding and attach TEST controller to a generated activity.
3. Validate NMSpy against the exact NMS binary, including singleton readiness/thread and scene lifetimes.
4. Run WINDOWS_ACCEPTANCE.md without fake packets; capture actual source/target observations, timings and game saves.
5. Diagnose failures at the actual adapter rather than extending the core prematurely.
6. Attempt one collision/target/rendering synchronization interaction preserving native Destiny combat in NMS surroundings. Record required hooks and source-backed limits.
7. If that vision proves blocked, describe the closest feasible alternative and its changed experience concretely before choosing it. Do not silently downgrade to two alternating games.

## Milestones

| Milestone | Result |
|---|---|
| Source feasibility baseline | Delivered, runtime uncertainty explicit |
| Real two-game IPC proof | NOT COMPLETE |
| Canonical isolated observation persistence | Tested; not full native/game persistence proof |
| First playable bidirectional progression loop | NOT STARTED |
| Same-space Guardian/NMS experience | NOT PROVEN |
| Windows x64 playable release | NOT BUILT |

## 2026-10-03 — Windows repair pass

User reported Python 3.10/Windows 11: original compileall succeeded; five tests yielded one pass, three errors, one POSIX-only skip. Root causes confirmed in source: unconditional fcntl on the file test backend, unclosed Store on constructor rejection, and SQLite backup destination transaction context mistaken for connection ownership. User's prior Sunrise compilation exhausted heap/RAM (C1060); no build retry is part of this pass.

Worked on a separate extracted copy. Factored native mutex ownership; selected it for Windows file-backed tests with a private path-derived namespace. Explicit resource cleanup covers partial constructors, locks, backup destinations, source connections, cursors, logs and children. Kept WAL/FULL, snapshot API, closed-handle promotion, original protocol/schema and game adapters. Win32 abandoned acquisition releases ownership before refusal. Windows existing mapping files are never re-truncated. Added marker shutdown only for isolated tests, removing POSIX signal dependency without weakening the restart assertions.

Added retained-handle assertions and lifecycle/Win32 status tests, including two native Windows kernel tests. Linux CPython 3.12.14: 32 discovered, 30 pass, two native tests skipped; compileall and Python 3.10 grammar checks pass. No actual Python 3.10 or Windows execution, no games, hooks or native builds. Mocks and fake packets clearly isolated. Portability audit found fcntl only inside the POSIX lock constructor and no additional POSIX-only APIs affecting the probe. Exact evidence is in WINDOWS_FIXES.md and Documentation/WINDOWS_TEST_RESULTS.txt.

Next: user runs the lightweight CMD workflow on Windows; require all 32 tests with no intentional skips. Then private Windows core IPC validation without games, NMS framework validation, NMS hook validation, and only later Sunrise bridge work. Prefer a separate build machine if a native build eventually remains necessary. Do not promote game integration capabilities from these tests. Preserve original ZIP and new release as separate artifacts.

## 2026-10-04 UTC — heartbeat repair / runtime milestone

Accepted user's Windows bidirectional actuation evidence, scoped to manual NMS pulse->visible phase and region event->live speed. Inspected supplied five-file handoff; NMS reconstruction caveat retained. Identified busy/stale conflation; a single missed mutex reset baseline until next >=100-ms update. Selected original-deadline bounded live-response caching, peer validation and reason/age logging. No timeout adjustment, retries/sleeps, native header/controller change or Sunrise compile. Pending events publish next successful exchange. Added 13 liveness tests and guarded patch refusal test; 46 total (44 Linux passes, two native Windows skips). Actual adapter methods exercised with fake engine state, not hooks. Current raw evidence/report saved. Next Windows guarded deployment/revalidation, then read-only spatial/context telemetry; same-space integration remains unverified.
