import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Core'))
from frontier.spatial import SLOT
p=argparse.ArgumentParser();p.add_argument('fixture',type=Path);a=p.parse_args()
expected=SLOT.pack(0x1122334455667788,0x8877665544332211,0x12345678,31,0x1020304050607080,*range(1,16))
if a.fixture.read_bytes()!=expected:raise SystemExit('FAIL: C++/Python wire bytes differ')
from frontier.control import CORE,NATIVE,readiness_status
expected_control=CORE.pack(0x43465444,1,128,64,1,2,3,4,5,1,3)+NATIVE.pack(6,7,8,9,1,1,1,0,10,11)
if Path(str(a.fixture)+'.control').read_bytes()!=expected_control:raise SystemExit('FAIL: control wire bytes differ')
from frontier.ipc import NAME as bridge_name
from frontier.spatial import NAME as spatial_name
from frontier.control import NAME as control_name
expected_names=''.join(name+'\n'+name+'_mutex\n' for name in (bridge_name,spatial_name,control_name)).encode('ascii')
if Path(str(a.fixture)+'.names').read_bytes()!=expected_names:raise SystemExit('FAIL: actual compiled C++/Python IPC names differ')
print('PASS: exact C++/Python spatial/control wire fixtures AND actual compiled IPC mapping/mutex names')

expected_diagnostic=CORE.pack(0x43465444,1,128,64,1,2,3,4,5,1,3)+NATIVE.pack(6,7,8,9,1,1,1,0x800000ff,10,11)
actual_diagnostic=Path(str(a.fixture)+'.diagnostics').read_bytes()
if actual_diagnostic!=expected_diagnostic:raise SystemExit('FAIL: native diagnostic word/layout differs')
bits=NATIVE.unpack_from(actual_diagnostic,64)[7]
fields=readiness_status(bits)
if not all(fields[name] is True for name in ('readiness_diagnostics','ready_in_world','ready_component','ready_ownership','ready_snapshot','ready_finite','ready_combined','ready_host','ready_ownership_checked')):
    raise SystemExit('FAIL: native readiness diagnostics decode differs')
print('PASS: native C++/Python diagnostic fixture at unchanged offset 108 and 128-byte ABI')

from frontier.motion import HEADER as MOTION_HEADER,INTENT,RESULT
expected_motion=MOTION_HEADER.pack(0x4D465444,1,256,64,7,10000,1)+INTENT.pack(10000,99,1,1,3)*2+RESULT.pack(10000,50,3,4,1,2,3,1,12,5)
if Path(str(a.fixture)+'.motion').read_bytes()!=expected_motion:raise SystemExit('FAIL: motion wire bytes differ')
print('PASS: independent motion channel C++/Python 256-byte exact fixture; legacy Control/Spatial unchanged')
