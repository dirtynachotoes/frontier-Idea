# Guardian locomotion candidate

This implements the first opt-in host/guest movement slice. Runtime acceptance is pending. The startup-discovery blocker in STARTUP_DISCOVERY_BLOCKER.md is unchanged: one normal Guardian movement bootstrap is allowed after loading the activity. No discovery workaround or synthetic bootstrap is included.

## Exact paths

* NMS: Adapters/NMS/frontier_spatial_probe.py hooks maintained cGcPlayer.Update before/after and registers the maintained SetToPosition signature. Before Update it captures cTkBigPos from mGraphicsMatrix.pos, preserving both local and offset. After Update it applies only returned Guardian displacement with SetToPosition and zero residual NMS velocity. Spawn/transition/death, foreground, result expiry and local-player identity checks guard actuation.
* Host input: Core/frontier/motion_host.py reads foreground WASD, Shift and Space. F9 explicitly arms/disarms this development mode. These are default keyboard inputs; custom NMS bindings/controllers are not yet translated.
* Core: Core/frontier/probe.py enables the independent channel only with --guardian-locomotion; motion.py routes intent under the existing live-peer gate without refreshing the intent's source heartbeat.
* Native: Native/frontier_native.cpp runs poll_motion from the existing always-on frame tick. It resolves the six authored account actions using primary or secondary bindings and the existing teleport::action_key scan-code lookup. The small Sunrise.patch additions to hooks/polled_input/polled_input_replacements.cpp override GetKeyState/GetAsyncKeyState only for game-image callers, preserving the existing interface-open guard and other input behavior. No OS input injection, foreground spoofing or new engine signature is used.
* Return: Native/frontier_motion.h accumulates actual published Guardian position differences. The existing native camera's horizontal forward/right basis and Z-up project those differences into NMS's published graphics facing/right/up basis. Core's result consumer handles cumulative displacement, duplicate sequences, generation rebasing and incarnation/context changes. Python implements no Guardian acceleration, speed, jump impulse, gravity or collision.

## Scope and prerequisites

Run StartGuardianLocomotion.cmd instead of StartFrontier.cmd for this test. Existing Scout Link and F8 remain available but must be off during locomotion. Existing Sunrise fly must also be off. Six actions are moveForward, moveBackward, moveLeft, moveRight, holdSprint and jump. Requested unbound/unresolvable actions fail closed; configure an ordinary holdSprint binding in Sunrise if absent. No rebinding is silently written. Native input is lease-limited using the existing 2,000 ms deadline, even if camera ticks cease.

The first slice uses the Guardian's existing activity geometry for collision. It does not export NMS collision or align two entire worlds. Test in a small flat clear area in both games. Measured displacements use a development translation of one Guardian coordinate unit to one NMS coordinate unit; scale equivalence is not runtime-calibrated. The host orientation is the already established NMS graphics facing/up/right, not an independently verified free-look camera seam. Grounded/airborne engine flags are not invented; actual vertical Guardian displacement carries jump/gravity results.

Two genuinely new runtime uncertainties remain: whether the authored keyboard scan processes held inputs while Destiny is backgrounded, and whether per-frame SetToPosition safely produces visible NMS motion. If the Guardian produces no displacement, the host receives no substituted speed boost. This candidate must not be called runtime-proven locomotion until the single acceptance session passes.

The existing Sunrise Anti-AFK setting remains unchanged and should remain enabled in player.json. Its 24-hour lanes and periodic reapplication are accepted for this milestone. No second mechanism is introduced.

## Game-free development

Tests/test_motion.py exercises real mapping routing and result consumers with fake endpoints. Tests/test_nms_motion.py executes the actual NMS callbacks against typed fake objects, proving measured results replace the host step, offsets survive, duplicate callback actuation is prevented, and stale/focus-loss/transition/foreign-player cases are rejected. Tests/Native/contract.cpp compiles only a tiny portable math/policy/ABI harness with warnings as errors. Full Sunrise compilation happens only in bounded remote CI.

Pinned Sunrise: 1da7f7a86cbfbe5c92dc91287594d0ac6c70eb1c. Reviewed maintained NMSpy source and hashes are in NMS_MOTION_SOURCE_LOCK.json (API 180383.0, pyMHF 0.2.4). Existing runtime binary validation remains required.
