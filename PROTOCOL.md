# Versioned Frontier contracts

All integers/floats are little-endian. Runtime timestamps use Windows GetTickCount64. Test files are explicitly isolated and are not game integration. Transactions use zero-wait named mutexes; no unlocked packed-structure races are permitted. An abandoned mutex is released and refused.

## Preserved event bridge

Local\DestinyFrontier_Probe_v1: 192 bytes. Header 32; NMS state 32 at 32; Sunrise state 32 at 64; commands 32 at 96/128; reserved 32. Core/frontier/ipc.py and the NMS event adapter are byte-identical to the confirmed heartbeat-fixed base. Cache continuation is bounded by the original validated Core and peer heartbeat timestamps. New native Sunrise is the sole Sunrise-slot owner. Optional Lua calls read its cached state and never increment native counters or publish heartbeats.

## Spatial V2

Local\DestinyFrontier_Spatial_v2 and matching _mutex. Header `<IIIIQ40x`, 64 bytes: magic 0x53544644, version 2, total 320, header 64, initialization epoch. Slots at 64/192, `<QQIIQ15f36x`, **128 bytes** with natural C++ alignment.

| Field | Offset | Bytes |
|---|---:|---:|
| heartbeat | 0 | 8 |
| incarnation | 8 | 8 |
| sequence | 16 | 4 |
| validity flags | 20 | 4 |
| context | 24 | 8 |
| player position | 32 | 12 |
| camera position | 44 | 12 |
| forward | 56 | 12 |
| up | 68 | 12 |
| right | 80 | 12 |
| reserved | 92 | 36 |

Flags bits 0..4 correspond to those five vectors. Absent fields are zero with the bit clear; finite vectors only. NMS publishes player position and its previously confirmed -matrix.at/up/right orientation; no guessed camera read. Sunrise publishes verified position/camera/forward/up; no guessed right-vector handedness. Native context is a generation; NMS context remains zero until a verified environment identity seam is adopted. Addresses are never sent as context.

The previous V2-labelled package still used spatial wire version/name v1. This canonical build deliberately changes both name and numeric version to v2, preventing same-size stale V1 producers being interpreted as valid. Old and new spatial mods must not both be loaded.

## Native control/result V1

Local\DestinyFrontier_Control_v1, 128 bytes; first/last 64 owned separately. Core format `<IIII5QII`; native format `<4Q4I2Q`.

| Field | Offset |
|---|---:|
| magic 0x43465444 / version 1 / bytes 128 / headerBytes 64 | 0/4/8/12 |
| Core epoch / heartbeat | 16/24 |
| monotonic request ID | 32 |
| expected native incarnation / context | 40/48 |
| opcode / flags | 56/60 |
| native heartbeat / incarnation / context | 64/72/80 |
| acknowledged request ID | 88 |
| native ready / status / leased hover / readinessBits | 96/100/104/108 |
| consumed host incarnation / sequence | 112/120 |

Opcodes: 0 none, 1 hover on, 2 hover off. Status: 0 idle, 1 applied, 2 rejected, 3 lease lost. Flags: bit 0 both peers live, bit 1 Core Scout Link mode. On requires fresh host pose, local Guardian ownership/readiness, matching incarnation/context and matching live Core epoch. Off always permits safe restoration when the Core lease is valid. Unknown opcodes are rejected. Request IDs are monotonic within one Core epoch; expired or context-invalid on requests are never automatically replayed when readiness returns. Send a new F8 pulse or explicit on request to re-arm.

A request acknowledgement means the native lease policy accepted/rejected it; it does not certify that the guest rendered, moved a requested distance, or collided against NMS terrain. Pose and consumed-host fields provide the structured return state for the next movement slice.

The deadline remains 2,000 ms from publication on every dependency. Native expiry additionally uses the oldest Core/bridge/NMS/host-pose timestamp. No arbitrary hysteresis, new sleep or expanded timeout is used.

## Optional native readiness diagnostics

The formerly reserved uint32 at offset 108 is now readinessBits. Total size/version, mapping names, slot ownership, Spatial V2 and every existing field offset remain unchanged. Bit 31 means diagnostics are implemented. Older producers publish zero: Python reports unavailable predicates as null, not false.

| Bit | Meaning |
|---:|---|
| 0 | in_world |
| 1 | component present |
| 2 | owns local Guardian |
| 3 | snapshot present |
| 4 | snapshot position finite (even if absent) |
| 5 | combined Guardian readiness (AND of bits 0..4) |
| 6 | existing hostReady predicate |
| 7 | ownership evaluated (in-world and component present) |
| 31 | diagnostic extension available |

Ownership remains guarded by in-world/component checks; status reports it null when not evaluated. nativeReady remains Guardian combined readiness AND hostReady. Diagnostics do not gate policy or change snapshot lifetime. Native logs predicate changes on the game-thread tick; status publishes the current mask in the normal 100 ms poll. A shorter transition can appear in logs between status samples. Logs use ev=frontier_readiness and include each predicate, context and tick_ms. No grace period or deadline change was added.

## Independent motion V1 channel

Local\DestinyFrontier_Motion_v1 and its _mutex contain 256 bytes: Core header at 0, NMS intent at 64, Core-routed intent at 128, native result at 192. Each section is 64 bytes. Existing Control and Spatial layouts are unchanged. Header <IIIIQQQ24x> is magic 0x4D465444/version1/bytes256/header64/epoch/heartbeat/enabled. Intent <QQQII32x> is heartbeat/incarnation/sequence/key bits/flags. Bits 1,2,4,8,16,32 map forward/back/left/right/sprint/jump; flags3 means armed+foreground. The routed packet retains original source heartbeat; timeout remains 2000ms. Result <QQQQ3fIQQ> is heartbeat/native incarnation/context/sequence/cumulative translated displacement XYZ/valid flag/input scan reads/generation. Only the owning writer changes each section. Epoch, incarnation, context and generation changes rebase results; duplicates produce zero delta, invalid/stale results produce no actuation. Native synthetic key overrides expire under the oldest applicable lease. Results are read through Frontier's host translator under the live Core epoch; Core does not simulate physics.
