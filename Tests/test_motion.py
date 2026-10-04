"""Game-free testing of production intent routing and authentic-result consumption.
Fake numeric samples validate plumbing/translation, not real Guardian input or NMS physics.
"""
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Core'))
from frontier.motion import MotionMapping,HEADER,INTENT,RESULT,MAGIC,ResultConsumer
class MotionTests(unittest.TestCase):
    def test_core_routing_is_bounded_and_owned(self):
        with tempfile.TemporaryDirectory() as td,patch('frontier.motion.ticks',return_value=10000):
            with MotionMapping(Path(td)/'motion') as m:
                m.start(7);m.host_exchange(99,1,17,3);host=bytes(m.memory[64:128])
                RESULT.pack_into(m.memory,192,10000,50,3,1,0,0,0,1,2,1);guest=bytes(m.memory[192:])
                self.assertTrue(m.route(7,True));self.assertEqual(INTENT.unpack_from(m.memory,128),(10000,99,1,17,3))
                self.assertEqual(bytes(m.memory[64:128]),host);self.assertEqual(bytes(m.memory[192:]),guest)
                m.route(7,False);self.assertEqual(INTENT.unpack_from(m.memory,128)[3:],(0,0))
                for hb,keys,flags in ((8000,1,3),(10001,1,3),(10000,64,3),(10000,1,1)):
                    INTENT.pack_into(m.memory,64,hb,99,2,keys,flags);m.route(7,True)
                    self.assertEqual(INTENT.unpack_from(m.memory,128)[3:],(0,0))
                m.stop(8);self.assertEqual(HEADER.unpack_from(m.memory)[4],7)
                m.stop(7);self.assertEqual(bytes(m.memory[:64]),bytes(64));self.assertEqual(bytes(m.memory[192:]),guest)
    def test_results_are_measured_deltas_not_a_speed_model(self):
        c=ResultConsumer();h=(MAGIC,1,256,64,7,10000,1)
        status=dict(ready=True,incarnation=50,context=3,hover=False)
        result=(10000,50,3,1,10.,20.,30.,1,4,1)
        self.assertEqual(c.delta(h,result,status,True,10000),(0.,0.,0.))
        # Intermediate publications may be skipped without losing measured movement.
        later=(10000,50,3,4,12.,19.,33.,1,10,1)
        self.assertEqual(c.delta(h,later,status,True,10000),(2.,-1.,3.))
        self.assertEqual(c.delta(h,later,status,True,10000),(0.,0.,0.))
        rearm=(10000,50,3,5,0.,0.,0.,1,12,2)
        self.assertEqual(c.delta(h,rearm,status,True,10000),(0.,0.,0.))
        self.assertIsNone(c.delta(h,rearm,status,False,10000))
        self.assertIsNone(c.delta(h,rearm,status,True,12000))
        self.assertIsNone(c.delta(h,rearm,dict(status,context=4),True,10000))
        self.assertIsNone(c.delta(h,rearm,dict(status,hover=True),True,10000))
        corrupt=list(rearm);corrupt[4]=float('nan');self.assertIsNone(c.delta(h,corrupt,status,True,10000))
    def test_foreground_release_and_disarm(self):
        from frontier.motion_host import HostMotion
        class Keys:
            value=(True,True,1)
            def sample(self):return self.value
        class Mapping:
            def host_exchange(self,*args):
                self.intent=args
                return ((MAGIC,1,256,64,7,10000,1),(10000,50,3,1,0.,0.,0.,1,1,1))
            def close(self):pass
        keys=Keys();mapping=Mapping();host=HostMotion(keys,mapping)
        with patch('frontier.motion_host.ticks',return_value=10000):
            status=dict(ready=True,incarnation=50,context=3,hover=False)
            self.assertEqual(host.exchange(99,status),(0.,0.,0.));self.assertEqual(mapping.intent[3],3)
            keys.value=(False,False,0);self.assertIsNone(host.exchange(99,status));self.assertEqual(mapping.intent[3],0)
            keys.value=(True,True,0);self.assertIsNone(host.exchange(99,status));self.assertFalse(host.armed)

    def test_busy_motion_mutex_reuses_only_original_valid_result_lease(self):
        from frontier.motion_host import HostMotion
        class Keys:
            def sample(self):return True,False,1
        class Mapping:
            def host_exchange(self,*args):return None
        host=HostMotion(Keys(),Mapping());host.armed=True
        host.last_header=(MAGIC,1,256,64,7,10000,1)
        host.last_result=(10000,50,3,1,0.,0.,0.,1,1,1)
        status=dict(ready=True,incarnation=50,context=3,hover=False)
        with patch('frontier.motion_host.ticks',return_value=10001):
            self.assertEqual(host.exchange(99,status),(0.,0.,0.))
            self.assertEqual(host.valid_until,12000)
            self.assertEqual(host.last_header[5],10000)
        with patch('frontier.motion_host.ticks',return_value=12000):
            self.assertIsNone(host.exchange(99,status));self.assertFalse(host.armed)
