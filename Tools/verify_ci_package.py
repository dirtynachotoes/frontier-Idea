"""Lightweight Python/static preflight; NEVER invokes a C++ compiler or a game."""
import ast
import ctypes
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Core'))
from frontier.spatial import SLOT,HEADER,SIZE
from frontier.control import CORE,NATIVE
class Slot(ctypes.LittleEndianStructure):
    _fields_=[('heartbeat',ctypes.c_uint64),('incarnation',ctypes.c_uint64),('sequence',ctypes.c_uint32),('flags',ctypes.c_uint32),('context',ctypes.c_uint64),('playerPosition',ctypes.c_float*3),('cameraPosition',ctypes.c_float*3),('forward',ctypes.c_float*3),('up',ctypes.c_float*3),('right',ctypes.c_float*3),('reserved',ctypes.c_ubyte*36)]
def validate():
    assert ctypes.sizeof(Slot)==SLOT.size==128 and HEADER.size==64 and SIZE==320
    assert CORE.size==NATIVE.size==64
    expected=dict(heartbeat=0,incarnation=8,sequence=16,flags=20,context=24,playerPosition=32,cameraPosition=44,forward=56,up=68,right=80,reserved=92)
    assert {name:getattr(Slot,name).offset for name in expected}==expected
    for base in ('Core','Adapters','Tools','Tests'):
        for path in (ROOT/base).rglob('*.py'):ast.parse(path.read_text(encoding='utf-8'),feature_version=(3,10))
    native=(ROOT/'Native/frontier_native.cpp').read_text();patch=(ROOT/'Native/Sunrise.patch').read_text()
    assert 'client::frontier::tick();' in patch and 'frontier::observe_region(' in patch
    assert 'movement::set_frontier_hover(' in native and 'player::position::component()' in native
    assert 'owns_local_player(component)' in native and 'player::position::snapshot()' in native
    assert 'read_position(' not in native and 'guardian_ready(' in native
    assert 'CreateThread' not in native and 'edz_freeroam' not in native
    assert 'runtime_get()' in patch and 'g_frontierHoverUntil' in patch
    assert 'COMPILE_OPTIONS "/WX"' in patch
    assert 'constexpr wchar_t' not in native and 'bridgeName' in native
    workflow=(ROOT/'.github/workflows/build-sunrise-spatial.yml').read_text()
    assert '--parallel 1' in workflow and 'windows-2025-vs2026' in workflow
    lock=json.loads((ROOT/'Documentation/PRESERVED_HASHES.json').read_text())
    for path,digest in lock.items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest, path
    print('PASS: V2 offsets/128 bytes, control ABI, Python 3.10 grammar, native seams, bounded remote CI, preserved bridge hashes')
if __name__=='__main__':validate()
