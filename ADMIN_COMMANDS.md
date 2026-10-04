# Current native Guardian control

StartFrontier.cmd enables Scout Link. In the NMS foreground window, F8 produces the preserved host pulse and toggles a temporary native Guardian hover/flight lease. Held-key repeats are suppressed. Other applications' key presses are ignored. The result controls NMS's existing walking assist. No window handoff is required.

Developer fallback (Core on PYTHONPATH): python -m frontier.control on, off, or status. GuardianOff.cmd requests safe off. On is refused unless live Core, both adapters and a fresh native ready status exist. Requests include native process incarnation and world/player generation. Off restores the CURRENT underlying movement preference rather than an old captured settings file. No command writes movement.json, account data or a game save.

No other cheats, currency commands, inventory editing or weapon lab are implemented in this milestone. Native status values and ABI are in PROTOCOL.md. File-backed --test-file endpoints are fake development fixtures only.
