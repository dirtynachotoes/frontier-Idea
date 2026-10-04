"""Prepare a clean pinned Sunrise checkout with the Destiny Frontier spatial probe.

This script is intended for a disposable CI checkout only.
"""
import argparse
from pathlib import Path
import shutil
import subprocess

PIN = "1da7f7a86cbfbe5c92dc91287594d0ac6c70eb1c"

parser = argparse.ArgumentParser()
parser.add_argument("checkout", type=Path)
args = parser.parse_args()
root = args.checkout.resolve()

head = subprocess.check_output(
    ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
).strip()
if head != PIN:
    raise SystemExit(f"Refused: Sunrise commit {head} differs from reviewed pin {PIN}")

if subprocess.check_output(
    ["git", "-C", str(root), "status", "--porcelain"], text=True
).strip():
    raise SystemExit("Refused: use a clean disposable Sunrise checkout")

sandbox = root / "Sunrise/src/server/activity/mission/mission_script_lua_sandbox.cpp"
text = sandbox.read_text(encoding="utf-8")
needle = "    world_api::register_metatables(state);\n    return 0;"
if text.count(needle) != 1:
    raise SystemExit("Refused: mission sandbox registration site changed")

patched = '#include "frontier_probe.h"\n' + text.replace(
    needle,
    "    world_api::register_metatables(state);\n"
    "    destiny_frontier_probe::install(state);\n"
    "    return 0;"
)

source = Path(__file__).resolve().parents[1] / "Adapters/Sunrise/frontier_probe.h"
shutil.copyfile(source, sandbox.parent / "frontier_probe.h")
sandbox.write_text(patched, encoding="utf-8")
print("Prepared clean pinned Sunrise checkout with Frontier spatial probe.")
