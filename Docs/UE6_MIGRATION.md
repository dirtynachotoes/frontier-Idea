# UE6 migration watchlist

Production engine: **Unreal Engine 5.8.** UE6 is a future migration target only. Do not build against the UE6 development stream.
Last reviewed: 2026-10-08. Companion: [ARCHITECTURE.md](ARCHITECTURE.md).

> Status note: no Unreal project exists yet (see ARCHITECTURE.md §1). The "current UE5.8 implementation" entries below describe the **planned** implementation. Update this file in the same commit that changes the real implementation.

## 1. What Epic has officially stated (as of this review)

Only these points are treated as established. Everything else is UNKNOWN.

| Statement | Source |
|---|---|
| UE6 will include "an entirely new gameplay framework known collectively as Scene Graph, built from scratch on Verse." | Epic, *The road to Unreal Engine 6* |
| Verse "transactionalizes C++"; the gameplay programming model moves to Verse. | Epic, *The road to Unreal Engine 6* / *State of Unreal 2026* recap |
| Actors and Blueprints ship in early UE6 versions. "Eventually, these will be deprecated when the new framework is sufficiently mature, and you'll have conversion tools to move projects from one framework to the other." | Epic, *The road to Unreal Engine 6* |
| Epic aims for "a manageable and clear path forward" for studios shipping on UE5. | Epic, *The road to Unreal Engine 6* (as quoted in search results) |
| Core systems "like animation, itemization, and gameplay abilities" are landing as Verse-scriptable Scene Graph components. | Epic, *State of Unreal 2026: top news* |
| UE6 Early Access is targeted for the end of 2027; full release 12–18 months later. | Epic, *The road to Unreal Engine 6* |
| A UE6 development stream is publicly visible on GitHub; the Verse implementation is visible there but "not intended for general adoption at this point." | Epic, *State of Unreal 2026: top news* |
| Distributed software transactional memory across servers is early prototype work. | Epic, *State of Unreal 2026: top news* |
| glTF/USD are to become first-class formats where they meet UE6's needs. | Epic, *State of Unreal 2026: top news* |
| UE5.8 released at State of Unreal on 2026-06-17. Reported as the last planned major UE5 release, with a 5.9 possible if needed. | Secondary coverage (gamefromscratch, wnhub). **Verify against Epic.** |

Verification limit: the review environment's network policy blocked direct fetches of `unrealengine.com` and `dev.epicgames.com`. The quotations above come from search-engine excerpts of those official pages. Re-read the originals before relying on exact wording.

Sources:
- https://www.unrealengine.com/news/the-road-to-ue-6
- https://www.unrealengine.com/news/state-of-unreal-2026-top-news-from-the-show
- https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-5-8-release-notes
- https://portal.productboard.com/epicgames/1-unreal-engine-public-roadmap/

**Conversion tooling:** Epic has announced conversion tools for moving projects from the Actor/Blueprint framework to Scene Graph. Their scope, fidelity and handling of C++ subclasses, GAS, replication and custom serialization: **UNKNOWN — awaiting official Epic documentation.** Treat them as future assistance, not as part of the architecture.

## 2. Migration-risk table

Risk levels: low / medium / high / unknown. "Tooling" = whether Epic has announced conversion tooling that covers the system.

| System | Planned UE5.8 implementation | Legacy-framework dependency | Risk | Official UE6 direction | Tooling announced | Action now | Deferred until UE6 is production-ready |
|---|---|---|---|---|---|---|---|
| Actors | Representation only: player pawn, NPC bodies, structures, projectiles, interactables | High (Actors are the representation layer) | **high** | Scene Graph replaces the Actor framework; Actors ship in early UE6, deprecated later | Yes (Actor/Blueprint → Scene Graph; scope UNKNOWN) | Keep canonical state, rules and IDs out of Actors (`UFRIdentityComponent` + registry); Actors hold handles | Evaluate the converter on a branch; rebuild the representation layer against Scene Graph |
| Actor Components | Thin bridges: identity, inventory view, interaction, ASC | Medium | **medium** | UNKNOWN — Scene Graph has its own component model; mapping not documented | Implicitly via Actor conversion; scope UNKNOWN | Components forward to domain services; no persistent state lives only in a component | Map each component to a Scene Graph equivalent |
| Blueprints | Presentation, ability cosmetics, encounter scripting, tuning subclasses of C++ | Medium (content), low (foundations) | **medium** | Deprecated eventually; Verse is the gameplay language; no visual-Verse tool announced | Yes (scope UNKNOWN) | Enforce the Blueprint policy (ARCHITECTURE.md §5); review graphs that grow logic | Convert or re-author presentation graphs |
| Gameplay Framework (GameMode/GameState/PlayerController/PlayerState) | Session wiring, ASC on PlayerState, RPC entry points | High | **high** | UNKNOWN — awaiting official Epic documentation | UNKNOWN | Keep these classes as thin wiring; rules live in subsystems/services | Re-map session flow |
| Scene Graph | Not used | n/a | unknown | New UE6 gameplay framework | n/a | Do **not** imitate it internally | Prototype a vertical slice on UE6 Early Access in a branch |
| Verse | Not used | n/a | unknown | UE6 gameplay language | n/a | None. Do not adopt the UE6 stream's Verse | Evaluate Verse interop with existing C++ modules |
| UObject assumptions | `USTRUCT` domain records, `UObject` subsystems, Data Assets, reflection-based replication and serialization | Medium | **unknown** | UNKNOWN — Epic describes Verse as transactionalizing C++ but has not documented UObject's future | UNKNOWN | Persist via explicit versioned records, never `UObject` graphs or object paths; keep content references as stable content IDs | Re-check once Epic documents C++/UObject interop |
| Replication (generic) | Push-model property replication, `FFastArraySerializer`, server RPCs for intents | High | **medium** | UNKNOWN — Verse/Scene Graph replication model not documented for UE6 | UNKNOWN | Replicate *views* of domain state; never put rules in `OnRep` handlers | Re-implement replication of views; domain rules unaffected |
| Iris | Optional; enable or disable after Phase 0 measurement | Medium | **unknown** | UNKNOWN | UNKNOWN | Write against standard replication APIs so Iris stays a configuration choice; verify 5.8 maturity (release notes say production-ready, roadmap said Experimental) | Re-evaluate |
| Network Prediction | Only if Mover is chosen | Medium | **unknown** | UNKNOWN | UNKNOWN | Avoid unless Mover is adopted | Re-evaluate |
| Mass | Candidate for tier-1 proxied NPCs/wildlife; prototype-gated (roadmap: Beta in 5.8) | Medium | **unknown** | UNKNOWN | UNKNOWN | Keep NPC identity and schedules in `FrontierSociety`; Mass would only be a representation | Re-evaluate |
| StateTree | Tier-0 NPC behaviour (roadmap: production-ready in 5.8; verify) | Low–medium | **medium** | UNKNOWN | UNKNOWN | StateTree tasks call domain services; schedule data is not authored inside trees | Port trees or tasks |
| Mover | Candidate movement backend vs CMC; spike in Phase 0 (5.8 maturity not confirmed in this review) | Medium | **unknown** | UNKNOWN | UNKNOWN | Movement behind `UFRMovementIntent` so CMC/Mover is swappable | Re-evaluate |
| CharacterMovementComponent | Default movement backend if Mover is not production-ready | High (Actor/Character based) | **high** | UNKNOWN; tied to `ACharacter` | Implicitly via Actor conversion; scope UNKNOWN | Same isolation as Mover | Replace with the UE6 movement solution |
| World Partition | Streaming for planet regions; Level Instances for stations/dungeons | Medium | **medium** | UNKNOWN | UNKNOWN | No canonical state in levels; procedural content regenerates from seed | Re-map streaming |
| PCG | Placement/presentation from deterministic descriptors | Low–medium | **medium** | UNKNOWN | UNKNOWN | Gameplay-relevant PCG graphs are part of `GenerationVersion`; gameplay identity comes from descriptors, not PCG output | Validate output parity under UE6 or pin by version |
| Gameplay Ability System | Abilities, attributes, effects, cues; ASC on PlayerState | High (Actor-owned ASC, Blueprint ability subclasses) | **high** | Epic: gameplay abilities landing as Verse-scriptable Scene Graph components; relation to GAS UNKNOWN | UNKNOWN | Class/route definitions and tuning in data; damage maths in C++ execution calculations; avoid ability logic that exists only in Blueprint graphs | Map GAS concepts to UE6 ability components; convert attributes/effects from data |
| Animation framework | Animation Blueprints/Motion Matching for character presentation | Medium | **medium** | Epic: animation landing as Verse-scriptable components | UNKNOWN | Keep animation presentation-only; gameplay never reads animation state for authority | Re-author per UE6 tooling |
| Input | Enhanced Input, per-mode mapping contexts | Low | **low** | UNKNOWN | UNKNOWN | Input actions map to intents; no gameplay rules in input handlers | Re-map bindings |
| UI (UMG/CommonUI, view models) | Client-only presentation bound to view models | Medium | **medium** | UNKNOWN | UNKNOWN | UI never mutates canonical state; view models isolate widgets from domain | Re-implement widgets if required |
| Persistence | Versioned canonical records + migration chains; `IFRPersistenceStore` | Low | **low** | Not engine-specific | n/a | Schema versions on every root record; fixtures for every version; content IDs not object paths | Write a migration only if UE6 changes content IDs |
| Gameplay Tags | Semantic tags (native + ini); persisted tags covered by migrations | Low | **low** | UNKNOWN | UNKNOWN | Keep tags semantic; tag renames need redirect + save migration | Verify tag support |
| Data Assets / Data Tables | Item, class, occupation, biome and settlement definitions | Medium (UObject assets) | **medium** | UNKNOWN | UNKNOWN | Definitions keyed by stable content IDs; keep them plain-data structs where possible | Convert or export |
| Editor automation | Validators, data tooling, migration test commands in `FrontierEditor` | Medium | **medium** | UNKNOWN | UNKNOWN | Keep tooling in C++/Python editor scripting; no critical tooling as Editor Utility Blueprints only | Port tooling |
| Third-party plugins (none adopted) | — | Varies | **unknown** | n/a | No | Apply the plugin policy (ARCHITECTURE.md §6) and require an adapter for load-bearing plugins | Confirm vendor UE6 plans before migrating |

## 3. Highest-leverage actions now

1. **Keep canonical state out of Actors and Blueprints.** This single rule shrinks the high-risk rows (Actors, Gameplay Framework, GAS, CMC) to "rebuild the representation layer", not "rewrite the game".
2. **Versioned persistence with stable IDs and content IDs.** The universe, saves and terrain deltas should load into any future engine.
3. **Isolate the two backends most likely to change:** movement (`UFRMovementIntent`) and terrain meshing (`IFRTerrainBackend`).
4. **Keep the domain modules headless-testable.** Those tests become the regression suite for any migration.

## 4. Future migration procedure (when UE6 tooling exists)

1. Read the official UE6 migration documentation; update §1 and the table.
2. Run Epic's conversion tools on a dedicated branch, never on the production branch.
3. Record unsupported systems in this file.
4. Migrate incrementally: domain modules first (expected to compile with few changes), then representation, then presentation.
5. Keep the UE5.8 build as production until the UE6 branch passes the full test suite, including save-migration fixtures and dedicated-server tests.

## 5. Change log

| Date | Change |
|---|---|
| 2026-10-08 | Initial watchlist from the architecture review. No Unreal implementation yet. |
