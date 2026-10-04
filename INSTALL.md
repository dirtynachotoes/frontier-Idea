# Install the complete candidate once

Wait for **Build Destiny Frontier Native Guest** to succeed. Download its sole DestinyFrontier-Windows-x64 artifact and extract it. Do not install the earlier spatial build or any source-only archive as a native DLL candidate.

Preserve the already working NMSpy/pyMHF environment, exact NMS executable and adjacent runtime-validation.json. Preserve existing Frontier profiles/backups, Sunrise account/save data and NMS native saves. The installer replaces code and the offline Sunrise DLL only. It does not replace an activity Lua controller, bootstrap games, build C++ or alter native saves.

Close Core, NMS and offline Destiny once. From the extracted candidate, run the single installer below with your existing known paths and the hash of the established offline destiny2.exe (use an existing fingerprint or Get-FileHash; this is identification, not a new runtime test):

```powershell
python Tools\install_candidate.py --core-root "<existing Frontier root>" --nms-mod-dir "<actual NMSpy mod directory>" --offline-root "<established OFFLINE Destiny root>" --offline-exe-sha256 "<established offline executable SHA256>" --apply
```

Never point --offline-root at the live/current Steam Destiny installation. The explicit hash attests the operator-selected existing offline target; the tool cannot infer commercial version compatibility from an unknown executable hash. It validates that hash, the existing NMS TEST validation record, the reviewed Sunrise pin, the remote DLL provenance/x64 PE and the candidate file manifest. Games/Core still running cause refusal. Backups are verified before replacement; staged files are closed before atomic promotion. A failure rolls back completed replacements. Multiple files are not a single filesystem transaction; targets.json provides manual recovery after interruption.

Core/frontier and project code/docs are consolidated into the existing Frontier root so the already working NMS Python import location remains valid. Exactly the two NMS mods frontier_nms_probe.py and frontier_spatial_probe.py should be enabled from the specified directory; remove/disable other old spatial-copy filenames in the loader if any. Keep the validated adjacent runtime-validation.json unchanged. No package-wide copy over Saves/Config is needed.

The legacy frontier_probe.lua may remain for its old phase display; this native architecture does not require it. Do not install a new EDZ controller. Choose an ordinary non-Frontier-controlled activity for acceptance.

Then follow Documentation/RUNTIME_ACCEPTANCE.md in one session. StartFrontier.cmd enables the host-operated Scout Link; preserve your already proven game/loader launch procedure. To use ordinary preserved bridge mode, start python -m frontier.probe without --scout-link with Core on PYTHONPATH. GuardianOff.cmd safely requests override removal. Ctrl+C stops Core and clears its command epoch; lost leases restore captured NMS baseline and the current Sunrise base setting.

Rollback, with all processes closed: restore targets.json's backup files to their recorded destinations; delete destinations whose backup entry is null. Restoring the old DLL restores its old Lua-dependent architecture, so restore the entire candidate's code set together if rolling back.
