"""Execute the actual NMS adapter methods with explicit fake framework/player inputs."""
import ast
from pathlib import Path
import secrets
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
import logging
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Core'))
from frontier.spatial import SpatialMapping
class FakeKey:
    def __init__(self):self.edge=False
    def pressed(self):result=self.edge;self.edge=False;return result
class FakeControl:
    def status(self):return dict(core_valid=True,scout_link=True)
    def close(self):pass
class NMSSpatialTests(unittest.TestCase):
    def test_real_methods_publish_v2_and_latch_short_host_key(self):
        path=Path(__file__).resolve().parents[1]/'Adapters/NMS/frontier_spatial_probe.py'
        cls=next(x for x in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(x,ast.ClassDef))
        for method in cls.body:
            if isinstance(method,ast.FunctionDef):method.decorator_list=[]
        vec=lambda x,y,z:SimpleNamespace(x=x,y=y,z=z)
        player=SimpleNamespace(mPosition=vec(1,2,3),mGraphicsMatrix=SimpleNamespace(at=vec(0,0,1),up=vec(0,1,0),right=vec(1,0,0)))
        with tempfile.TemporaryDirectory() as td,SpatialMapping(Path(td)/'spatial') as mapping:
            namespace=dict(Mod=object,Path=Path,__file__=str(Path(td)/'mod.py'),time=time,secrets=secrets,gameData=SimpleNamespace(player=player),SpatialMapping=SpatialMapping,ControlMapping=FakeControl,HostKey=FakeKey,log=logging.getLogger('fake-spatial'))
            exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),str(path),'exec'),namespace)
            adapter=namespace[cls.name]();adapter.mapping=mapping;adapter.control=FakeControl()
            adapter.last_poll=time.monotonic();adapter.key.edge=True;adapter.update(None)
            self.assertTrue(adapter.pulse_pending);self.assertFalse(Path(td,'frontier_pulse.trigger').exists())
            adapter.last_poll=0;adapter.update(None)
            self.assertTrue(Path(td,'frontier_pulse.trigger').exists());self.assertFalse(adapter.pulse_pending)
            slot=mapping.snapshot()['nms'];self.assertEqual(slot[3],29);self.assertEqual(slot[5:8],(1,2,3));self.assertEqual(slot[11:14],(0,0,-1))
