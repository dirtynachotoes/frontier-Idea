# Phase 0 research — 2026-10-03 UTC / 2026-10-02 US Eastern

## Findings and limits

The requested two-live-process architecture has a real reference implementation in SkyCraft. Both candidate games have modifiable offline/runtime components. **There is no verified Destiny–NMS integration, and no evidence yet that a real Guardian can inhabit NMS terrain with authentic combat.** Source-backed event exchange is a reasonable next experiment, not proof of the ultimate fantasy.

Research used fresh shallow source checkouts, official project documentation and Hello Games' release log. `Documentation/SOURCE_LOCK.json` contains exact commits, URLs and SHA-256 hashes of reviewed files. Hashes describe reviewed upstream files; the separate disposable Sunrise checkout was later patched for this probe. No commercial game files were downloaded or included.

Evidence vocabulary:

- **VERIFIED AVAILABLE**: implementation/documentation exists in the identified upstream revision, or an isolated test explicitly identified here passed. This label never implies we ran a game.
- **VERIFIED POSSIBLE WITH DEVELOPMENT**: bounded engineering using identified source integration points; still not proof of a cross-engine gameplay outcome.
- **REQUIRES PROTOTYPING**: implementation or compatibility requires real binary/game testing.
- **CURRENTLY BLOCKED**: a necessary dependency is unavailable here, or the identified interface does not offer the required operation.

## SkyCraft: current implementation rather than the design proposal

Repository: https://github.com/chasmlol/SkyCraft ; reviewed HEAD `bfcaf178524b92c2cdeb88e4ce0f13ef9ded6f32` (2026-10-01), release identified by commit message as 0.1.2.

The SKSE plugin lives in `skse/`; the Fabric mod lives in `fabric/`. Skyrim remains the visible host; Minecraft runs a real hidden client/integrated world. The README identifies Skyrim AE runtime 1.7.104 as its development/test target and Minecraft 26.3, Fabric Loader 0.19.5+, Java 25 as requirements. These are SkyCraft facts, not Destiny Frontier dependencies.

`protocol/skycraft_protocol.h` is the concrete ABI: magic `0x43594B53`, protocol version **11**, mapping name `Local\\SkyCraft_v1` (the name's suffix is not the current protocol version). The header stores process IDs and heartbeats. It defines state slots protected by sequence counters, collision/input/event/render regions, a water grid and a triple-buffered pixel overlay. `fabric/.../link/Proto.java` mirrors the layout. `skse/src/Link.cpp` creates the Win32 mapping and explicitly handles Windows user/integrity access; `SkyLink.java` opens it with Java's native interop and checks liveness. This is not a generic RPC that automatically turns two engines into one.

The division of responsibility is explicit: Minecraft computes player mechanics; Skyrim supplies its world and NPCs. Implementation files include `skse/src/Collision.cpp`, `Input.cpp`, `Game.cpp`, `WorldRender.cpp`; Fabric has `SkyCollision.java`, `TriCollider.java`, `SkyrimActorEntity.java`, `SkyCombat.java`, `InputBridge.java` and `ProxySync.java`. Collision is injected into Minecraft queries; invisible actor proxies let Minecraft's combat operate on Skyrim actors; the host player/camera become puppets. Input, pause/menu ownership and handoff are also necessary.

**Important implementation/design difference:** `docs/DESIGN.md` is a draft dated 2026-09-29 and discusses GPU texture sharing as a proposed transport. Current `FrameExporter.java` actually stages texture-to-buffer readback and copies completed pixels into shared memory. `WorldExporter.java`/`AvatarExporter.java` export mesh/texture data, and `WorldRender.cpp` draws it in Skyrim. Do not claim the present release is simply two GPU frames sharing textures. These implementation details substantially change portability estimates.

Lessons adopted: one authority per subsystem; coordinate/world identities; engine-side hooks rather than only external IPC; bounded state transfers; heartbeats; restoring ordinary control after disconnect; versioned ABI. SkyCraft's success cannot establish that Tiger supports arbitrary NMS collision, entity proxies or isolated weapon simulation.

## Project Sunrise architecture and build

Repository: https://github.com/stanuwu/Sunrise ; reviewed commit `1da7f7a86cbfbe5c92dc91287594d0ac6c70eb1c` (2026-09-28).

Official build documentation: https://projectsunrise.dev/docs/destiny-2/the-build/ . Target is Windows Steam client **86657**, build string `86657.20.08.23.1800.d2_rc___release`, a pre-Beyond-Light client. Shared depot 1085661 manifest `7180122903232116872`; English depot 1085662 manifest `2210332166360342287`. Current live Destiny is not a target. The documentation explicitly warns that package formats and engine interfaces changed after this era.

Source builds a `steam_api64` DLL, not a standalone replacement Destiny engine. `dllmain.cpp` initializes local Steam-compatible runtime, client hooks, core and an egress guard; `server/` contains local service/transport/activity logic. Do not infer a separate Sunrise server EXE must be launched. The local game process carries multiple Sunrise subsystems; Destiny Frontier Core would be an additional process.

`server/runtime/server_runtime.cpp`, `server/transport/`, `server/bap/` and `server/activity/mission/` supply identifiable adaptation seams. Use their local state/intent APIs; do not invent a public Sunrise HTTP API or feed guessed wire packets to the game. The README advertises destinations, mission scripting, exploration controls and persistent saves, and explicitly calls full progression and many missions incomplete.

`mission_script_lua_sandbox.cpp` permits selected base/string/table/math functions and controlled generated Lua modules. It does **not** open `io`, `os`, networking libraries or native package loaders. A plain Lua script cannot directly connect to our core. This is a verified interface limitation, resolved in the probe candidate with a narrow native binding rather than unlocking arbitrary host IO.

`mission_script_lua_context_api.cpp` exposes activity/player identity, mission phase, timers and domain handles. `mission_script_lua_state_api.cpp` stages phase changes in the callback candidate. `mission_script_vm.cpp` recognizes `on_event_region_changed` and timer handlers. `ui_hud_mission_script_overlay.cpp` displays instance phase through Sunrise's existing diagnostics HUD. An IPC acknowledgement from this candidate is not proof the native callback committed or that the player's gameplay changed; visual/runtime verification is required.

`state/investment/investment_store_boot.cpp` uses the artifact `data/investment.sqlite3`; `investment_database.cpp` recognizes schema 2 and migration from schema 1; account and inventory stores use SQLite transactions. This is distinct from our canonical database. Do not edit it externally while the game is running. Settings JSON is not the entire modern account persistence system.

## SunriseMissions, launcher and custom gear

- Missions: https://github.com/stanuwu/SunriseMissions ; `f317a32805ea72dac57152a65244e6ae36218e0d` (2026-09-18). There are campaign and freeroam libraries, region/Sense event handling and service timers. Several controllers explicitly say **not tested in game**; the EDZ controller states a cleared chest grants nothing because no script call reaches an account. These scripts do not establish complete playable campaigns or reward plumbing.
- Launcher: https://github.com/JohnMarkR/SunriseLauncher ; `8b9f73287a369abefc66d945b2b452d51ea80c1d` (2026-09-17). README identifies it as the official zeex64/stanuwu launcher rewrite, using TypeScript/Rust, pinned depot retrieval, checksum validation and SunriseMissions installation. Reuse its install validation ideas later; do not silently update any user's installation during the experiment.
- Sundial: https://github.com/KyleThmpsn/sundial ; `0bda0c53259df6c528086cb555949c5ef1d3ed6e` (2026-09-27), commit release v0.5.2. Its README lists Shadowkeep 86657, Sunrise settings schema 18 and SQLite schema 2. It edits account/configuration data and requires the game to close and relaunch for edits; it is not itself a hot runtime bridge.
- Parhelion: https://github.com/KyleThmpsn/sundial/tree/main/crates/parhelion . An actual experimental recipe/workbench/package authoring system exists for weapons and other equipment, reusing installed stock assets and engine perk components. It is a promising later Weapon Lab dependency. Mixed rigs/types/perks can fail or crash; arbitrary new engine behavior is not guaranteed. Do not mistake composing supported package structures for injecting any desired exotic function.
- SunriseGearEditor: https://github.com/WalterGerig/SunriseGearEditor . Source/README provide an unofficial live inventory editor fork. It merits a later focused review for runtime item refresh; compatibility with the selected upstream Sunrise pin is not established by its README. No merge is included here.
- Tiger tooling: https://github.com/v4nguard/tiger-pkg . README lists pre-Beyond-Light package support and required Oodle library supplied from a game installation. Package extraction/authoring does not yield a runtime combat API or automatically convert Destiny ships into NMS spacecraft.

## Current NMS and runtime modding

Hello Games release log https://www.nomanssky.com/release-log/ lists **Cosmos 7.05** as the latest retrieved public patch; notes https://www.nomanssky.com/2026/09/cosmos-7-05/ . No installed executable is present to verify storefront build ID, PE hash or equivalence to any framework's internal build number. Therefore 7.05 is a researched public release, **not a supported Destiny Frontier version**.

**Best current candidate:** https://github.com/monkeyman192/NMS.py ; `52e2e55493ddade1d89d3e638491afff995f5631` (2026-10-01). `pyproject.toml` gives NMSpy **180383.0**, with **pyMHF 0.2.4**. Treat 180383 as framework versioning; its relationship to public 7.05 has not been demonstrated here. The framework explicitly warns updates break hooks. It supports Windows Python through 3.13; its README says 3.14 is not yet supported.

Concrete source: `nmspy/data/types.py` declares patterns and native signatures for `cGcPlayerState.AwardNanites` and `cGcApplication.Update`; `common.py` exposes player-state singleton access; `globals.py` locates globals; `data/exported_types.py` declares `GroundWalkSpeed`. `example_mods/playerLocation.py` demonstrates award observation and movement-global control; gravity/scanning examples show other runtime seams. The candidate adapter uses these declarations rather than guessed addresses. A unique pattern match still does not validate field layout, ABI, object lifetime or safe callback thread; all require the real Windows executable.

**Older options:** https://github.com/gurrenm3/NoMansSky.Api ; last reviewed HEAD `1974810b828802377129a03bb96fa2d6f10ded8a`, 2023-06-03. It exposes player currencies/stats, events and globals over Reloaded-II but supplies no present-release proof. https://github.com/sonny-tel/renms ; `9696413ec82bd0bd6cea81565ef20122a1c168bb`, 2024-01-20. README explicitly targets Fractal 4.13. ReNMS would mean a separate old-version prototype, not a drop-in current NMS integration. Do not change the target to it silently.

Reloaded-II https://github.com/Reloaded-Project/Reloaded-II is a general loader/framework. Its availability does not update NMS-specific signatures or structs. The older API's debugging setup is not adopted as an instruction to alter the game executable.

## NMS assets, static mods and saves

MBINCompiler/libMBIN https://github.com/monkeyman192/MBINCompiler ; `0e81c91aa51c78d7aa3e298e9ba7532bd0c7c49c`, 2026-09-24. `libMBIN/Source/Version.cs` reports **7.04.1.3**, not blanket 7.05 validation. MBIN/MXML serialization is for metadata; source README emphasizes matching game-version layouts. It is not our runtime IPC endpoint.

AMUMSS https://github.com/HolterPhylo/AMUMSS ; `d19a6e7b115511600d8431aa195f158afb15a40f`, 2025-12-13. It processes Lua mod scripts into static mods, auto-updating components; it does not run arbitrary Sunrise event handlers inside NMS. Current README describes `GAMEDATA/MODS` subfolders for NMS 5.5+. Reproducibility requires pinning the actual downloaded tools, not just this bootstrap repository.

NMS save tooling https://github.com/zencq/libNOM.io ; `652aabb0147888776a088909cdb13bccbd3d9588`, 2025-10-28. Source supports platform save IO and multiple format generations. Its format-2004 range description is not evidence that every 7.05 save or live-write conflict is safe. Native save backup/reconciliation is a later independent gate. No save editing is used as a substitute for live integration.

## Smallest bidirectional experiment

Implemented **source candidates**, not a completed experiment:

1. Launch both original games in a Windows TEST setup and keep both alive.
2. Start the probe core, patch/build the pinned Sunrise DLL and attach the standalone test controller to a generated activity.
3. Observe a positive NMS `AwardNanites` call caused by normal player gameplay. Route its counter to Sunrise; set mission phase and visibly verify the diagnostics HUD.
4. Walk between Destiny activity regions. Observe `region_changed`, route its counter, and toggle NMS's normal walking speed between the captured baseline and 1.25× baseline.
5. Repeat, disconnect/crash each participant, verify baseline restoration when update callbacks still run, then restart all and verify canonical totals.

This proves only event/state exchange. It does not prove research, inventory unlocks, combat rewards, seamless presentation or shared physical space. No nanites are awarded by our return effect, so it cannot self-trigger an infinite reward loop.

## Feasibility decision

A small live event bridge is **REQUIRES PROTOTYPING**, with identifiable implementation points on both sides. Running two processes concurrently is technically ordinary but game liveness, pause behavior and hardware demand remain unmeasured. The **same-space Guardian fantasy** additionally needs NMS collision export into Tiger, proxy actors/targets, faithful weapon/ability simulation, unified camera/input and a usable renderer bridge. None of the inspected source establishes that combination.

Retain both processes as the research architecture. Do not build a launcher/content library until the small experiment and the same-space engine feasibility gate pass. An alternative using separate activity scenes could retain cross-game progression, but changes the requested experience and requires a concrete design decision before proceeding; it is not silently selected here.
