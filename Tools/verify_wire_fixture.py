import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Core'))
from frontier.spatial import SLOT
p=argparse.ArgumentParser();p.add_argument('fixture',type=Path);a=p.parse_args()
expected=SLOT.pack(0x1122334455667788,0x8877665544332211,0x12345678,31,0x1020304050607080,*range(1,16))
if a.fixture.read_bytes()!=expected:raise SystemExit('FAIL: C++/Python wire bytes differ')
from frontier.control import CORE,NATIVE
expected_control=CORE.pack(0x43465444,1,128,64,1,2,3,4,5,1,3)+NATIVE.pack(6,7,8,9,1,1,1,0,10,11)
if Path(str(a.fixture)+'.control').read_bytes()!=expected_control:raise SystemExit('FAIL: control wire bytes differ')
print('PASS: exact C++/Python 128-byte spatial AND control wire fixtures')
