# Destiny Frontier — native Guardian guest milestone

NMS is the visible world host. Offline Sunrise/Destiny is the Guardian gameplay guest. Frontier coordinates small, versioned state transfers; it is not a third engine.

This canonical tree consolidates the repaired, runtime-proven event bridge, spatial V2, native guest source, remote build tooling, game-free tests and installation. The earlier spatial Actions build is a **closed compile gate**: do not install its intermediate DLL. Build this entire milestone once through the existing repository workflow.

The new slice is **Guardian Scout Link**: while NMS has focus, F8 produces an existing Frontier pulse. Core requests a temporary native Guardian flight/hover lease. Sunrise applies its existing native flight simulation and returns acknowledgement, context and pose. Core translates the acknowledged guest lease into the already proven NMS walking assist (1.25 × the captured baseline). F8 again clears the lease/assist. No window switching is required to operate the feature. No preference or native save is changed by the command.

This is an initial guest capability/result exchange, **not shared Guardian/NMS physics**. The NMS assist is a translation of the guest flight lease, not the Guardian's measured walking velocity. NMS still owns visible movement and collision. The existing NMS event callback also observes positive nanite awards; it is preserved, not expanded. In Scout Link those legacy pulses can also toggle the lease; no currency is awarded or modified by Frontier.

Always-on means native communication during Sunrise's existing client frame lifecycle regardless of loaded mission Lua. An unloaded or suspended guest cannot simulate independently of its game lifecycle. The optional old Lua phase display can still read cached status, but has no transport ownership.

Read BUILD.md for the **one remote build**, INSTALL.md for the **one consolidated install**, and Documentation/RUNTIME_ACCEPTANCE.md for the **one eventual session**. StartFrontier.cmd starts Core in Scout Link mode using the existing Python environment. Use the already working game/loader launch arrangements, with Sunrise backgrounded only as far as its lifecycle continues to tick. This milestone does not claim the final polished DestinyFrontier.exe is finished.

RunLightweightTests.cmd performs Python/static/fake-endpoint checks without launching games or compiling Sunrise. Remote CI additionally compiles the small real native policy/ABI harness and the complete native guest.
