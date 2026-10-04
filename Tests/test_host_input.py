import ctypes
import os
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Core'))
from frontier.host_input import HostKey
class User32Fake:
    def __init__(self):self.pid=os.getpid();self.down=False
    def GetForegroundWindow(self):return 1
    def GetWindowThreadProcessId(self,window,pointer):ctypes.cast(pointer,ctypes.POINTER(ctypes.c_uint32))[0]=self.pid
    def GetAsyncKeyState(self,key):assert key==0x77;return 0x8000 if self.down else 0
class HostInputTests(unittest.TestCase):
    def test_only_foreground_edges_and_no_repeat(self):
        key=HostKey.__new__(HostKey);key.down=False;key.user=User32Fake()
        self.assertFalse(key.pressed());key.user.down=True
        self.assertTrue(key.pressed());self.assertFalse(key.pressed())
        key.user.pid=0;self.assertFalse(key.pressed())
        key.user.pid=os.getpid();self.assertFalse(key.pressed()) # held in another app never becomes a new edge
        key.user.down=False;self.assertFalse(key.pressed())
        key.user.down=True;self.assertTrue(key.pressed())
