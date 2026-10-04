# Current runtime milestone and heartbeat repair

The user's supplied 2026-10-03 Windows handoff verifies simultaneous NMS/Sunrise activity and BOTH actuation directions: manual NMS-process pulse -> Core -> visible Sunrise phase 3 to 4; Sunrise region events -> Core -> NMS speed 4.4/5.5. Treat these narrow runtime paths as VERIFIED AVAILABLE on that tested setup. Exact local executable/framework/DLL fingerprints were not supplied as a complete reproducible version envelope; do not generalize to other builds. The NMS source is explicitly a reconstruction, not a reread of the installed file.

| Capability | Classification / evidence |
|---|---|
| Two real game processes and narrow bidirectional event/absolute-state actuation | VERIFIED AVAILABLE: user's runtime handoff |
| Heartbeat contention correction | VERIFIED AVAILABLE in isolated Linux tests; REQUIRES PROTOTYPING on Windows/games |
| Core tests and resource safety | Linux CPython 3.12.14: 47 discovered, 45 pass, two native Windows skips |
| Actual Python 3.10 / Windows repair execution | REQUIRES PROTOTYPING; syntax parsing only here |
| Natural NMS nanite event hook | REQUIRES PROTOTYPING unless separately observed; manual pulse proves NMS-process actuation |
| Persistence across actual both-game restart/native saves | REQUIRES PROTOTYPING; core synthetic restart tests are insufficient |
| Same-space Guardian, movement/collision/rendering/input bridge | REQUIRES PROTOTYPING; NOT VERIFIED |
| Fun persistent playable loop and consumer Windows EXE | CURRENTLY BLOCKED on later integration gates |

No timeout is enlarged, protocol/schema unchanged, native Sunrise header/Lua unchanged. All applicable lightweight tests run on Windows without an intentional skip. Historical research and original unverified statuses follow below as an archived baseline; this table supersedes them ONLY for the narrow runtime milestones and current test results above.

---

# Historical compatibility and feasibility matrix

**Historical pre-runtime baseline.** Still no playable Destiny Frontier configuration or consumer Windows release. The narrow real-game bridge is now verified as stated above; broader compatibility is not established.

## Windows repair validation — 2026-10-03

| Target / check | Evidence | Status |
|---|---|---|
| Windows 11 x64, Python 3.10 | User's intended target; standard-library implementation and Python 3.10 grammar check | REQUIRES PROTOTYPING: no execution here on either Windows or Python 3.10 |
| Linux Python 3.12.14 | 32 lightweight tests: 30 pass, two native Windows tests skipped; compileall passes | VERIFIED AVAILABLE for isolated core tests only |
| Win32 lock abstraction | Fake-API status/error/cleanup tests pass | VERIFIED AVAILABLE as unit-test evidence only; native kernel behavior unverified |
| Windows file-backed test IPC | Reuses native Win32 mutex, isolated name derived from canonical test path; portable subprocess test included | REQUIRES PROTOTYPING on Windows |
| Windows named mapping / mutex | Two native kernel tests included; automatically run on Windows | REQUIRES PROTOTYPING: both skipped on Linux |
| SQLite close/backup/rejection safety | Retained-handle, failure-injection, restart and deletion tests pass on Linux | VERIFIED AVAILABLE under tested Linux environment; Windows file semantics still need execution |
| Sunrise / NMS runtime bridge, hooks, same-space integration | No games, adapters or native build executed in this repair | REQUIRES PROTOTYPING; no capability promotion |

There are **no intentional Windows skips** in the lightweight Python suite. Native Windows tests use private test names and do not access games. Neither platform-abstraction mocks nor fake adapter packets certify game integration. Adapter and upstream lock files are unchanged. Python 3.10 grammar parsing cannot prove Python 3.10 runtime compatibility.

## Historical candidate version envelope

The table below is inherited from the original research package, not a fresh survey of current upstream releases. Its entries are candidates, not tested supported combinations.

| Component | Reviewed candidate / fact | Local runtime result |
|---|---|---|
| Destiny | Steam Windows x64 86657; `86657.20.08.23.1800.d2_rc___release` | Not installed / not run |
| Sunrise | `1da7f7a86cbfbe5c92dc91287594d0ac6c70eb1c` | Native extension prepared; uncompiled |
| SunriseMissions | `f317a32805ea72dac57152a65244e6ae36218e0d` | Source inspection only; upstream marks several scripts untested |
| NMS public release | Hello Games release log: Cosmos 7.05 | No storefront executable/build ID/hash obtained |
| NMSpy | `52e2e55493ddade1d89d3e638491afff995f5631`; 180383.0 | Hook candidate not executed |
| pyMHF | NMSpy declares dependency 0.2.4 | Not installed/run against game |
| MBINCompiler | `0e81c91aa51c78d7aa3e298e9ba7532bd0c7c49c`; source version 7.04.1.3 | No compiled 7.05 asset round trip |
| Sundial / Parhelion | `0bda0c53259df6c528086cb555949c5ef1d3ed6e`; v0.5.2 | Source inspection only |
| Research reference SkyCraft | `bfcaf178524b92c2cdeb88e4ce0f13ef9ded6f32`; protocol 11 | Source inspected; Skyrim/Minecraft not run |
| Original core test baseline | Linux Python 3.12; POSIX test transport | Historical five-test pass; superseded for this repair by the table above |
| Mission Lua contract | Sunrise vendored Lua compiled with g++ | Passed with fake context; not Windows adapter compilation |

Source links, file names and SHA-256 evidence are in RESEARCH.md and Documentation/SOURCE_LOCK.json.

## Capability classification

“Available” below refers only to the scoped evidence named in the last column. A native game's ordinary capability is not evidence our adapter controls it.

| Capability | Classification | Evidence / missing gate |
|---|---|---|
| SkyCraft runs two engines with engine-side bridge | VERIFIED AVAILABLE | Source includes both mods and shared ABI; no local play test |
| Native NMS exploration, terrain, ships, bases, freighters | VERIFIED AVAILABLE | Existing game's systems; integration control not established |
| Sunrise supported offline client/build | VERIFIED AVAILABLE | Official build docs and DLL source |
| Sunrise local service, mission and investment seams | VERIFIED AVAILABLE | Reviewed source modules |
| Sunrise mission phase/timers/region events | VERIFIED AVAILABLE | Lua registrations and HUD source; transport outcome not played |
| Sunrise script opens sockets/files without extension | CURRENTLY BLOCKED | Sandbox excludes host IO and native loaders |
| Narrow native Lua IPC extension | VERIFIED POSSIBLE WITH DEVELOPMENT | Identified sandbox registration seam; candidate header/patch tool supplied |
| Both game processes live simultaneously on user's hardware | REQUIRES PROTOTYPING | Neither game nor Windows/GPU installed here |
| Game liveness while hidden/minimized | REQUIRES PROTOTYPING | Must test pause/update/render behavior separately |
| NMS nanite award observation | REQUIRES PROTOTYPING | NMSpy native hook source exists; executable match and real event not tested |
| NMS walking speed read/control | REQUIRES PROTOTYPING | Global + upstream example exist; layout/lifetime not tested |
| NMS location, gravity, scan hooks | REQUIRES PROTOTYPING | NMSpy examples/declarations; no full version validation |
| Bidirectional event bridge on Windows | REQUIRES PROTOTYPING | Real adapter candidates supplied; Windows backend unrun |
| Core bidirectional transport on isolated Linux backend | VERIFIED AVAILABLE | Portable subprocess test passes with explicitly fake adapter packets; Windows execution outstanding |
| Canonical observation restart/dedup/backups | VERIFIED AVAILABLE | Isolated Linux SQLite tests, including handle ownership; not a full campaign save or Windows validation |
| Restoring both native saves coherently | REQUIRES PROTOTYPING | No native checkpoints/save identity contract implemented |
| Real Guardian movement inside NMS terrain | REQUIRES PROTOTYPING | No verified Tiger external-collision ingestion or player puppet integration |
| Actual Destiny projectiles hit NMS world entities | REQUIRES PROTOTYPING | Collision/target proxy/native damage paths unresolved |
| Actual Destiny enemies inside constructed NMS bases | REQUIRES PROTOTYPING | Entity spawning, AI/navigation/collision + rendering all unresolved |
| Camera/input authority and unified presentation | REQUIRES PROTOTYPING | No cross-engine compositor, transform or input arbitration implementation |
| Complete Sunrise missions/combat progression | REQUIRES PROTOTYPING | Upstream incomplete/untested scripts; no restored progression guarantee |
| Live Guardian item grant triggered by NMS | REQUIRES PROTOTYPING | Investment APIs/fork editor merit work; no validated external grant path |
| Custom equipment recipe/package tool | VERIFIED AVAILABLE | Parhelion existing source; no local runtime validation |
| Arbitrary custom exotic behavior | REQUIRES PROTOTYPING | Existing engine components can be composed; unrestricted semantics not verified |
| Weapon Lab wrapping Parhelion | VERIFIED POSSIBLE WITH DEVELOPMENT | Existing tool/source, subject to compatibility + recipe testing |
| Runtime gear editor reuse | REQUIRES PROTOTYPING | Unofficial fork; merge/version compatibility unresolved |
| MBIN/MXML/static NMS mod authoring | VERIFIED AVAILABLE | MBINCompiler and AMUMSS source; each asset version still must match |
| Static AMUMSS supplies live bidirectional IPC | CURRENTLY BLOCKED | Script processor is not a runtime communication adapter |
| Direct Destiny ship to NMS spacecraft conversion | REQUIRES PROTOTYPING | Assets/rigging/native spacecraft behavior not verified |
| NMS save IO tooling | VERIFIED AVAILABLE | libNOM.io source; candidate save format must independently round trip |
| Using old NoMansSky.API with current public NMS | REQUIRES PROTOTYPING | Reviewed revision from 2023; current compatibility not shown |
| ReNMS as current NMS drop-in | CURRENTLY BLOCKED | README explicitly supports Fractal 4.13, not researched current release |
| Loot/research/base modules/chaos systems | REQUIRES PROTOTYPING | Intentionally deferred until runtime + playable loop gates |
| Full requested admin command set | REQUIRES PROTOTYPING | Commands need per-engine native implementations; no console provided |
| Final one-entry Windows release | CURRENTLY BLOCKED | Depends on real integration/build/game validation absent here |
| Performance minimum/recommended specification | CURRENTLY BLOCKED | Cannot measure two actual games here |

## Explicit incompatible or excluded targets

Live/current Destiny 2 is excluded. Later Destiny builds, console executables, Destiny VR variants and unrelated Sunrise/Dawn forks are not accepted by the pinned patch tool. ReNMS Fractal 4.13 does not establish support for Cosmos. Python 3.14 is not supported by the reviewed NMSpy instructions. The present probe supports a single TEST controller, a single adapter per role and one core; campaign/sandbox operation is not implemented.

## Promotion rule

A configuration becomes supported only after exact storefront/build and executable fingerprints, DLL/mod commits, real read/write observations, repeatability, disconnect/restart behavior, native-save reconciliation and hardware measurements are recorded. A successful byte-pattern search or synthetic packet test alone cannot promote it.
