# Current heartbeat repair results

Linux CPython 3.12.14: 47 tests discovered, 45 pass, two native Windows kernel tests skipped. compileall, ResourceWarning-as-error suite and Python 3.10 grammar parsing passed. Raw current output: HEARTBEAT_TEST_RESULTS.txt. Windows/Python 3.10 and games were not run for this change.

New liveness tests exercise actual Mapping code, deterministic original heartbeat boundaries, real file-backed mutex contention, and actual NMS adapter methods with explicitly fake engine/framework objects. No game module/loader/hook is imported. Guarded updater refusal and a separate disposable-copy apply/backup check passed. Existing persistence/subprocess/resource tests remain.

User-reported real Windows bidirectional actuation predates this repair and is recorded in HEARTBEAT_FIXES.md; it is separate evidence from these isolated tests. No same-space integration, native-save coherence or final playable release is verified. NativeWindowsTests automatically run on Windows; no intentional Windows skips.
