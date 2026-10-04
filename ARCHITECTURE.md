# Host/guest architecture

NMS owns the visible universe, player-facing window and environmental collision. Sunrise owns the existing Guardian flight simulation, local component and camera/position reads. Frontier owns command lease, readiness, context validation, narrow result translation and its existing observation database.

Three named mappings are coordinated with their existing platform mutex abstraction:

| Mapping | Purpose | Writers |
|---|---|---|
| Probe_v1, 192 bytes | Preserved counters/targets and heartbeats | Core header/targets; each engine its state slot |
| Spatial_v2, 320 bytes | Structured host/guest pose | NMS slot at 64; native Sunrise slot at 192 |
| Control_v1, 128 bytes | Guardian hover requests and structured guest result | Core/frontend first 64; native guest last 64 |

The NMS spatial adapter publishes the already accessed player fields. Native Sunrise reads the fresh NMS slot as host context; it does not teleport into those coordinates. It publishes its actual Guardian position/camera into its own slot and reports which host incarnation/sequence it consumed. Core brokers pulse-to-command and acknowledged-result-to-NMS assist. The NMS movement writer stays exactly the repaired adapter: there are no competing setters.

Native Sunrise starts from client_hook_activation after both existing teleport/camera and Havok hooks successfully install. Its tick follows player-position and bootflow polling in teleport_lifecycle::camera_transform, on the existing game thread. It is independent of mission VM creation, scripts and timers. Accepted region transitions are counted at host_runtime::apply_client_state_change, before the mission-VM path, using the existing region-event predicate. That ingress hook performs atomics only; no IPC or engine writes under the host reducer's lock.

The only new Guardian command layers a transient hover expiry over movement settings. Physics-side fly readers use runtime_get(); the UI and persistent hotkey use get(). An override therefore cannot be accidentally published into movement.json. This accessor independently expires the overlay if camera ticks stop. No new memory layout, engine signature or offset is introduced.

Every frame validates loaded-world state, local-component ownership and a fresh fault-safe position read. Player-component, world-ready or local slice-context changes increment a generation and clear the lease. Requests target both process incarnation and this generation. The slice index is local context, not a universal world identifier. Neither engine's coordinates are assumed to share axes, origins, scale or collision.

IPC polls run at 100 ms, matching the existing NMS publication interval; Core remains at 20 ms. Missed locks retain only original-timestamp-bounded data. The existing 2,000 ms budget is reused, never extended by cache receipt or a retry. Explicit invalid/unready/peer-loss state clears the override; expiry bounds loss when notification cannot be observed. No worker thread touches a Guardian component. Shutdown disables ingress/ticks, clears the override and closes owned handles.

Next gameplay slice: host-controlled, bounded Guardian motion and a corresponding visible host movement result. Before writing NMS pose, identify its actual supported movement/placement API and its collision relationship. Reuse Sunrise's existing local-owner physics/velocity seams; introduce one local plane/proxy before nearby terrain collision. Do not copy a galaxy or promise guest collision on NMS terrain yet.
