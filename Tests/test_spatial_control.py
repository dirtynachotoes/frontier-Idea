import ctypes
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Core'))
from frontier.spatial import SpatialMapping,SLOT,HEADER,MAGIC,VERSION,SIZE
from frontier.control import ControlMapping,CORE,NATIVE
class ContractTests(unittest.TestCase):
    def test_v2_roundtrip_and_owned_slots(self):
        with tempfile.TemporaryDirectory() as td:
            with SpatialMapping(Path(td)/'spatial') as m:
                self.assertEqual(SLOT.size,128)
                m.publish('nms',10,20,30,player=(1,2,3),forward=(0,0,-1))
                before=bytes(m.memory[64:192])
                m.publish('sunrise',11,21,31,player=(4,5,6),camera=(7,8,9))
                self.assertEqual(bytes(m.memory[64:192]),before)
                n=m.snapshot()['nms'];self.assertEqual(n[1:5],(10,20,5,30));self.assertEqual(n[5:8],(1,2,3))
                self.assertEqual(struct.unpack_from('<Q',m.memory,64+24)[0],30)
            Path(td,'spatial').unlink()
    def test_reject_old_header_and_wrong_file_size(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'spatial'
            with SpatialMapping(p) as m:
                HEADER.pack_into(m.memory,0,MAGIC,1,SIZE,64,1)
                with self.assertRaisesRegex(RuntimeError,'ABI'):m.publish('nms',1,1)
            p.write_bytes(b'wrong')
            with self.assertRaises(ValueError):SpatialMapping(p)
            p.unlink()
    def test_nonfinite_fields_not_published(self):
        with tempfile.TemporaryDirectory() as td:
            with SpatialMapping(Path(td)/'spatial') as m:
                m.publish('nms',1,1,player=(float('nan'),0,0),up=(0,1,0))
                slot=m.snapshot()['nms'];self.assertEqual(slot[3],8);self.assertEqual(slot[5:8],(0,0,0))
    def test_control_ownership_and_command_context(self):
        with tempfile.TemporaryDirectory() as td,patch('frontier.control.ticks',return_value=10000):
            with ControlMapping(Path(td)/'control') as m:
                NATIVE.pack_into(m.memory,64,10000,40,50,0,1,0,0,0,60,70)
                native=bytes(m.memory[64:]);m.start(1);m.refresh(1,True,True)
                self.assertEqual(bytes(m.memory[64:]),native)
                self.assertEqual(m.request_hover(True),1)
                c=CORE.unpack_from(m.memory);self.assertEqual(c[7:11],(40,50,1,3))
                self.assertEqual(m.status()['host_sequence'],70)
                m.stop(2);self.assertTrue(m.status()['core_valid']);m.stop(1)
                self.assertFalse(m.status()['core_valid']);self.assertEqual(bytes(m.memory[64:]),native)
                m.close();m.close()
    def test_no_ready_no_on_but_off_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            with ControlMapping(Path(td)/'control') as m:
                m.start(1)
                with self.assertRaises(RuntimeError):m.request_hover(True)
                self.assertEqual(m.request_hover(False),1)
    def test_stale_and_future_native_commands_refused(self):
        with tempfile.TemporaryDirectory() as td,patch('frontier.control.ticks',return_value=10000):
            with ControlMapping(Path(td)/'control') as m:
                m.start(1);m.refresh(1,True)
                for hb in (8000,10001):
                    NATIVE.pack_into(m.memory,64,hb,40,50,0,1,0,0,0,60,70)
                    with self.assertRaises(RuntimeError):m.request_hover(True)
    def test_preflight(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
        from verify_ci_package import validate
        validate()
