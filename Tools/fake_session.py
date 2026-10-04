"""One isolated fake-host/fake-guest session against the REAL Core. No games/hooks.
The simulated guest tests routing only; Tests/Native tests the actual C++ guest policy.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Core'))
from frontier.ipc import Mapping,HEADER,STATE,OFFSETS,ticks
from frontier.control import ControlMapping,CORE,NATIVE
from frontier.spatial import SpatialMapping

def run_session():
    with tempfile.TemporaryDirectory(prefix='frontier-fake-') as td:
        folder=Path(td);stop=folder/'stop';transport=folder/'bridge';commands=folder/'control'
        env=dict(os.environ,PYTHONPATH=str(ROOT/'Core'))
        with open(folder/'core.log','w+',encoding='utf-8') as output:
            proc=subprocess.Popen([sys.executable,'-m','frontier.probe','--database',str(folder/'probe.sqlite3'),
                                   '--test-file',str(transport),'--control-file',str(commands),'--test-stop-file',str(stop),'--scout-link'],env=env,stdout=output,stderr=subprocess.STDOUT)
            try:
                with Mapping(transport) as bridge,ControlMapping(commands) as control,SpatialMapping(folder/'spatial') as spatial:
                    nms_seq=sunrise_seq=0;ack=0;hover=False;targets=set();request_seen=False
                    deadline=time.monotonic()+8;last_count=0
                    while time.monotonic()<deadline:
                        if proc.poll() is not None:raise RuntimeError('Core exited: '+str(proc.returncode))
                        now=ticks()
                        spatial.publish('nms',101,nms_seq,player=(1,2,3),forward=(0,0,-1))
                        spatial.publish('sunrise',202,sunrise_seq,30,player=(4,5,6))
                        with control.locked() as acquired:
                            if acquired:
                                c=CORE.unpack_from(control.memory)
                                if c[6]!=ack and c[4] and c[10]&1:
                                    ack=c[6];hover=c[9]==1;request_seen=True
                                NATIVE.pack_into(control.memory,64,now,202,30,ack,1,1 if ack else 0,int(hover),0,101,nms_seq)
                        result=bridge.exchange('nms',101,nms_seq,True)
                        bridge.exchange('sunrise',202,sunrise_seq,True)
                        if result and result[2]:targets.add(result[1])
                        if last_count==0 and result and result[2]:nms_seq=1;sunrise_seq=1;last_count=1
                        if hover and result and result[1]==1 and last_count==1:nms_seq=2;last_count=2
                        if request_seen and ack>=2 and not hover and result and result[1]==0:break
                        time.sleep(.01)
                    else:raise RuntimeError('Fake routing did not complete')
                    assert targets=={0,1} and ack>=2
                    stop.touch();proc.wait(timeout=5)
                    assert proc.returncode==0
                    assert not control.status()['core_valid']
                    with bridge.locked() as acquired:
                        assert acquired and HEADER.unpack_from(bridge.memory)[2]==0
                # Real Core/store persistence, not a fake native game save.
                from frontier.store import Store
                with Store(folder/'probe.sqlite3') as store:
                    assert store.totals()['nms']==2 and store.totals()['sunrise']==1
            finally:
                if proc.poll() is None:
                    stop.touch()
                    try:proc.wait(timeout=5)
                    finally:
                        if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
            output.seek(0);events=[json.loads(line) for line in output if line.startswith('{')]
            assert any(x['event']=='guardian_hover_requested' for x in events)
    print('PASS: REAL Core + FAKE NMS/Sunrise endpoints, both directions, on/off result, graceful shutdown and Core persistence; no games')
if __name__=='__main__':run_session()
