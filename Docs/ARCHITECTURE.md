# Architecture — UE5.8 sci-fantasy co-op action RPG

Status: **architecture review complete; no Unreal project exists yet.** No gameplay feature has been implemented.
Review date: 2026-10-08. Companion document: [UE6_MIGRATION.md](UE6_MIGRATION.md).

Working names in this document (`Frontier*` module prefix, `FR` type prefix) are placeholders until the game has a name. Rename them before the first `.uproject` commit. Changing names after assets reference the modules costs real effort (redirects, `CoreRedirects`).

---

## 1. Repository review findings

### 1.1 What this repository actually contains

This repository (`dirtynachotoes/frontier-Idea`) is **not an Unreal Engine project**. It is *Destiny Frontier*, a GPL-3.0 interoperability bridge that:

- uses *No Man's Sky* as the visible "host" world (Python adapters for NMSpy/pyMHF in `Adapters/NMS/`);
- runs the *Sunrise* offline Destiny emulator as a "guest" (a C++ patch against pinned Sunrise source in `Native/`, built only by remote CI);
- brokers both through shared-memory IPC (`Core/frontier/`, Windows named mappings and mutexes);
- stores probe observations in SQLite (`SAVE_FORMAT.md`).

| Review item | Finding |
|---|---|
| 1. Whole-repo inspection | ~750 KB of Python, a small C++ patch, Windows `.cmd` launchers and documentation. No `.uproject`, `.uplugin`, `*.Build.cs`, `*.Target.cs`, `Config/Default*.ini`, `Content/` or `Source/` tree. |
| 2. Unreal Engine version | **None.** No engine association exists. |
| 3. Game modules and plugins | **None.** |
| 4. Gameplay Ability System configured | **No.** |
| 5. Character/movement architecture | **None in Unreal.** The bridge forwards WASD into Sunrise and writes the result to NMS via `SetToPosition`. Not reusable. |
| 6. Networking/replication | **None in Unreal.** Only local single-machine IPC (100 ms polling, mutex leases). Not reusable. |
| 7. Persistence/save | SQLite with `PRAGMA user_version`, idempotent per-incarnation sequence numbers, snapshot backups. **The concepts are reusable** (§4.4); the code is not. |
| 8. Procedural generation | **None.** |
| 9. Source control/build | Git on GitHub. Branch `main` + this review branch. Existing Python suite: `python3 -m unittest discover -s Tests` → 74 tests OK, 2 skipped (Linux run, 2026-10-08). CI (`.github/workflows/build-sunrise-spatial.yml`) builds only the Sunrise patch on Windows. **No Git LFS rules. `.gitattributes` sets `* text eol=lf`. This would corrupt `.uasset`/`.umap` binaries** (see §1.3). |
| 10. Dedicated-server blockers | Nothing in the repo can run as an Unreal dedicated server. The whole codebase is a client-side, Windows-only, single-player bridge to commercial games. |
| 11. UE6 migration hazards | None in the repo itself (there is no Unreal code). Hazards in the *proposed* design are tracked in UE6_MIGRATION.md. |

Missing required reading: `Docs/GAME_BIBLE.md` and `Docs/ROADMAP.md` do not exist. This review does **not** invent them. Game design is owned by the design lead. Where this document needs a design fact, it uses only the project brief and marks assumptions.

### 1.2 Conflict: this repository should not host the new game

These problems should be resolved **before** the first Unreal commit:

1. **License.** The repository root is GPL-3.0-or-later (`LICENSE`, `ATTRIBUTION.md`). The Unreal Engine EULA is not compatible with distributing a combined work under GPL. An original, commercial-track UE game placed in this repository would at best have an ambiguous license. **Recommendation:** create a new repository for the UE5.8 game with its own license, and leave this bridge as a separate project.
2. **Third-party IP.** The bridge exists to run Bungie and Hello Games content. The new game is described as original. Keep identifiers, terms, data and assets from the bridge (for example "Guardian", Destiny catalog data, NMS MBIN data) out of the new game's repository and history.
3. **Binary corruption risk.** `* text eol=lf` forces line-ending normalization on every file. Unreal assets are binary and would be corrupted on commit.
4. **CI collision.** The existing workflow triggers on `Tools/**`, `Tests/**`, `Native/**` and similar paths. A UE project would almost certainly create paths that unintentionally trigger the Sunrise build.

This document lives under `Docs/` in this repository only because it is the only repository available to the review session. It is written to be moved, unchanged, into the new repository.

### 1.3 Source-control requirements for the new repository

- **Git + Git LFS** (adequate for a small team) or **Perforce/Helix Core** (Epic's primary workflow; better file locking for binary assets). Decide before content production. With Git, enable LFS file locking for `*.uasset`/`*.umap` so two people cannot edit the same asset at once.
- `.gitattributes` must mark `*.uasset`, `*.umap`, `*.ubulk`, `*.uexp`, textures, audio and source art as `filter=lfs diff=lfs merge=lfs -text lockable`. Never apply a blanket `text` rule.
- Ignore `Binaries/`, `Intermediate/`, `Saved/`, `DerivedDataCache/` and `.vs/`.
- **Pin the engine:** set `EngineAssociation` to `5.8`. If engine patches are needed, use a source build from Epic's GitHub at a recorded tag/commit. Record the exact engine build in this document.
- **CI:** GitHub-hosted runners cannot practically hold a UE5.8 install. Plan for a self-hosted Windows build agent (and a Linux agent for dedicated-server targets) or Epic's Horde. Minimum gates: editor build, `Win64 Development` client, `Linux Development Server`, cook of the vertical-slice map, and the automation test suite (§7).

---

## 2. Architectural principles (summary of the brief)

1. **UE5-native today, migration-friendly tomorrow.** Use UE5.8 production systems. Do not imitate Scene Graph or Verse.
2. **Canonical state → runtime representation.** Persistent universe state is never "whatever Actors exist".
3. **Stable game identity.** Persistent entities are identified by game-level IDs, never by Actor pointers or object paths.
4. **Server authority** for everything that grants, costs, persists or decides damage.
5. **Seed + generation version + deltas** for procedural content.
6. **Versioned persistence** with explicit migration functions.
7. **C++ foundations, Blueprint presentation.** Blueprint children extend C++ APIs. No foundational system lives only in a Blueprint graph.
8. **Boundaries only at real seams.** No speculative abstraction layers.

---

## 3. Proposed module layout

One C++ game project. Code is split into a small number of runtime modules (not plugins) at first. Promote a module to a game-feature or standalone plugin only when there is a concrete reason (optional content, separate shipping, reuse).

```
Source/
  FrontierCore/          ids, native gameplay tags, schema/version helpers, deterministic hashing/RNG, log categories
  FrontierPersistence/   canonical record types, IFRPersistenceStore, migrations, transaction/intent ledger
  FrontierUniverse/      universe/planet/region state, simulation tiers, location instances, representation spawning seam
  FrontierWorldEvents/   canonical event ledger, knowledge propagation, news
  FrontierItems/         item definitions, item instances, inventory authority, currency, trade transactions, crafting rules
  FrontierAbilities/     GAS: attribute sets, base abilities, effects, damage execution, class/route definitions
  FrontierCharacter/     first-person character, movement, camera, weapons, melee, interaction routing
  FrontierProcGen/       deterministic generation descriptors (pure), PCG adapters
  FrontierTerrain/       terrain edit authority, delta log, permission checks, backend seam (prototype-gated)
  FrontierSociety/       NPC identity/records, schedules, relationships, settlements, factions
  FrontierConstruction/  structures, placement validation, base ownership
  FrontierUI/            CommonUI screens, view models (client only)
  Frontier/              primary game module: GameMode/GameState/PlayerState/PlayerController, wiring
  FrontierEditor/        editor-only: validators, data tooling, migration test commands
  FrontierTests/         automation tests for domain modules (Development/editor builds only)
```

### 3.1 Dependency direction (enforced in `*.Build.cs`)

```
FrontierCore
   ↑
FrontierPersistence
   ↑
Domain modules (Universe, WorldEvents, Items, Society, Construction, Terrain[authority], ProcGen[descriptors])
   ↑
Representation modules (Character, Abilities, Terrain[backend], ProcGen[PCG adapters], Frontier)
   ↑
Presentation (FrontierUI, Blueprints, VFX/SFX, animation)
```

Rules:

- Domain modules must not include `GameFramework/Character.h`, `GameFramework/Pawn.h` or concrete Actor classes. They may use `UObject`, `USTRUCT`, `UGameInstanceSubsystem`/`UWorldSubsystem`, Gameplay Tags and replication-capable structs.
- The Representation layer reads domain state and forwards player intent to domain services. Actors hold *handles* (stable IDs) into the domain, not copies of the canonical state.
- UI binds to view models fed by domain/representation state. It never mutates canonical state directly. Every mutation goes through a server RPC into a domain service.

**UE6 compatibility review — module split:** *Low migration sensitivity.* This is ordinary UE5 practice, and it keeps the most valuable code (rules, data and persistence) away from the Actor framework that Epic says will eventually be deprecated.

### 3.2 Why domain state uses USTRUCT/UObject rather than "pure" C++

Domain records are `USTRUCT`s and services are `UObject` subsystems. They are not engine-free C++. This choice gives:

- reflection-driven replication (`FFastArraySerializer`, push model),
- editor/Data Asset authoring, and
- `FJsonObjectConverter`/structured serialization for persistence tooling.

The cost is a dependency on UObject reflection. Epic has published no plan to remove UObject reflection, and its UE6 statements describe Verse as "transactionalizing C++" rather than replacing it. **Migration-sensitive but justified.** Rewriting the reflection-dependent pieces (replication, Data Assets, serialization) by hand would cost far more now than any speculative migration saving.

---

## 4. Core systems

### 4.1 Stable identity (`FrontierCore`)

- Strongly typed ID structs wrapping `FGuid`: `FFRPlayerId`, `FFRSettlementId`, `FFRPlanetId`, `FFRSystemId`, `FFRNPCId`, `FFRItemInstanceId`, `FFRStructureId`, `FFRPortalId`, `FFREventId`, `FFRTerrainEditId`. Distinct types prevent mixing up an NPC ID with an item ID at compile time.
- IDs are minted **only on the server**, by the owning domain service.
- Procedurally generated entities get **derived deterministic IDs**: `hash(parent id, generation version, stable local key)`. A generated NPC therefore has the same ID every time its region regenerates, without being stored.
- `UFRIdentityComponent` (a small Actor component in the Representation layer) carries the stable ID of whatever an Actor represents. `UFRRepresentationRegistry` (a world subsystem) maps ID → weak Actor pointer. Losing the Actor never loses the entity.
- `FFRPlayerId` is the game's own ID. It maps to an Online Services account/`FUniqueNetId` in the persistence layer, because platform IDs differ across Steam, EOS and LAN.
- Content references in saves use stable content IDs (`FPrimaryAssetId` or our own `FName` content keys), **never** soft object paths. Moving or renaming an asset must not break saves.

### 4.2 Gameplay Tags

- Declare engine-critical tags natively in C++ (`UE_DECLARE_GAMEPLAY_TAG_EXTERN` / `UE_DEFINE_GAMEPLAY_TAG` from `NativeGameplayTags.h`). Declare content tags in `Config/Tags/*.ini`, split by domain (`Ability`, `State`, `Damage`, `Faction`, `World`, `Item`, `Occupation`, `Event`).
- Tags describe semantics (`Damage.Kinetic`, `State.Player.Airborne`, `World.Biome.Swamp`), never Blueprint class identity.
- Tags persisted in saves are part of the save schema. Renaming a persisted tag requires a `GameplayTagRedirects` entry **and** a save migration.

### 4.3 Server authority and networking

- Dedicated server is the reference topology. Listen servers run identical server code paths. Every authoritative operation checks `HasAuthority()` at the service boundary, not in UI or Blueprint.
- Clients send **intents** (RPCs carrying IDs and parameters). Servers validate them: range, ownership, permissions, resources, cooldowns, rate limits. Clients never send outcomes.
- Replication: standard property replication with the **push model** enabled, and `FFastArraySerializer` for inventories, structure lists and similar collections. Replicate *views* of domain state scoped to relevance (owner-only inventory, area-scoped settlement summaries), never whole universe state.
- **Iris:** the official UE5.8 release notes, as quoted in search results, state that Iris is production-ready in 5.8. Epic's public roadmap still listed it as Experimental. Verify against the installed 5.8 build. Write replication code against the standard UPROPERTY/FastArray/push-model APIs so that Iris is a configuration choice. Decide whether to enable it after a Phase 0 measurement on the vertical-slice map. *Migration-sensitive but justified* (UE6 networking direction: UNKNOWN).
- Hit validation: client-predicted hit *feedback* only. The server confirms hits with bounded rewind (lag compensation) against server-side hitbox history. UE5 has no general built-in lag compensation for this use case. Budget a dedicated task.
- Anti-cheat posture for co-op: validate economy, persistence and progression strictly. Movement and aim validation can be more lenient, since this is co-op and not competitive, but must never award items or progression.

### 4.4 Persistence (`FrontierPersistence`)

**Model:** canonical records → (serialize) → store. On load, store → (migrate) → canonical records → representation.

- Every persisted root record carries `SchemaVersion` (int32) and a record kind. Each kind registers a chain of migration functions `vN → vN+1`. Loads always run the chain. Saves always write the current version. Unknown *future* versions are refused, not guessed.
- Record kinds (initial): `PlayerProfile`, `PlayerCharacter`, `Inventory`, `UniverseHeader`, `SystemState`, `PlanetState`, `TerrainDeltaLog`, `SettlementState`, `NPCRecord`, `NPCMemory`, `StructureSet`/`BaseState`, `PortalNetwork`, `EventLedgerSegment`.
- Serialization: canonical `USTRUCT`s. The on-disk format is chosen by the store, not by the records: compact binary for runtime, JSON export for debugging, tooling and migration tests. **Never** save live `UObject` graphs or `AActor` subobjects as the persistence format. `USaveGame` may serve as a transport container on listen servers, but the payload remains our versioned records.
- `IFRPersistenceStore` is a real seam: listen-server local store vs dedicated-server store, and later possibly an external database service. First implementation: a file- or SQLite-backed store. The engine ships a `SQLiteCore` plugin; confirm its presence and status in the installed 5.8 build before relying on it.
- **Economic transactions are idempotent.** Every grant, trade, purchase or craft has a server-minted transaction ID. It is applied atomically (all records in one store transaction) and recorded in an intent ledger so that a replayed or retried request is a no-op. (This carries over the proven idea from this repository's sequence-idempotent `store.py`.)
- Autosave cadence and crash-recovery policy are decided in Phase 0. Backups use snapshot copies, never copying a live database file mid-write.
- Server-only data (other players' inventories, hidden world state) never leaves the server.

**UE6 compatibility review:** *Low migration sensitivity.* Explicit versioned records are exactly what lets a future engine load the same universe.

### 4.5 Universe, locations and simulation tiers (`FrontierUniverse`)

The universe is canonical data: systems → planets (`PlanetId`, `PlanetSeed`, `GenerationVersion`, deltas) → regions/settlements/structures. A **location instance** is the runtime thing a player physically occupies: a planet region, a station, a ship interior, a dungeon instance or a raid.

**Open technical risk — players in different places at once.** One UE server process hosts one `UWorld`. There are two candidate topologies:

- **A. One world, many far-apart zones.** Use Large World Coordinates (double precision, default in UE5) and World Partition with server-side streaming around every player. Stations, dungeons and ship interiors would be placed as Level Instances in distant regions of the same world. Simplest networking. Risks: server memory and CPU with 10 dispersed players, and the cost of streaming procedural planets.
- **B. Multiple server processes.** One process per active location, with travel and handoff between them and a shared persistence store. Scales better. Much more operational complexity (orchestration, cross-process consistency).

**Recommendation:** the vertical slice uses one process and one region. All universe state lives in `UFRUniverseSubsystem` plus the persistence store, **never** in a level. A location instance is entered through `IFRLocationHost` (load/unload/travel). That keeps A versus B a deployment decision. Run a Phase 1 prototype of A with 10 simulated dispersed clients before committing.

**Simulation tiers** (applied to NPCs, wildlife, settlements and economy):

| Tier | Where | Fidelity |
|---|---|---|
| 0 — Embodied | Near players | Full Actors, StateTree behaviour, navigation, animation |
| 1 — Proxied | Loaded but distant | Lightweight agents (candidate: Mass, prototype-gated); no full Actor |
| 2 — Abstract | Unloaded, recently relevant | Coarse schedule/economy tick in domain services (minutes of game time per step) |
| 3 — Catch-up | Unloaded | Deterministic or statistical resolution of elapsed time when the location loads |

Promotion and demotion happen through the representation seam (`IFRRepresentationSpawner`). An NPC keeps its `NPCId`, record and memories across all tiers.

### 4.6 World events, knowledge and dialogue (`FrontierWorldEvents`)

```
Game simulation → canonical event → event ledger → knowledge propagation → NPC/faction interpretation → natural-language expression
```

- A canonical event is a record (`EventId`, type tag, participants by stable ID, location ID, game time, magnitude/payload). Only server-side game systems emit events.
- Knowledge propagation is a domain rule: who learns what, when, and with what distortion or confidence. It runs in tier 2 for unloaded locations.
- NPC and faction interpretation produces structured attitudes and memories.
- Any AI or LLM text generation is a **read-only expression layer** over known facts. Its output is never parsed back into canonical state. If this layer uses an external AI service, it sits behind a client-or-server adapter with timeouts and a deterministic authored fallback line.

### 4.7 Items, inventory, currency, trading (`FrontierItems`)

- Item *definitions* are `UPrimaryDataAsset`s keyed by stable content IDs. Item *instances* are records (`ItemInstanceId`, definition ID, stack count, rolled stats, provenance).
- `UFRInventoryComponent` replicates an owner-only `FFastArraySerializer` view. **All mutations go through `UFRInventoryService` on the server** (grant, consume, move, split, equip), and each is idempotent by transaction ID.
- Currency is a server ledger, not a float on a pawn.
- Trades (player↔player, player↔merchant) are two-phase on the server: lock both sides → validate → commit atomically → release. No client-side state is ever trusted.

### 4.8 Abilities, classes, combat (`FrontierAbilities`, `FrontierCharacter`)

- **GAS** for class abilities, attributes, effects, costs, cooldowns and status interactions. Players get an `AbilitySystemComponent` on the **PlayerState**, so it survives respawn. AI gets it on the Pawn. Replication mode is Mixed for players and Minimal for AI.
- Classes (Resonant, Vanguard, Wayfarer, Artificer, Bladebound, Wildborn) and advanced routes are defined as data (a `UFRClassDefinition` Data Asset referencing ability sets, attribute defaults, skill-tree data and movement profile). Design identity lives in data plus specific C++/Blueprint ability implementations, **not** a shared generic ability recoloured six times. Class design content belongs in GAME_BIBLE.md (not yet written).
- Damage is authoritative via `UGameplayEffectExecutionCalculation` on the server. Damage types are tags (`Damage.Kinetic`, …).
- Weapons: a C++ weapon-instance model (fire modes, spread, recoil, ammo as attributes or inventory) with Blueprint/Data Asset configuration. Presentation (recoil animation, VFX, audio) is in Blueprints.
- **Movement — prototype-gated decision.** `UCharacterMovementComponent` (CMC) is proven, with client prediction and custom movement modes. Mover (with Network Prediction) is Epic's newer path; 5.8 notes expanded rollback/prediction, but this review could not confirm its maturity label. Phase 0 builds the same small high-mobility kit (dash, wall-run or equivalent, gravity anchor, glide) on both and measures prediction correctness under latency. **Default to CMC** if Mover is not marked production-ready in the installed 5.8 build. Either way, abilities request movement through a thin `UFRMovementIntent` API so the movement backend is replaceable. *Needs isolation behind boundary.*
- First-person rendering: use the engine's first-person rendering support if present and suitable in 5.8 (verify in the installed headers). Otherwise use the conventional separate first-person arms mesh. Third-person views for vehicles, ships and selected exosuit modes are camera modes, not separate characters.
- Input: Enhanced Input, with input mapping contexts per mode (on-foot, vehicle, ship, build mode, menu).

### 4.9 Procedural generation (`FrontierProcGen`)

- Generation is a deterministic function: `(seed, GenerationVersion, inputs) → descriptors`. Descriptors are plain data: biome map, POI list, spawn tables, settlement seeds. Representation (meshes, PCG output, foliage) is then built from descriptors.
- Seeds are derived by **integer hashing** of parent seed + stable key, not by stepping one shared random stream, so adding a new generation step does not reshuffle everything else.
- Avoid floating-point-dependent branching in descriptor generation where it affects gameplay identity (POI placement, IDs). Floating-point output may differ across compilers and platforms.
- **PCG graphs are part of the generation version.** Editing a PCG graph used for gameplay-relevant placement can move content. Such graphs are versioned, and persisted planets pin the `GenerationVersion` they were created with. Changing it requires a migration that re-anchors deltas, or "new content only applies to unvisited planets".
- Authored anchors (story locations, raids, signature enemies) are placed by authored data that procedural generation must respect (exclusion zones, fixed seeds). Procedural systems never overwrite them.

### 4.10 Mutable terrain (`FrontierTerrain`) — dedicated risk area

UE Landscape is a heightfield and cannot do caves, overhangs or tunnels. UE5.8 introduces an **experimental** mesh-based terrain system, according to secondary coverage of the release notes. Its suitability for runtime, multiplayer, volumetric editing is **unknown**; evaluate it, but do not assume it.

The authority model is independent of the rendering/meshing backend and can be built first:

- Base terrain = `f(PlanetSeed, GenerationVersion)`. Never stored.
- **Edits are an ordered, server-authored operation log** per chunk: `TerrainEditId`, author `PlayerId`, op type (dig, fill, smooth, paint, plant, remove vegetation), brush parameters, chunk key, sequence number. Periodic per-chunk compacted snapshots bound the replay cost.
- Clients send edit *requests*. The server validates permissions (claims, protected authored areas, rate and volume limits), applies the edit, appends it to the log and replicates ops (not geometry) to relevant clients. Every client meshes deterministically from base + ops.
- Admin tools: per-player edit rollback, per-area reset to generated state, log inspection.
- The log is schema-versioned like any other record.

**Backend options to prototype in Phase 1** (do not commit before measuring):

1. A third-party voxel plugin, for example Voxel Plugin. Evaluate against the plugin criteria in §6.
2. A custom voxel/SDF chunk mesher (in-house; full control; most work).
3. The engine's experimental mesh terrain (only if runtime editing is supported).

Wrap the chosen backend behind `IFRTerrainBackend` (apply op, query density/material, build collision). *Needs isolation behind boundary.*

### 4.11 Society: NPCs, schedules, settlements (`FrontierSociety`)

- `NPCRecord` (identity, occupation tag, home and work location IDs, relationships, schedule template, faction, memory refs) is canonical. Actors are tier-0 representations of these records.
- Schedules are data (occupation → time-slotted activities) and are evaluated by the domain service at every tier. StateTree runs the embodied behaviour at tier 0 (StateTree is listed as production-ready for 5.8 on Epic's roadmap; verify).
- Settlement simulation (population, economy, mood, construction, threat) is a domain service ticking at tier 2 when unloaded. Never put it in a settlement Blueprint.

### 4.12 Construction, bases, vehicles, ships

- Structures are records (`StructureId`, owner, definition ID, transform relative to an anchor, which is a planet chunk, station or ship ID, plus health and state). Placement is validated on the server (overlap, terrain support, claims, cost).
- Bases on moving anchors (ships, orbital stations) store transforms **relative to the anchor**, never world-absolute.
- Vehicles and ships: deferred until after the vertical slice. They must use the same identity, persistence and authority rules. Spaceflight and planet transitions are a major technical risk that needs a dedicated prototype (coordinate frames, LWC, streaming, physics authority).

---

## 5. Blueprint policy

| Allowed and encouraged in Blueprint | Must have a C++/data foundation |
|---|---|
| VFX, SFX, animation hookups, cosmetic ability cues (GameplayCues) | Inventory, currency, trading, crafting outcomes |
| Encounter assembly, level scripting for authored missions | Damage rules, ability authority, progression awards |
| Ability *presentation* and designer-tuned subclasses of C++ abilities | Persistence, IDs, schema migration |
| UI layout (UMG/CommonUI) | Terrain edit authority, structure placement authority |
| PCG graph authoring | NPC identity, settlement and universe simulation |
| Data Asset/Data Table content | Portal network state, world event ledger |

Blueprints subclass C++ types that expose `BlueprintImplementableEvent`/`BlueprintNativeEvent` hooks. A Blueprint graph that grows logic beyond presentation should be reviewed for promotion to C++.

---

## 6. Third-party plugin policy

Before adopting any plugin, record in this section and in UE6_MIGRATION.md:

- verified UE5.8 compatibility (a build of the exact engine version),
- source availability and license,
- behaviour on dedicated server (Linux server target builds, authority model, replication),
- persistence implications (does it own save data, and in what format),
- migration-blocker risk if the vendor does not follow UE6,
- an adapter seam if the plugin is load-bearing (terrain, voice, backend services).

No third-party plugins have been adopted yet.

---

## 7. Testing strategy

- **Domain modules** (`FrontierCore`, `FrontierPersistence`, Items, Society, ProcGen descriptors, Terrain authority) are covered by automation tests (Automation Spec or Low-Level Tests) that run headless without a map. This is the main payoff of keeping rules out of Actors.
- **Persistence migration tests:** a fixture directory of saved records for every historical schema version, loaded and migrated on every CI run. Never delete old fixtures.
- **Determinism tests:** golden descriptor hashes for fixed seeds and generation versions.
- **Networking tests:** functional tests or Gauntlet runs with a dedicated server and 2+ clients for inventory, trade, terrain edit and ability authority. Use latency/packet-loss emulation for movement prediction.
- **Server target:** CI builds the Linux dedicated-server target from day one so client-only code paths are caught early.

---

## 8. Phased plan (architecture only — no features before Phase 0)

| Phase | Content | Exit criteria |
|---|---|---|
| 0 — Foundation | New repo + LFS/locking, UE5.8 C++ project, module skeletons, IDs, tags, persistence store + migration framework, GAS setup on PlayerState, dedicated-server target in CI, CMC vs Mover spike, Iris measurement | Clean server and client builds; save → migrate → load test green; 2-client dedicated-server smoke test |
| 1 — Risk prototypes | Volumetric terrain backend comparison; one-world dispersed-players prototype (topology A); NPC tier promotion/demotion; first-person gunplay feel prototype | Written decision records for terrain backend, topology, movement backend |
| 2 — Vertical slice | One region, one settlement, 2–3 classes, gunplay + melee, inventory/trade, terrain edits, event ledger → NPC reaction | Defined in ROADMAP.md (to be written by design lead) |

---

## 9. Decision log

| # | Decision | UE6 compatibility review |
|---|---|---|
| D1 | New game goes in a new, non-GPL repository | n/a |
| D2 | Domain/representation module split with enforced dependency direction | Low migration sensitivity |
| D3 | USTRUCT/UObject-based domain records and subsystems | Migration-sensitive but justified |
| D4 | Stable typed GUID IDs; deterministic derived IDs for generated entities | Low migration sensitivity |
| D5 | Versioned canonical records + migration chains; no UObject-graph saves | Low migration sensitivity |
| D6 | GAS for abilities/attributes; ASC on PlayerState | Migration-sensitive but justified (Epic says UE6 gameplay abilities land as Verse-scriptable Scene Graph components; conversion path UNKNOWN) |
| D7 | Movement backend behind `UFRMovementIntent`; CMC default pending spike | Needs isolation behind boundary |
| D8 | Terrain authority = op log independent of meshing backend | Needs isolation behind boundary (backend); authority layer low sensitivity |
| D9 | Location instances behind `IFRLocationHost`; topology A vs B deferred to prototype | Unknown — UE6 architecture not documented sufficiently (Epic describes distributed-server Verse work as early prototype) |
| D10 | Iris on/off is a configuration decision after measurement | Migration-sensitive but justified |
