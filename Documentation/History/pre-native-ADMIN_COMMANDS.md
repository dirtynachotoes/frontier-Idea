# Admin commands — deferred, not implemented

The required offline admin system remains part of the project scope. This probe supplies no in-game command console or F1 overlay. It would be false to advertise /god, /spawn or /give as working.

| Proposed group | Candidate implementation seam | Status |
|---|---|---|
| /help, /diagnostics, /profile, /backup | Core command registry and validated profile store | Not implemented |
| /fly, /noclip | Sunrise exploration controls | Source feature exists; external adapter command unverified |
| /give, /weaponlab | Investment/item APIs and Parhelion; live editor research | Runtime grant/refresh requires prototype |
| /spawn, /mission | Authored mission squads/activities and native intents | Arbitrary entities/counts not verified |
| /gravity, /scan | NMSpy native/global examples | Exact executable + callback behavior requires test |
| /ship, /base, /weather | NMS native systems | No validated command adapter |
| Infinite ammo/abilities/super, damage multipliers | Destiny native combat state | Unverified |

Future commands declare adapter capability and supported build; unavailable commands return an explicit unsupported result. Campaign/Sandbox/Test must be separate canonical profiles plus appropriately separate native game save/account identities. Admin-generated equipment must retain provenance. No promotion from a sandbox profile into a campaign is implicit.
