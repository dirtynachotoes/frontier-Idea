"""Single backed-up install into explicitly selected, CLOSED offline/test installations.
No builds, process launches, mission-controller replacement or native-save writes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
ROOT=Path(__file__).resolve().parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def promote(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent,prefix='.frontier-',delete=False) as file:
        staged=Path(file.name)
        with source.open('rb') as original:shutil.copyfileobj(original,file)
        file.flush();os.fsync(file.fileno())
    try:os.replace(staged,target)
    finally:
        if staged.exists():staged.unlink()
def plan(core_root,nms_mod_dir,offline_root,offline_exe_sha256):
    core=Path(core_root).resolve();mods=Path(nms_mod_dir).resolve();offline=Path(offline_root).resolve()
    for directory in (core,mods,offline):
        if not directory.is_dir():raise RuntimeError('Existing destination directory required: '+str(directory))
    validation=mods/'runtime-validation.json'
    record=json.loads(validation.read_text(encoding='utf-8'))
    if record.get('runtime_hooks_validated') is not True or record.get('test_profile') is not True:
        raise RuntimeError('Retain the already validated NMS TEST record')
    exe=offline/'destiny2.exe'
    if len(offline_exe_sha256)!=64 or digest(exe)!=offline_exe_sha256.lower():raise RuntimeError('Explicit established offline Destiny executable hash differs')
    native=ROOT/'Adapters/Sunrise/Native';build=json.loads((native/'build.json').read_text(encoding='utf-8'))
    if build['sunrise_commit']!='1da7f7a86cbfbe5c92dc91287594d0ac6c70eb1c' or build['frontier_commit']=='LOCAL_TEST_ONLY':raise RuntimeError('Use the remotely built complete candidate')
    if digest(native/'steam_api64.dll')!=build['dll_sha256']:raise RuntimeError('Native candidate hash differs')
    from package_candidate import x64_dll
    x64_dll(native/'steam_api64.dll')
    manifest=json.loads((ROOT/'Documentation/CANDIDATE_HASHES.json').read_text(encoding='utf-8'))
    for path,hash_value in manifest.items():
        if digest(ROOT/path)!=hash_value:raise RuntimeError('Candidate content changed: '+path)
    targets=[]
    for folder in ('Core','Adapters','Native','Tests','Tools','Documentation'):
        for path in (ROOT/folder).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix!='.pyc':
                target=core/path.relative_to(ROOT)
                if path.resolve()!=target:targets.append((path,target))
    for path in ROOT.iterdir():
        if path.is_file() and path.suffix in ('.md','.cmd'):
            target=core/path.name
            if path.resolve()!=target:targets.append((path,target))
    for name in ('frontier_nms_probe.py','frontier_spatial_probe.py'):targets.append((ROOT/'Adapters/NMS'/name,mods/name))
    targets.append((native/'steam_api64.dll',offline/'steam_api64.dll'))
    # Deduplicate a mod folder that is also Core/Adapters/NMS.
    unique={str(t):(s,t) for s,t in targets if s.resolve()!=t.resolve()}
    return list(unique.values()),build

def install(targets,backup_root):
    backup=Path(backup_root)/('native-guest-'+uuid.uuid4().hex);backup.mkdir(parents=True)
    records=[]
    for index,(source,target) in enumerate(targets):
        if target.exists():
            saved=backup/str(index);shutil.copy2(target,saved)
            if digest(saved)!=digest(target):raise RuntimeError('Backup verification failed')
        else:saved=None
        records.append(dict(target=str(target),backup=str(saved) if saved else None,source_sha256=digest(source)))
    (backup/'targets.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    completed=[]
    try:
        for (source,target),record in zip(targets,records):
            completed.append(record);promote(source,target)
            if digest(target)!=record['source_sha256']:raise RuntimeError('Install verification failed')
    except BaseException:
        for record in reversed(completed):
            target=Path(record['target'])
            if record['backup']:promote(Path(record['backup']),target)
            elif target.exists():target.unlink()
        raise
    print('Installed one complete candidate; backup: '+str(backup))
def require_closed():
    if os.name!='nt':raise RuntimeError('Installation is Windows-only')
    # Conservatively refuse either game or another Frontier Core; no guessed game addresses.
    command="$p=Get-CimInstance Win32_Process; $p | Where-Object { $_.Name -in @('destiny2.exe','NMS.exe') -or $_.CommandLine -match 'frontier\\.probe' } | ForEach-Object { $_.ProcessId }"
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],text=True,capture_output=True,check=True)
    # Our own installer command line has no frontier.probe string, so no self-match.
    if result.stdout.strip():raise RuntimeError('Close Core and both games before the ONE candidate install')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--core-root',required=True);p.add_argument('--nms-mod-dir',required=True)
    p.add_argument('--offline-root',required=True);p.add_argument('--offline-exe-sha256',required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
    targets,build=plan(a.core_root,a.nms_mod_dir,a.offline_root,a.offline_exe_sha256)
    print(json.dumps(dict(candidate=build,files=len(targets),destinations=sorted({str(t.parent) for _,t in targets})),indent=2))
    if a.apply:require_closed();install(targets,Path(a.core_root)/'Backups')
    else:print('Read-only plan. Add --apply for the single consolidated installation.')
