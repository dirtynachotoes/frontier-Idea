"""Actual adapter callbacks against fake typed player structures; no game or engine emulation."""
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
class Player(c.Structure):
    _fields_=[('mGraphicsMatrix',Matrix),('mPosition',V),('mbSpawned',c.c_bool),('mbIsTransitioning',c.c_bool),('mbIsDying',c.c_bool)]
    # Fake engine: the command lands at X - TRUE_OFFSET (unknown to the adapter), graphics trail by GFX.
    TRUE_OFFSET=(0.0,0.9,0.0);GFX=(0.0,1.7,0.0)
    def SetToPosition(self,p,d,v):
        x=c.cast(p,c.POINTER(Big)).contents.local
        self.commands=getattr(self,'commands',0)+1
        self.place((x.x-self.TRUE_OFFSET[0],x.y-self.TRUE_OFFSET[1],x.z-self.TRUE_OFFSET[2]))
    def place(self,pos):
        self.mPosition=V(*pos);self.mGraphicsMatrix.pos.local=V(*(a+b for a,b in zip(pos,self.GFX)))
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
            if isinstance(f,ast.FunctionDef):f.decorator_list=[d for d in f.decorator_list if isinstance(d,ast.Name) and d.id=='staticmethod']
        player=Player(Matrix(V(1,0,0),V(0,1,0),V(0,0,-1),Big(V(0,0,0),V(1000,2000,3000))),V(0,0,0),True,False,False)
        player.place((10,20,30))
        ns=dict(Mod=object,ctypes=c,math=math,json=json,Path=Path,basic=NS(cTkBigPos=Big,cTkVector3=V),gameData=NS(player=player),HostKey=lambda:None,secrets=secrets,log=logging.getLogger('fake-motion'),time=time,ticks=ticks)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),str(path),'exec'),ns)
        adapter=ns[cls.name]();adapter.control=NS(status=lambda:{})
        adapter.motion_trace=lambda *a:None
        adapter.motion_host=Motion();adapter.motion_host.delta=delta
        return adapter,player,c.pointer(player)
    def frame(self,a,p,ptr,host_step=(0,0,0)):
        a.motion_before(ptr,0.016)
        x,y,z=p.mPosition.x,p.mPosition.y,p.mPosition.z
        p.place((x+host_step[0],y+host_step[1],z+host_step[2]))  # NMS's own Update (input/gravity)
        a.motion_after(ptr,0.016)
    def pos(self,p):return tuple(round(v,3) for v in (p.mPosition.x,p.mPosition.y,p.mPosition.z))
    def test_idle_armed_never_drifts_after_first_correction(self):
        a,p,ptr=self.make((0,0,0))
        for _ in range(120):self.frame(a,p,ptr)
        self.assertEqual(self.pos(p),(10,20,30))
    def test_guardian_horizontal_steps_move_host_and_vertical_is_ignored(self):
        a,p,ptr=self.make((0.1,0.5,0))  # 0.5 vertical Guardian motion must not lift the NMS player
        self.frame(a,p,ptr)  # first frame calibrates the unknown offset
        for _ in range(10):self.frame(a,p,ptr)
        self.assertEqual(self.pos(p),(11.1,20,30))
    def test_host_own_horizontal_input_is_replaced_but_gravity_kept(self):
        a,p,ptr=self.make((0,0,0))
        for _ in range(10):self.frame(a,p,ptr,host_step=(0.3,-0.05,0))
        x,y,z=self.pos(p)
        self.assertAlmostEqual(x,10,places=2);self.assertAlmostEqual(z,30,places=2);self.assertLess(y,20)
    def test_absent_guest_result_never_acts(self):
        a,p,ptr=self.make(None);self.frame(a,p,ptr)
        self.assertFalse(hasattr(p,'commands'))
    def test_transition_and_focus_between_callbacks_reject_actuation(self):
        for reason in ('transition','expired','focus'):
            a,p,ptr=self.make((1,0,0));a.motion_before(ptr,0.016)
            if reason=='transition':p.mbIsTransitioning=True
            elif reason=='expired':a.motion_base=a.motion_base[:-1]+(ticks()-1,)
            else:a.motion_host.keys=NS(focused=lambda:False)
            a.motion_after(ptr,0.016);self.assertFalse(hasattr(p,'commands'),reason)
    def test_large_jump_disarms_instead_of_chasing(self):
        a,p,ptr=self.make((0,0,0))
        for _ in range(3):self.frame(a,p,ptr)
        p.place((500,20,30));n=p.commands
        self.frame(a,p,ptr)
        self.assertEqual(p.commands,n);self.assertIsNone(a.motion_host)
    def test_foreign_player_ignored(self):
        a,p,ptr=self.make((1,0,0));foreign=Player();a.motion_before(c.pointer(foreign),0.016)
        self.assertIsNone(a.motion_base)
class NoVerticalFeedbackTests(NMSMotionTests):
    def test_upward_push_is_not_amplified(self):
        a,p,ptr=self.make((0,0,0))
        speeds=[]
        orig=Player.SetToPosition
        def capture(self_,pp,d,v):
            speeds.append(c.cast(v,c.POINTER(V)).contents.y);orig(self_,pp,d,v)
        Player.SetToPosition=capture
        try:
            for _ in range(30):self.frame(a,p,ptr,host_step=(0,0.05,0))  # small engine push-out each frame
        finally:Player.SetToPosition=orig
        self.assertTrue(all(s==0 for s in speeds))
        self.assertLess(p.mPosition.y-20,30*0.05+0.01)  # grows linearly at most, never exponentially

class GroundPushOutTests(NMSMotionTests):
    def push_frame(self,a,p,ptr):
        # Fake engine: a re-placed player rests 0.5 m above where it was put, and is pushed there.
        a.motion_before(ptr,0.016)
        placed=getattr(p,'commands',0)>0
        x,y,z=p.mPosition.x,p.mPosition.y,p.mPosition.z
        if placed and y<self.rest+0.5:p.place((x,self.rest+0.5,z))
        a.motion_after(ptr,0.016)
    def test_constant_push_out_is_learned_not_followed_upward(self):
        a,p,ptr=self.make((0,0,0));self.rest=20.0
        heights=[]
        for _ in range(120):
            self.push_frame(a,p,ptr);heights.append(p.mPosition.y)
        self.assertLess(max(heights),21.0)
        self.assertAlmostEqual(heights[-1],heights[-30],places=3)
