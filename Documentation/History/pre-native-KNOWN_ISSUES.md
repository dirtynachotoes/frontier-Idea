# Current heartbeat limitations

The user has runtime-proven BOTH narrow bridge directions; the earlier pre-runtime blockers below are historical and superseded only for those observations. This heartbeat change remains Windows-unverified. Current NMS source is reconstructed; deployment is hash-guarded. Same-space integration, actual-game restart/native-save coherence and gameplay remain unverified. Cache can continue an effect during an unknown lock miss only up to the original last verified deadlines; no instantaneous crash detection claim. Sunrise phase rollback is not implemented. Core still performs SQLite/log work under the shared mutex; measure stalls before any structural redesign. Updater changes three files individually, with backups; interruption requires restoring all three originals before launch.

## Historical baseline

# Known issues / blockers

1. No Windows game-runtime access: no actual Destiny or NMS process has run here. Both adapter candidates are unverified; Sunrise binding is uncompiled.
2. No playable game, Windows release, launcher, unified combat world, Guardian control, compositor, terrain bridge or entity synchronization.
3. Exact NMS storefront/build fingerprint and compatibility with NMSpy 180383.0 are unknown. Framework freshness does not establish 7.05 compatibility.
4. Sunrise test controller must be attached to a generated activity. No new activity is registered merely by adding its filename; runtime SDK/setup has not been exercised.
5. Existing Sunrise mission controllers are not all game-tested; full progression/rewards are not restored by the bridge.
6. Native acknowledgements do not prove an observable effect. Sunrise commits phase after callback completion; verify visual phase independently.
7. Probe supports one producer per role and one Lua test controller. Concurrent mission VMs, callback threading, hot-reload and lifecycle are not validated. This is not campaign/sandbox profile isolation.
8. Native Windows/Python 3.10 execution of this repair is outstanding. The file-backed test backend now uses a Win32 mutex on Windows and flock on POSIX. The real named-mapping and abandoned-mutex tests require Windows and were skipped here. Same user/session/integrity is required; mixed elevation is not implemented.
9. Counter protocol stores only totals/maxima, not durable rich events or native intents. A producer death before publication can lose an increment. Native save rollback can diverge from canonical totals. Do not use for campaign rewards.
10. Core SQLite work currently occurs under the shared mutex. Adapters skip rather than block, but Windows latency/IO contention is unmeasured. Rich gameplay requires a different bounded queue/outbox design.
11. NMS speed baseline assumes no competing movement mod. If the update callback cannot run, it cannot restore a changed global; restarting NMS clears runtime memory. Hot-reloading the plugin can capture a modified baseline and should not be used.
12. Core logs liveness and action observations but does not log every packet or measure end-to-end gameplay latency. Disconnect loses the displayed diagnostic state only if native game resets it; no automatic phase rollback is implemented.
13. Backups are opening/closing snapshots, not timed native-save backups. No backup retention, restore UI or full campaign migration exists.
14. No validated minimum hardware, background render limit or performance recommendation.
15. No final Windows packaging workflow has run. Embedded-runtime distribution and native DLL license audit still required.

16. This repair did not revalidate upstream releases or game hooks. Original candidate version statements are historical research inputs. Linux tests and mocked Win32 calls cannot establish Windows handle behavior. Externally retained mmap buffer views, concurrent close from another thread, and thread-sharing a single Mapping are outside the probe ownership contract.
