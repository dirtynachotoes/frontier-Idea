"""Actual adapter callbacks with fake typed player structures; no game or engine emulation."""
import ast
import ctypes as c
import json
import logging
import math
from pathlib import Path
import secrets
import time
from types import SimpleNamespace as NS
import unittest
from frontier.ipc import ticks
class V(c.Structure):_fields_=[('x',c.c_float),('y',c.c_float),('z',c.c_float)]
class Big(c.Structure):_fields_=[('local',V),('offset',V)]
class Matrix(c.Structure):_fields_=[('right',V),('up',V),('at',V),('pos',Big)]
class Controller(c.Structure):_fields_=[('mTargetVelocity',V)]
class Player(c.Structure):
    _fields_=[('mGraphicsMatrix',Matrix),('mPosition',V),('mPhysicsController',c.POINTER(Controller)),
              ('mbSpawned',c.c_bool),('mbIsTransitioning',c.c_bool),('mbIsDying',c.c_bool)]
    def SetToPosition(self,p,d,v):self.teleported=True
class Motion:
    armed=True;valid_until=0;last_result=(0,)*10
    keys=NS(focused=lambda:True)
    def exchange(self,inc,status):self.valid_until=ticks()+2000;return self.delta
    def close(self):self.armed=False
class NMSMotionTests(unittest.TestCase):
    def make(self,delta,target=(5,-9.8,5)):
        path=Path(__file__).resolve().parents[1]/'Adapters/NMS/frontier_spatial_probe.py'
        cls=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.ClassDef))
        for f in cls.body:
            if isinstance(f,ast.FunctionDef):f.decorator_list=[]
        self.controller=Controller(V(*target))
        player=Player(Matrix(V(1,0,0),V(0,1,0),V(0,0,-1),Big(V(10,20,30),V(1000,2000,3000))),V(10,20,30),c.pointer(self.controller),True,False,False)
        ns=dict(Mod=object,ctypes=c,math=math,json=json,Path=Path,basic=NS(cTkBigPos=Big,cTkVector3=V),gameData=NS(player=player),HostKey=lambda:None,secrets=secrets,log=logging.getLogger('fake-motion'),time=time,ticks=ticks)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),str(path),'exec'),ns)
        adapter=ns[cls.name]();adapter.control=NS(status=lambda:{})
        adapter.motion_trace=lambda *a:None
        adapter.motion_host=Motion();adapter.motion_host.delta=delta
        return adapter,player,c.pointer(player)
    def velocity(self):
        v=self.controller.mTargetVelocity;return (round(v.x,3),round(v.y,3),round(v.z,3))
    def test_guardian_horizontal_velocity_replaces_host_intent_keeping_host_vertical(self):
        a,p,ptr=self.make((0.3,0.6,0));a.motion_before(ptr,0.016);a.motion_after(ptr,0.016)
        # 0.3 units in the 0.15 s window = 2 u/s horizontal; Guardian vertical is never applied.
        self.assertEqual(self.velocity(),(2.0,-9.8,0.0))
        self.assertFalse(hasattr(p,'teleported'))
        a.motion_after(ptr,0.016);self.assertIsNone(a.motion_base)
    def test_idle_armed_guardian_stops_host_horizontal_motion(self):
        a,p,ptr=self.make((0,0,0));a.motion_before(ptr,0.016);a.motion_after(ptr,0.016)
        self.assertEqual(self.velocity(),(0.0,-9.8,0.0))
    def test_absent_guest_result_never_acts(self):
        a,p,ptr=self.make(None);a.motion_before(ptr,0.016);a.motion_after(ptr,0.016)
        self.assertEqual(self.velocity(),(5.0,-9.8,5.0))
    def test_transition_and_expiry_between_callbacks_reject_actuation(self):
        for reason in ('transition','expired','focus'):
            a,p,ptr=self.make((1,0,0));a.motion_before(ptr,0.016)
            if reason=='transition':p.mbIsTransitioning=True
            elif reason=='expired':a.motion_base=(a.motion_base[0],a.motion_base[1],ticks()-1)
            else:a.motion_host.keys=NS(focused=lambda:False)
            a.motion_after(ptr,0.016);self.assertEqual(self.velocity(),(5.0,-9.8,5.0),reason)
    def test_foreign_player_ignored(self):
        a,p,ptr=self.make((1,0,0));foreign=Player();a.motion_before(c.pointer(foreign),0.016)
        self.assertIsNone(a.motion_base)
    def test_null_controller_is_ignored(self):
        a,p,ptr=self.make((1,0,0));p.mPhysicsController=c.POINTER(Controller)()
        a.motion_before(ptr,0.016);a.motion_after(ptr,0.016)
        self.assertFalse(hasattr(p,'teleported'))
