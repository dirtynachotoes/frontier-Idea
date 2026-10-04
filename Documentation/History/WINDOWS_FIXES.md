HISTORICAL WINDOWS RESOURCE REPAIR RECORD — current heartbeat results/provenance are in HEARTBEAT_FIXES.md and Documentation/HEARTBEAT_TEST_RESULTS.txt.

# Destiny Frontier — Windows probe repair pass

Date: 2026-10-03. Scope: repair the existing standard-library Python core and isolated tests for the user's Windows 11 x64 / Python 3.10 target. This is a new package; the original archive is unchanged. No Sunrise compilation, game launch, hook installation, game-save modification or change to either installed game was performed.

## Root causes and production fixes

| Failure | Root cause in original source | Repair |
|---|---|---|
| `ModuleNotFoundError: fcntl` and mapped-file cleanup errors | File-backed tests unconditionally selected POSIX flock; partially completed Mapping constructors retained mmap/files | Small platform lock abstraction: existing Win32 mutex strategy for Windows runtime AND file-backed tests; POSIX flock retained conditionally. ExitStack registers each resource immediately, closes mmap before file/mutex, and cleans failed constructors |
| Future schema DB remains open | Store raised after connect without closing its owned connection; tests also treated SQLite transaction contexts as connection ownership | Constructor closes on any initialization exception; Store context manager plus idempotent close; test connections and cursors explicitly closed |
| Backup `.partial` cannot be promoted | `with sqlite3.connect(...)` commits/rolls back but does not close destination handle | SQLite snapshot, FULL sync, commit and quick_check; explicit destination/cursor close before same-directory replacement; failure cleanup after close, errors propagate |
| Windows subprocess test skipped / unsafe signal assumptions | Test was POSIX-specific and used signal-based shutdown | Portable file-backed test uses isolated Win32 mutex on Windows and a unique stop-file marker. Core exposes marker only with explicit test backend; every child is killed if still running, waited and stderr closed during cleanup |
| Setup/shutdown errors leak earlier resources | Core created Store/Mapping/log before cleanup covered every later initialization failure | ExitStack owns all three immediately; reset/log/Mapping failures still close previous resources |

Microsoft documents that WAIT_ABANDONED grants mutex ownership. The wrapper releases that ownership before refusing inconsistent state; WAIT_TIMEOUT alone is an ordinary missed poll. WAIT_FAILED, failed release and failed handle-close are reported. Win32 function argument/results use HANDLE/DWORD/BOOL declarations; GetTickCount64 remains the Windows heartbeat clock.

No third-party dependency was added. No cleanup errors are ignored and no retry sleep is used to conceal leaked handles. Poll sleeps remain only for core scheduling/event polling. Existing active mapping files are not re-truncated, even to the same size, because Windows SetEndOfFile may fail while views exist. Test names derive from the canonical backing path and are separate from the real runtime mapping.

## Exact files changed or added

Production modified: `Core/frontier/ipc.py`, `Core/frontier/store.py`, `Core/frontier/probe.py`.

Tests modified: `Tests/test_probe.py`. Added: `Tests/test_resource_safety.py`, `Tests/test_core_lifecycle.py`.

Documentation modified: `README.md`, `BUILD.md`, `INSTALL.md`, `COMPATIBILITY.md`, `PROTOCOL.md`, `SAVE_FORMAT.md`, `KNOWN_ISSUES.md`, `CHANGELOG.md`, `DEVELOPMENT_JOURNAL.md`, `Documentation/TEST_RESULTS.md`, `Documentation/WINDOWS_ACCEPTANCE.md`, `Documentation/PACKAGE_HASHES.json`.

Added: `WINDOWS_FIXES.md`, `RunLightweightTests.cmd`, `Documentation/WINDOWS_TEST_RESULTS.txt`.

The Sunrise header/Lua candidate, NMS plugin, tools, runtime validation template and source lock are byte-for-byte unchanged. The current package manifest lists actual files and excludes itself from its own hash set.

## Regression coverage

The suite has 32 tests: the original five strengthened tests, 23 resource/lock tests and four core lifecycle tests. Coverage includes future-schema rejection with a retained connection (GC cannot mask leaks), corrupt database refusal/deletion, idempotent Store/Mapping close, commit recovery/deduplication, immediate rename/delete of backup and mapping files, validation of closed destination before promotion, promotion failure, constructor/closing backup failure, refusal of backup inside an active write transaction, invalid IPC headers, wrong backing-file size, mmap construction failure, repeated locking, exception release, contention and shared mapping views.

Core lifecycle injection checks Mapping-constructor failure closes Store; log-open failure closes both; shutdown-reset failure closes Store/Mapping/log; invalid stop-marker usage is rejected before allocating resources. Win32 fake-API tests cover acquisition, timeout, abandonment, create/wait/release/close errors, HANDLE-sized values, Windows backend selection and named-map constructor failure. Native Windows tests cover private named views and real abandoned-mutex handling.

The subprocess test exercises the real core with **explicitly fake packets** in both directions, second-core refusal, orderly restart and forced exit between critical sections, persistence and no duplicate counts. It is not a game test. No original assertion was weakened to obtain green results.

## Results and remaining verification

Linux CPython 3.12.14: compileall passed; 32 tests discovered, **30 passed, two skipped** with ResourceWarning promoted to error. Python 3.10 grammar parsing passed for all Python source; actual Python 3.10 execution was unavailable. Captured output is in Documentation/WINDOWS_TEST_RESULTS.txt.

Skipped here: `NativeWindowsTests.test_named_mapping_views_and_close` and `NativeWindowsTests.test_real_abandoned_mutex_released_and_refused`, because this environment has no native Windows kernel. These tests run automatically on Windows. There are no intentional Windows skips in this suite. The formerly POSIX-only interprocess test now runs on either platform.

**This package has not been executed on native Windows or Python 3.10 here.** Fake Win32 calls establish wrapper behavior only, not kernel/file-sharing semantics. A Windows pass is the next required validation. Sunrise bridge, NMS hooks, two real game-process communication, same-space Guardian integration, gameplay, performance and final Windows release remain unverified.

Protocol version 1, mapping size/name/offsets, schema version 1, WAL and synchronous FULL are preserved. Backups use snapshot API plus closed-handle same-directory replacement. Atomic visibility where supported does not guarantee directory metadata persistence across every power failure. Failed backups still close resources and report errors. There is no new schema migration. Crash leftovers can remain if a process is killed mid-snapshot; no automatic deletion of unknown historical partials is introduced. Native saves are untouched.

A single Mapping is not designed for concurrent thread use or externally retained memoryviews. The probe's existing single-core/single-producer constraints remain. Game adapter lifecycle and hook lifetimes have not been tested. Historical upstream version pins were not re-researched in this repair.

## Exact next commands — ordinary Windows CMD

Extract the NEW archive separately. Assuming Windows Explorer creates the folder matching the new archive name:

```bat
cd /d "C:\Users\Me yo\Downloads\DestinyFrontier-research-probe-windows-fixed\DestinyFrontier"
set PYTHONPATH=%CD%\Core
python -m compileall -q Core Adapters Tools Tests
python -m unittest discover -s Tests -v
```

Change only the first quoted path if your extraction directory differs. The quoted directory handles `Me yo`; `set PYTHONPATH=%CD%\Core` is the requested CMD syntax. `RunLightweightTests.cmd` is an optional equivalent. No administrator rights, Visual Studio, pip install, game processes or heavy build is required.

Record `python --version` and all output. Require compileall success and unittest `OK`; expected on Windows is 32 tests and no intentional skips, but that has not yet been observed. If anything fails, retain the full traceback and stop at this gate.

After that pass, use the **game-free** Windows core IPC checks in Documentation/WINDOWS_ACCEPTANCE.md. Then NMS framework validation, NMS hook validation, and only later revisit the Sunrise bridge. Do not retry Sunrise compilation during this repair; any eventual necessary build should preferably occur away from the gaming PC.

## Primary documentation used for this repair

- Python 3.10 SQLite connection context managers: https://docs.python.org/3.10/library/sqlite3.html#using-the-connection-as-a-context-manager
- Python 3.10 mmap close and backing-file ownership: https://docs.python.org/3.10/library/mmap.html#mmap.mmap.close
- Win32 CreateMutexW: https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createmutexw
- Win32 wait status/abandonment: https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject
- Win32 ReleaseMutex: https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-releasemutex
- Python 3.10 subprocess signal portability: https://docs.python.org/3.10/library/subprocess.html#subprocess.Popen.send_signal
