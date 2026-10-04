# Architecture — experimental baseline

The desired final architecture remains two live original games with in-process adapters and an external core. Current source implements only a small TEST observation/control bridge. There is no claim that IPC embeds either engine in the other.

## Actual probe topology

- Destiny process: original supported client + modified pinned Sunrise DLL + one standalone mission controller. Native `frontier_probe.exchange` exposes bounded shared-memory access to sandboxed Lua.
- NMS process: original locally validated NMS + NMSpy/pyMHF + candidate `DestinyFrontierNMSProbe`. Native hook declarations stay in NMSpy; this code has no copied offsets.
- Core process: Python `frontier.probe`, Windows shared mapping/mutex, canonical SQLite observation store and structured log.

Core does not implement physics. The probe does not transfer player poses, scenery, NPCs or images. It routes monotonic observation counters to idempotent state setters rather than replaying additive rewards. NMS returns to the captured walking-speed baseline if the core/source goes stale while its update callback continues running. Sunrise freezes the last displayed test phase. No server packets are guessed and no native save is edited externally.

## Proposed authority for the target fantasy

| System | Proposed owner | Gate before adoption |
|---|---|---|
| Universe/terrain/weather/flight/building | NMS | Local collision/world IDs can be exported and represented faithfully |
| Guardian weapon/ability/armor/combat semantics | Destiny | Real combat can operate against imported collision/target proxies |
| On-foot movement | Undecided | Choose one controller after terrain/combat feasibility tests |
| NPC AI and navigation | Undecided by entity family | No double physics; target engine must expose usable navigation/collision |
| Displayed camera/input | One selected visible host | One source of truth, focus/pause routing, unified frame/coordinates |
| Cross-game unlocks/research/loot rules | Core | Exactly-once intent accounting + native application reconciliation |
| Native world/account saves | Respective games | Checkpoints/profile identity and backup boundary verified |
| Cross-game durable state | Core | Versioned schema, event history and verified native references |

There is no defensible coordinate conversion constant yet. NMS world-relative/planetary coordinates, large positions, system changes and Destiny activity-region coordinates require measured transforms and rebasing. Copying SkyCraft's 70-units scale is invalid.

## Expansion gates

1. Real two-process event probe, both directions, repeat/restart/disconnect.
2. Separate same-space feasibility probe: export local NMS collision; feed Tiger's player/weapon collision safely; synchronize one real combat target and one camera. Record unsupported hooks explicitly.
3. One NMS discovery → meaningful Guardian change → real combat objective → meaningful NMS capability loop, backed by native save reconciliation.
4. Only then modules for progression, loot, base integration, admin, Weapon Lab and launcher.

A complete renderer bridge is a separate technical project. Do not assume D3D11 Destiny and an NMS renderer can share depth/cameras or faithfully composite transparent projectile/ability effects without investigation. Background FPS reduction must retain authoritative simulation and is a measurement decision, not simply minimizing a window.

## Transport choice

A 192-byte latest-state named mapping with a zero-wait mutex is a provisional choice for this tiny probe. It matches two native/runtime adapters without Lua socket dependencies and avoids allocations while the native mutex is held. It is not a benchmark-proven final gameplay transport. Game callbacks skip a busy mutex; the core retries at 50 Hz. Real Windows contention/latency and CPU cost are unmeasured.

Before increasing traffic, compare shared-state/ring-buffer, named-pipe and localhost socket designs on actual hardware. Rich events require durable IDs/acknowledgements and bounded queues; the current counter protocol cannot carry items, arbitrary abilities or geometry.

## Deliberate limitations

Core validation is not remote authentication. Same-user single-session IPC is assumed. No external network listener exists. Multiple Lua mission VMs must not act as separate producers; use one test controller. Hot-reload, concurrent callbacks, sudden DLL teardown and native pointer lifetimes remain runtime validation gates.
