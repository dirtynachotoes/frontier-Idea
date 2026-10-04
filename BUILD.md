# One remote build

Repository: https://github.com/dirtynachotoes/frontier-Idea . The earlier successful spatial run https://github.com/dirtynachotoes/frontier-Idea/actions/runs/37177567768 is closed and is not an installation candidate for this milestone.

The existing workflow path .github/workflows/build-sunrise-spatial.yml is replaced by **Build Destiny Frontier Native Guest**. The final code commit triggers one push build on main; manual dispatch remains available only as a fallback if that build cannot be triggered and uses the previously successful windows-2025-vs2026 runner. Every CMake build uses --parallel 1, and CMAKE_BUILD_PARALLEL_LEVEL=1. No Sunrise compilation belongs on the gaming PC.

Do not dispatch a duplicate if the final commit already started its build. If Work cannot start it, the exactly one next build action after the canonical commit is in main: open Actions → Build Destiny Frontier Native Guest → Run workflow (main). CI runs Python 3.10 static/unit/fake checks, real Windows mutex checks, the small native contract harness and exact C++/Python wire-fixture comparison. It then clones Sunrise at 1da7f7a86cbfbe5c92dc91287594d0ac6c70eb1c, uses an LF-preserving source checkout and verifies each patched file SHA against Native/source-lock.json, applies the complete integration patch, and builds Release x64 remotely.

One artifact, **DestinyFrontier-Windows-x64**, contains the canonical Frontier tree, the complete patched matching Sunrise source under Source/Sunrise, the compiled DLL/PDB under Adapters/Sunrise/Native, DLL SHA/build provenance and one candidate file-hash manifest. No commercial game files are packaged. Install only that whole candidate after CI succeeds, once.

To reproduce source preparation without compiling: Tools/prepare_sunrise_frontier.py <clean pinned source checkout>. This modifies only that disposable source tree. Wrong revision, dirty tree or reviewed-file hash differences are refused before patch application. For maintenance, update reviewed pins/patches together; never loosen the guards to get green CI.

RunLightweightTests.cmd runs Python checks only. Tools/fake_session.py exercises the actual Core with explicitly fake endpoints. The native contract CMake project is intended for remote CI; no local Sunrise build command is included in the user workflow.
