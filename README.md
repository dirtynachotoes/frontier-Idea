# Destiny Frontier — Guardian locomotion candidate

NMS is the visible world host. Offline Sunrise/Destiny is the authentic Guardian gameplay guest. Frontier translates small state transfers.

The current opt-in slice routes foreground WASD/Shift/Space into Sunrise's authored keyboard actions and returns measured Guardian displacement to NMS. F9 arms/disarms it. **Locomotion runtime acceptance is pending**; this is one consolidated development candidate, not a finished release game.

StartGuardianLocomotion.cmd enables this candidate using the existing Python environment. StartFrontier.cmd preserves the previously tested Scout Link behavior. Keep Scout Link hover and Sunrise fly off for locomotion. The known one-time manual Guardian movement bootstrap remains permitted; the startup-discovery blocker is unchanged.

Read Documentation/GUARDIAN_LOCOMOTION.md for the exact seams, limits and new uncertainties. Documentation/RUNTIME_ACCEPTANCE.md describes the single session after the remotely compiled candidate is installed. INSTALL.md and Tools/install_candidate.py preserve backup and offline-executable fingerprint checks. No commercial game files are distributed.

The proven bidirectional bridge, heartbeat repair, published-snapshot readiness, always-on native lifecycle, ControlBlock 128-byte layout and Spatial V2 remain in place. RunLightweightTests.cmd checks protocol work without games; the bounded GitHub workflow alone compiles Sunrise.
