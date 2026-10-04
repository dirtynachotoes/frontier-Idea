# One readiness/hover runtime retest

Use the single corrected remotely built candidate. The previous installed test already proved Core, both live paths, heartbeat repair, NMS Spatial V2 delivery, native lifecycle/heartbeat/host consumption and F8 input. Do not repeat separate tests of those paths.

1. With games/Core stopped, install this candidate once using Tools/install_candidate.py and the same established Core/NMS/offline paths and offline executable fingerprint. Preserve existing configuration and saves; the installer backs up replaced files. No intermediate DLL installation is needed.
2. Start Core with the existing scout-link configuration, start the supported offline Sunrise activity, then NMS. Keep NMS foreground and the existing base Sunrise fly setting off. Run the existing `python -m frontier.control status` from the Core environment: expect `ready: true` once the local Guardian is present.
3. Press F8 once: expect request acknowledgement, `hover: true`, and visible NMS movement assist. Press F8 again: expect a new acknowledgement, `hover: false`, and clean baseline restoration. Record status/logs and stop.

This resolves only whether the published Guardian snapshot repairs the false unready condition and enables the already-implemented reversible native command/host result. It does not claim shared-space collision or Guardian-driven NMS physics.
