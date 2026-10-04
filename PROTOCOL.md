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
| native ready / status / leased hover / reserved | 96/100/104/108 |
| consumed host incarnation / sequence | 112/120 |

Opcodes: 0 none, 1 hover on, 2 hover off. Status: 0 idle, 1 applied, 2 rejected, 3 lease lost. Flags: bit 0 both peers live, bit 1 Core Scout Link mode. On requires fresh host pose, local Guardian ownership/readiness, matching incarnation/context and matching live Core epoch. Off always permits safe restoration when the Core lease is valid. Unknown opcodes are rejected. Request IDs are monotonic within one Core epoch; expired or context-invalid on requests are never automatically replayed when readiness returns. Send a new F8 pulse or explicit on request to re-arm.

A request acknowledgement means the native lease policy accepted/rejected it; it does not certify that the guest rendered, moved a requested distance, or collided against NMS terrain. Pose and consumed-host fields provide the structured return state for the next movement slice.

The deadline remains 2,000 ms from publication on every dependency. Native expiry additionally uses the oldest Core/bridge/NMS/host-pose timestamp. No arbitrary hysteresis, new sleep or expanded timeout is used.
