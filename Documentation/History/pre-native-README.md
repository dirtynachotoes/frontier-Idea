# Destiny Frontier — heartbeat stability repair

The user reports real bidirectional Windows bridge actuation: NMS manual pulse changes Sunrise phase; Sunrise region events change NMS walking speed. Same-space Guardian/NMS integration remains unverified. This package repairs one proven false-disconnect path in the supplied runtime handoff; the repair itself still requires Windows runtime validation. No playable launcher/EXE is provided.

Read HEARTBEAT_FIXES.md for exact intervals, unchanged two-second thresholds, source provenance, implementation and next gate. INSTALL.md provides lightweight checks and a SHA-guarded updater for ONLY the two Core Python files and actually loaded NMS Python adapter. The source reconstruction is compared before replacement. Sunrise native header and active Lua are unchanged; no rebuild is needed.

47 lightweight tests: 45 pass on Linux CPython 3.12.14, two native Windows tests skipped. Those tests run automatically on Windows. Python 3.10 grammar parsing passes; actual Python 3.10/Windows execution is outstanding. Engine stubs and fake packets are clearly isolated from game validation.

Manual frontier_pulse.trigger behavior, nanite-hook declaration, speed logs, protocol 1/192 bytes, schema 1/WAL/FULL and canonical data are preserved. The original input packages remain intact. Historical upstream research/pins are retained, not refreshed. No campaign/native save is redistributed or changed.
