# Destiny Frontier Sunrise spatial probe — CI build package

This package is for **remote GitHub Actions compilation** so the gaming PC does not
compile Sunrise locally.

## Mandatory local check (lightweight, no C++ compilation)

```powershell
python Tools\verify_ci_package.py
```

Expected:

```text
CI PREFLIGHT PASSED
SpatialSlot natural layout: 128 bytes
Workflow: manual dispatch only
Remote build: bounded --parallel 1
```

## Use

Create a small GitHub repository and copy the contents of this package into it,
including the hidden `.github` folder. Push it.

In GitHub:
1. Open **Actions**.
2. Select **Build Sunrise Frontier Spatial Probe**.
3. Choose **Run workflow**.
4. Wait for the remote Windows job to finish.
5. Download artifact **Sunrise-Frontier-Spatial-Release-x64**.

The workflow:
- clones the reviewed Sunrise pin `1da7f7a86cbfbe5c92dc91287594d0ac6c70eb1c`
- refuses a different revision
- patches only a disposable checkout
- builds Release x64 remotely with `--parallel 1`
- uploads `steam_api64.dll`, PDB and SHA-256 JSON

Do not run CMake/MSVC locally on the gaming PC for this project unless explicitly
choosing to override the no-local-build rule.
