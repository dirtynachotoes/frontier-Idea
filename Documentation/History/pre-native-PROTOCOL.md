# Probe ABI — protocol 1

All integers are little-endian. Windows mapping `Local\DestinyFrontier_Probe_v1`, length **192 bytes**; mutex `<mapping name>_mutex`. Every read/write uses the same mutex. Adapters wait zero milliseconds; skipped polls retry. Abandoned mutex state is rejected and requires restarting the probe. The core rejects a second active core. All participants must run in the same user session at ordinary matching integrity level.

| Offset | Size | Contents / owner |
|---:|---:|---|
| 0 | 32 | Header: magic u32 `0x52465444` (`DTFR`), protocol u32=1, core epoch u64, core heartbeat u64, padding 8; core writes |
| 32 | 32 | NMS state; NMS adapter writes |
| 64 | 32 | Sunrise state; native Sunrise binding writes |
| 96 | 32 | Command to NMS; core writes |
| 128 | 32 | Command to Sunrise; core writes |
| 160 | 32 | Reserved zero region |

Each state: heartbeat u64, adapter incarnation u64, action sequence u32, ready u32, acknowledgement u32, diagnostic detail u32. Incarnation is nonzero and changes with adapter restart; sequence is bounded 0–1,000,000 and monotonic within incarnation. Core persists sequence maxima by `(role,incarnation)` and adds only new deltas. A skipped packet does not lose intervening counter increments while the producer lives.

Each command: target u32, both-participants-live u32, padding 24. Target is the other side's canonical action total modulo 1000. NMS uses parity to choose baseline/1.25× walking speed; Sunrise displays target as test mission phase. It is an absolute setter, not an additive reward command.

Heartbeat clocks: `GetTickCount64` on all Windows participants. Core heartbeat expires at 2 seconds; ready adapter state must be fresher than 2 seconds. Liveness is based on callbacks, not merely process existence. Core polls at approximately 20 ms, NMS at 100 ms and Sunrise at 500 ms. Expected latency is therefore hundreds of milliseconds; no measured in-game latency claim is made.

Acknowledgement means the candidate adapter attempted/applied its local setter. Sunrise stages phase inside a Lua callback transaction, so its receipt ack is not a verified native commit or visual effect. Core currently logs ack at liveness transitions and raw data remains inspectable; full latency/ack tracing is future work.

Core epoch permits reconnect across core restart; mapping retains producer incarnation while a game handle exists. Existing stored observations suppress duplicates. A lost producer process before the core saw a new increment may lose that observation: no durable producer outbox exists. An NMS hook hot reload also starts a new incarnation. Never use this probe protocol for financially meaningful/additive/campaign rewards.

Explicit `--test-file` mode uses file-backed mmap solely for isolated tests. On Windows it uses the same Win32 mutex abstraction as the runtime mapping, with a private `Local\DestinyFrontier_Probe_Test_<SHA256 canonical path>_mutex` name. On POSIX it uses nonblocking flock; fcntl is imported only for that path. All participants must refer to the same canonical test path. Tests must not delete/recreate a backing file while participants hold mappings.

The optional `--test-stop-file <path>` marker permits graceful portable test shutdown and requires `--test-file`. Each test process gets its own marker; production runtime behavior and adapter ABI are unchanged. Kill/restart tests stop the child outside its critical section; separate Windows tests exercise abandoned-mutex refusal. A WAIT_ABANDONED acquisition grants ownership, so the wrapper releases it before refusing potentially inconsistent state. WAIT_FAILED and cleanup errors propagate.

Both isolated backends use intentionally fake packets and never certify Phase 1. Protocol version, real named mapping, offsets, clocks and command semantics remain unchanged.

## Heartbeat repair: unchanged ABI, bounded missed-poll continuation

Windows mapping name/version/192-byte offsets and native C++/Lua are unchanged. Python Mapping.exchange now caches only a validated live tuple, keyed by role/incarnation, with actual core and opposite-role heartbeat timestamps. A missed mutex returns that tuple only before both ORIGINAL deadlines; no cached sample refreshes either timestamp. Known live=false/invalid/stale/unready state clears eligibility and baseline is restored. The client checks peer freshness directly under lock so an old command cannot keep a dead peer live behind a fresh core. The original <2000-ms peer and <=2000-ms core boundaries are preserved.

Mapping.last_exchange is out-of-band Python diagnostic metadata: status, core_age_ms, peer_age_ms. It is not shared-memory data or a new protocol field. NMS logs transitions; Core existing adapter_status logs now include age/readiness/incarnation/reason. busy_cached is continued application of an earlier absolute setter, not a new command observation/heartbeat/event publication.
