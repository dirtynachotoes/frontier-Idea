# Lightweight validation only

No Sunrise compilation, C++ build, hook installation or game launch is part of this repair. Standard-library Python source only; no consumer EXE.

From the new package root, ordinary PowerShell:

```powershell
$env:PYTHONPATH = Join-Path $PWD.Path 'Core'
python -m compileall -q Core Adapters Tools Tests
python -m unittest discover -s Tests -v
```

RunLightweightTests.cmd remains available for CMD. Linux CPython 3.12.14: 45 pass, two native Windows skips, 47 total. Python 3.10 syntax passes; actual Windows/Python 3.10 execution not available. The existing bridge actuation was verified by the user on Windows before this change; this does not validate this repair. See INSTALL.md for guarded three-file deployment, not a heavyweight build.
