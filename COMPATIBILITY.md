# Current compatibility

| Component/capability | Status/evidence |
|---|---|
| Two simultaneous games; NMS→Core→Sunrise phase; region→NMS speed | Runtime verified by supplied Windows history |
| Repaired heartbeat contention behavior | Confirmed; repaired ipc.py and NMS event adapter preserved byte-for-byte |
| NMS live position/orientation, Sunrise position/camera access | Closed source/runtime findings; reused without new addresses |
| Sunrise spatial V2 128-byte native layout | Closed compile gate; successful existing Actions spatial build |
| New always-on native guest/hover and host-operated return | Implemented/source validated; full new remote compilation and batched game acceptance pending |
| Shared terrain collision, Guardian weapon/ability simulation on NMS host | Not implemented or verified |

Target stays the established offline Steam Destiny client 86657, build string 86657.20.08.23.1800.d2_rc___release, with Sunrise commit 1da7f7a86cbfbe5c92dc91287594d0ac6c70eb1c. Live/current Destiny/Bungie services/anti-cheat are outside scope. Hooks fail closed if existing movement seams cannot install.

NMS remains the exact previously validated local executable, NMSpy 180383.0 and pyMHF 0.2.4. Its binary validation gate and adjacent-record fallback are retained. No claim is made that an arbitrary current NMS release or newer framework is compatible. Core supports the existing Windows Python 3.10 environment; Linux explicit file-backed test endpoints are also retained.

V2 is now wire version 2 and name Spatial_v2 on both engines. Prior Spatial_v1 components cannot join it. The event bridge remains v1. The native command/result contract is a separate v1 mapping. Native lease readiness requires a loaded/local Guardian and a fresh valid NMS pose; communication/readiness survives any activity Lua selection, but game lifecycle pauses/suspension naturally expire leases.

Hardware/FPS/background-rendering changes are not introduced or guessed. The eventual session specifically checks native guest progress while NMS is focused. If the guest frame lifecycle stops in the background, do not hide that with timeout expansion; guest scheduling is then the next actual gameplay blocker.
