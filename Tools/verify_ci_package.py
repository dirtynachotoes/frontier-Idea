from pathlib import Path
import ctypes
import hashlib
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
header = ROOT / "Adapters/Sunrise/frontier_probe.h"
text = header.read_text(encoding="utf-8")

class CSpatialSlot(ctypes.Structure):
    _fields_ = [
        ("heartbeat", ctypes.c_uint64),
        ("incarnation", ctypes.c_uint64),
        ("sequence", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("context", ctypes.c_uint64),
        ("playerPosition", ctypes.c_float * 3),
        ("cameraPosition", ctypes.c_float * 3),
        ("forward", ctypes.c_float * 3),
        ("up", ctypes.c_float * 3),
        ("right", ctypes.c_float * 3),
        ("reserved", ctypes.c_ubyte * 36),
    ]

errors = []
if ctypes.sizeof(CSpatialSlot) != 128:
    errors.append(f"SpatialSlot natural layout is {ctypes.sizeof(CSpatialSlot)}, expected 128")
for needle in [
    "static_assert(sizeof(SpatialSlot) == 128);",
    "client::player::position::snapshot()",
    "client::hooks::teleport::camera_pose(camera)",
]:
    if needle not in text:
        errors.append(f"missing: {needle}")

wf = (ROOT / ".github/workflows/build-sunrise-spatial.yml").read_text(encoding="utf-8")
if "--parallel 1" not in wf:
    errors.append("workflow is missing bounded --parallel 1 build")
if "workflow_dispatch" not in wf:
    errors.append("workflow is not manual-dispatch only")

if errors:
    print("CI PREFLIGHT FAILED")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print("CI PREFLIGHT PASSED")
print("SpatialSlot natural layout: 128 bytes")
print("Workflow: manual dispatch only")
print("Remote build: bounded --parallel 1")
print("Header SHA256:", hashlib.sha256(header.read_bytes()).hexdigest())
