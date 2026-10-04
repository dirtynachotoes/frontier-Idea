# Offline validation checkpoint

Linux CPython 3.12: 60 discovered unit tests, 58 pass and two native-Windows kernel tests skipped. The skips automatically execute on the remote Windows runner; they are not fake Windows success. ResourceWarning is an error. Original heartbeat contention/deadline/resource/persistence tests remain in the suite.

compileall and Python 3.10 grammar checks pass. Pure preflight validates natural 128-byte V2 layout/offsets, 64+64 command ownership, bounded workflow and untouched-base SHA guards. Real Core + explicitly FAKE game endpoints test bidirectional routing, native-request/result plumbing, on/off host target, shutdown and persisted observation totals. These endpoints never claim Guardian/game runtime success.

The small actual C++ protocol/policy harness was compiled and run in the isolated Linux work environment with -std=c++17 -Wall -Wextra -Werror. No Sunrise project was compiled locally. It validates lease expiry at the original two-second budget, peer loss, stale/future commands, no implicit replay, context/player changes, opcode refusal, pending-request rejection during peer loss and region predicate. C++ and Python produce EXACT equal 128-byte spatial and control wire fixtures, including sentinel offsets/reserved bytes.

Guarded installer tests verify closed-file atomic promotion and complete rollback after an injected multi-file failure.

The actual NMS spatial adapter methods were executed against fake player/framework inputs: V2 pose/flags and short-key-edge latching passed. Foreground-only key tests suppress repeats and held keys inherited from another application.

The source-preparation tool applied the complete reviewed patch to a fresh disposable Sunrise checkout at the locked commit and git diff --check passed. Wrong/dirty source is refused. Native source changes still require the ONE full remote Windows compile and one eventual batched runtime acceptance; the older successful spatial compile remains a closed prior fact.

Remote Windows run 37227359793: all 59 tests passed with no skips; native policy and packet fixtures passed; full Sunrise compiled. Artifact audit then found C4129 name escapes, so this is NOT valid integration/release success. Added a regression for all six actual mapping/mutex names and a compiled cross-language names fixture; the correction requires its replacement remote build.
