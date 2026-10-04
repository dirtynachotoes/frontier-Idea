"""Actual adapter callbacks with fake typed player methods; no game or engine emulation."""
import ast
import ctypes as c
import logging
from pathlib import Path
import secrets
import time
from types import SimpleNamespace as NS
import unittest
from frontier.ipc import ticks
class V(c.Structure):_fields_=[('x',c.c_float),('y',c.c_float),('z',c.c_float)]
class Big(c.Structure):_fields_=[('local',V),('offset',V)]
class Matrix(c.Structure):_fields_=[('at',V),('pos',Big)]
class Player(c.Structure):
    _fields_=[('mGraphicsMatrix',Matrix),('mbSpawned',c.c_bool),('mbIsTransitioning',c.c_bool),('mbIsDying',c.c_bool)]
    def SetToPosition(self,p,d,v):
        self.applied=(Big.from_buffer_copy(c.cast(p,c.POINTER(Big)).contents),V.from_buffer_copy(c.cast(v,c.POINTER(V)).contents))
class Motion:
    armed=True;valid_until=0;last_result=(0,)*10
    keys=NS(focused=lambda:True)
    def exchange(self,inc,status):self.valid_until=ticks()+2000;return self.delta
    def close(self):self.armed=False
class NMSMotionTests(unittest.TestCase):
    def make(self,delta):
        path=Path(__file__).resolve().parents[1]/'Adapters/NMS/frontier_spatial_probe.py'
        cls=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.ClassDef))
        for f in cls.body:
            if isinstance(f,ast.FunctionDef):f.decorator_list=[]
        player=Player(Matrix(V(0,0,-1),Big(V(10,20,30),V(1000,2000,3000))),True,False,False)
        ns=dict(Mod=object,ctypes=c,basic=NS(cTkBigPos=Big,cTkVector3=V),gameData=NS(player=player),HostKey=lambda:None,secrets=secrets,log=logging.getLogger('fake-motion'),time=time,ticks=ticks)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),str(path),'exec'),ns)
        adapter=ns[cls.name]();adapter.control=NS(status=lambda:{})
        adapter.motion_host=Motion();adapter.motion_host.delta=delta
        return adapter,player,c.pointer(player)
    def test_actual_guest_delta_overrides_host_step_preserving_offset(self):
        a,p,ptr=self.make((2,3,-4));a.motion_before(ptr,0.016)
        p.mGraphicsMatrix.pos.local=V(999,999,999) # host original Update's unrelated motion
        a.motion_after(ptr,0.016)
        pos,vel=p.applied
        self.assertEqual((pos.local.x,pos.local.y,pos.local.z),(12,23,26))
        self.assertEqual((pos.offset.x,pos.offset.y,pos.offset.z),(1000,2000,3000))
        self.assertEqual((vel.x,vel.y,vel.z),(0,0,0))
        a.motion_after(ptr,0.016);self.assertIsNone(a.motion_base)
    def test_absent_guest_result_never_acts(self):
        a,p,ptr=self.make(None);a.motion_before(ptr,0.016);a.motion_after(ptr,0.016)
        self.assertFalse(hasattr(p,'applied'))
    def test_transition_and_expiry_between_callbacks_reject_actuation(self):
        for reason in ('transition','expired','focus'):
            a,p,ptr=self.make((1,0,0));a.motion_before(ptr,0.016)
            if reason=='transition':p.mbIsTransitioning=True
            elif reason=='expired':a.motion_base=(a.motion_base[0],a.motion_base[1],ticks()-1)
            else:a.motion_host.keys=NS(focused=lambda:False)
            a.motion_after(ptr,0.016);self.assertFalse(hasattr(p,'applied'),reason)
    def test_foreign_player_ignored(self):
        a,p,ptr=self.make((1,0,0));foreign=Player();a.motion_before(c.pointer(foreign),0.016)
        self.assertIsNone(a.motion_base)
