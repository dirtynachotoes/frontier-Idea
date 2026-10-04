# Heartbeat repair — lightweight install

Extract the NEW DestinyFrontier-heartbeat-fixed.zip separately. Open ordinary PowerShell in its DestinyFrontier folder. No administrator rights, pip packages, Visual Studio or Sunrise build are needed.

```powershell
$env:PYTHONPATH = Join-Path $PWD.Path 'Core'
python -m compileall -q Core Adapters Tools Tests
python -m unittest discover -s Tests -v
```

Expected Windows result for this corrected package: 47 tests, OK, no intentional skips. Linux result is 45 pass, two Windows-only skips. The user previously observed all 46 tests in the pre-correction heartbeat package pass on native Windows; the added 47th test is a static regression check that preserves the actually loaded adapter's adjacent runtime-validation.json fallback, so this corrected package still needs its own Windows run.

## Guarded source update

The updater defaults to a read-only comparison. Enter your EXISTING DestinyFrontier project folder containing the running Core, and the full path to the NMS adapter actually loaded by NMSpy. Paths with spaces are supported. Neither value is guessed.

```powershell
$coreRoot = Read-Host 'Existing DestinyFrontier folder containing Core'
$nmsAdapter = Read-Host 'Full path to the actually loaded frontier_nms_probe.py'
python Tools\apply_heartbeat_fix.py --core-root "$coreRoot" --nms-adapter "$nmsAdapter"
```

If any destination differs from the guarded SHA-256, the tool refuses before changing anything. This corrected package uses the SHA-256 of the actually loaded NMS adapter supplied after the first dry-run refusal and preserves its adjacent runtime-validation.json fallback. Any later mismatch still requires review of the actual file. There is no force option. Do not replace local changes blindly.

After the dry-run passes, stop Frontier Core and fully close NMS and offline Destiny. Do not hot-reload the NMS mod. Then:

```powershell
python Tools\apply_heartbeat_fix.py --core-root "$coreRoot" --nms-adapter "$nmsAdapter" --apply
```

Only Core/frontier/ipc.py, Core/frontier/probe.py and the supplied loaded NMS adapter path change. Every original is backed up and hash-verified before the first replacement, under the existing project's Backups/heartbeat-source-<id>; targets.json records destinations. Each changed file is staged next to its destination and closed before promotion. The tool does not verify process shutdown itself; close them first. Three-file replacement is not an atomic transaction; if interrupted/failing, restore ALL three originals from that printed backup before restarting. Do not mix old/new Core copies or overwrite Saves/Config/native game data.

Run the lightweight suite from the new package and then restart using your already proven game/loader/core setup, with the updated Core import path. No new loader or native hook setup is required. Verify manual pulse -> visible phase and region event -> speed again. Check Frontier IPC status and heartbeat ages to distinguish contention from real loss. See HEARTBEAT_FIXES.md and Documentation/WINDOWS_ACCEPTANCE.md.

To undo, while processes are closed, restore the three saved originals to the corresponding paths in targets.json. Keep canonical/native saves unchanged. No DLL/controller rollback is needed because neither was altered.
