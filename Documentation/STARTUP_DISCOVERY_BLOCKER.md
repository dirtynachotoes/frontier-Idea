# Cold-start Guardian discovery: exact missing native seam

Frontier implementation remains 77427db275d83a1092ae9e9f072f350f0d404afd. Sunrise remains pinned to 1da7f7a86cbfbe5c92dc91287594d0ac6c70eb1c. No replacement binary is justified by the available source; no new diagnostics-only build is produced.

## Closed runtime result

Before movement: in-world/host-ready true, component/snapshot absent. Normal Guardian movement for 2–3 seconds discovers the player, after which all readiness predicates stay true for the 30-second idle sample without restarting processes. Idle snapshot retention is therefore closed. The reproducible defect is cold-start acquisition, not retention or heartbeat expiry. No grace period, synthetic movement or relaxed ownership check is appropriate.

## Source-backed cause and blocker

Pinned source links:
- [player_position.cpp](https://github.com/stanuwu/Sunrise/blob/1da7f7a86cbfbe5c92dc91287594d0ac6c70eb1c/Sunrise/src/client/player/player_position.cpp): observe(component) requires a component supplied by the physics sync; poll() only reuses g_component or teleport::local_player_component(). With both null it returns without publishing. It contains no independent discovery query.
- [teleport_lifecycle.cpp](https://github.com/stanuwu/Sunrise/blob/1da7f7a86cbfbe5c92dc91287594d0ac6c70eb1c/Sunrise/src/client/hooks/teleport/teleport_lifecycle.cpp): physics_sync supplies the component to position::observe(); camera_transform polls the cache but cannot supply a component. The pinned comments explicitly state that the player physics sync stops at rest.
- [teleport_move.cpp](https://github.com/stanuwu/Sunrise/blob/1da7f7a86cbfbe5c92dc91287594d0ac6c70eb1c/Sunrise/src/client/hooks/teleport/teleport_move.cpp): local_player_component() returns the last sync-populated cache. apply_pending() populates it only while the teleport feature is active and receives its pointer from the same sync seam. owns_local_player() validates a supplied component against the controlled-object handle; it does not resolve a handle into a component.
- [teleport/runtime.h](https://github.com/stanuwu/Sunrise/blob/1da7f7a86cbfbe5c92dc91287594d0ac6c70eb1c/Sunrise/src/client/hooks/teleport/runtime.h): documents that a frame poll has no other way back to the physics component before it has been seen.

The cache cannot bootstrap itself when the first usable local-player sync has not been observed. The runtime evidence does not establish whether an earlier startup sync was absent, or occurred before ownership/body state was usable. Moving the observation after the original sync or retaining rejected foreign candidates would assume an unverified ordering/lifetime and cannot be called the exact fix.

Reviewed alternatives: world_objects object creation/allocator hooks, handle-pair/datums and entity-create paths expose object identity but no verified physics-component extraction. bootflow spawn calls expose world/slice-set gates, not the Guardian component. noclip's Havok island lookup first obtains its target body through player::position::component(); it has the same bootstrap dependency. None supplies a verified independent idle-player component address. Object datums, cinematic objects, Havok bodies and physics components are different source interfaces and must not be cast interchangeably.

The precise missing implementation seam is either (a) a verified lookup from the existing local controlled-object handle to that object's live physics component, including its lifecycle/generation validity, or (b) a verified component creation/assignment callback that delivers the local Guardian component after ownership is established, without waiting for movement. That seam must be established against the supported offline executable or an authoritative matching source/decompilation; existing pointer/offset evidence does not provide it. No user files are requested again and no already-closed runtime test is requested.

Once that seam is available, use it from the existing game-thread discovery path, validate owns_local_player(), publish through the existing snapshot abstraction and retain all world/context/finite/lease checks. A regression must start with an idle existing Guardian and no prior sync, then acquire component/snapshot through the genuine new seam while rejecting unload, replacement, ownership loss and nonfinite positions. A test-only fake resolver cannot prove that a real resolver exists.

## Existing Anti-AFK: no second implementation

Reviewed pinned client/hooks/inactivity/inactivity_override.cpp, player/player_settings_store.cpp, ui/player/player_panel.cpp, core/filesystem/path.cpp and graphics/renderer/graphics_renderer_lifecycle.cpp. Existing settings default antiAfkEnabled to false. Enable the existing Player > Anti AFK > Enabled control; it persists anti_afk_enabled in Sunrise/player.json relative to the loaded Sunrise DLL directory. Alternatively, with Sunrise stopped, back up that existing JSON and set only its anti_afk_enabled field to true while preserving all other values.

The existing implementation resolves the client activity-config getter, holds all 14 lanes at 86,400,000 ms, and reapplies at its existing two-second interval after activity re-authoring. It restores captured client values on disable/uninstall. poll() runs after a successful Sunrise rendered frame, outside the renderer lock. No Frontier-specific change is necessary to use this existing setting; no preference overwrite or duplicate anti-AFK mechanism was added. A 24-hour timeout is not mathematically infinite, and continued polling with completely suspended rendering is not established by this source review. No separate AFK runtime milestone is requested.

## Work performed

Pinned-source review and static assertions confirm the acquisition dependency and existing AFK constants/setting. No native behavior was changed, no game was launched, no local Sunrise compilation was performed and no remote build was triggered. Existing native readiness/control/spatial/lease/bridge code remains unchanged. There is no new DLL SHA, artifact ID/digest or claimed passing startup-discovery regression. The last compiled candidate remains the existing diagnostics candidate; rebuilding it cannot resolve this missing seam.
