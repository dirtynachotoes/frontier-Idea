"""Apply the complete milestone to a clean reviewed SOURCE checkout. Never builds/installs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
ROOT=Path(__file__).resolve().parents[1]
def prepare(checkout):
    checkout=Path(checkout).resolve()
    lock=json.loads((ROOT/'Native/source-lock.json').read_text())
    def git(*args):return subprocess.check_output(['git','-C',str(checkout),*args],text=True).strip()
    if git('rev-parse','HEAD')!=lock['commit']:raise RuntimeError('Wrong reviewed Sunrise commit')
    if git('status','--porcelain'):raise RuntimeError('Use a clean disposable source checkout')
    for path,digest in lock['files'].items():
        if hashlib.sha256((checkout/path).read_bytes()).hexdigest()!=digest:raise RuntimeError('Reviewed source changed: '+path)
    patch=ROOT/'Native/Sunrise.patch'
    subprocess.run(['git','-C',str(checkout),'apply','--check',str(patch)],check=True)
    subprocess.run(['git','-C',str(checkout),'apply',str(patch)],check=True)
    dest=checkout/'Sunrise/src/client/frontier';dest.mkdir()
    for path in (ROOT/'Native').glob('frontier_*.h'):shutil.copy2(path,dest/path.name)
    shutil.copy2(ROOT/'Native/frontier_native.cpp',dest/'frontier_native.cpp')
    shutil.copy2(ROOT/'Adapters/Sunrise/frontier_probe.h',checkout/'Sunrise/src/server/activity/mission/frontier_probe.h')
    print('Complete native Frontier source prepared. No compilation or installation performed.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('checkout');a=p.parse_args();prepare(a.checkout)
