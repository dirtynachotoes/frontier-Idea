"""CI-only packaging of the complete source + compiled native guest. No game files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
ROOT=Path(__file__).resolve().parents[1]
def x64_dll(path):
    data=path.read_bytes()
    if data[:2]!=b'MZ' or len(data)<64:raise RuntimeError('Output is not a PE DLL')
    pe=struct.unpack_from('<I',data,60)[0]
    if pe+24>len(data) or data[pe:pe+4]!=b'PE\0\0':raise RuntimeError('Invalid PE header')
    if struct.unpack_from('<H',data,pe+4)[0]!=0x8664 or not struct.unpack_from('<H',data,pe+22)[0]&0x2000:raise RuntimeError('Expected Windows x64 DLL')
def package(build,output):
    build=Path(build).resolve();output=Path(output).resolve()
    if output.exists():raise RuntimeError('Candidate destination must be new')
    dll=build/'steam_api64.dll';x64_dll(dll)
    source=build.parents[2] # .../Sunrise-Probe/build/x64/Release -> Sunrise-Probe
    if not (source/'Sunrise/src/client/frontier/frontier_native.cpp').exists():raise RuntimeError('Native guest patched source missing')
    excluded={'.git','__pycache__','Sunrise-Probe','Native-Contract-Build','DestinyFrontier','Saves','Backups','Logs','Source'}
    output.mkdir()
    for path in ROOT.iterdir():
        if path.name in excluded:continue
        if path.is_dir():shutil.copytree(path,output/path.name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        else:shutil.copy2(path,output/path.name)
    dest=output/'Adapters/Sunrise/Native';dest.mkdir()
    for name in ('steam_api64.dll','steam_api64.pdb'):
        if (build/name).exists():shutil.copy2(build/name,dest/name)
    shutil.copytree(source,output/'Source/Sunrise',ignore=shutil.ignore_patterns('.git','build','__pycache__'))
    lock=json.loads((ROOT/'Native/source-lock.json').read_text())
    record=dict(frontier_commit=os.environ.get('GITHUB_SHA','LOCAL_TEST_ONLY'),sunrise_commit=lock['commit'],
                run_url='https://github.com/'+os.environ.get('GITHUB_REPOSITORY','UNSET')+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID','UNSET'),
                dll_sha256=hashlib.sha256(dll.read_bytes()).hexdigest(),runtime_accepted=False)
    (dest/'build.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    hashes={str(p.relative_to(output)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob('*') if p.is_file()}
    (output/'Documentation/CANDIDATE_HASHES.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
    print('One consolidated Windows x64 candidate: '+str(output))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sunrise-output',required=True);p.add_argument('--output',required=True);a=p.parse_args();package(a.sunrise_output,a.output)
