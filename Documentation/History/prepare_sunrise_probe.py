"""Produce an isolated patch workspace; never alter a supplied game installation."""
import argparse
from pathlib import Path
import shutil
import subprocess

PIN = '1da7f7a86cbfbe5c92dc91287594d0ac6c70eb1c'
parser = argparse.ArgumentParser()
parser.add_argument('checkout', type=Path)
args = parser.parse_args()
root = args.checkout.resolve()
if subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip() != PIN:
    raise SystemExit('Refused: Sunrise commit differs from reviewed pin')
if subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True).strip():
    raise SystemExit('Refused: use a clean disposable checkout')
file = root / 'Sunrise/src/server/activity/mission/mission_script_lua_sandbox.cpp'
text = file.read_text()
needle = '    world_api::register_metatables(state);\n    return 0;'
if text.count(needle) != 1:
    raise SystemExit('Refused: registration site changed')
text = '#include "frontier_probe.h"\n' + text.replace(needle, '    world_api::register_metatables(state);\n    destiny_frontier_probe::install(state);\n    return 0;')
source = Path(__file__).resolve().parents[1] / 'Adapters/Sunrise/frontier_probe.h'
shutil.copyfile(source, file.parent / 'frontier_probe.h')
file.write_text(text)
print('Prepared uncompiled Sunrise TEST binding. Build this disposable checkout using CMake. NOT runtime-verified.')
