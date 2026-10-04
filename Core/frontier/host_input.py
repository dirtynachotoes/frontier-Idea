"""Win32 foreground-only key edge. No game input layouts or injected key events."""
import ctypes
import os
class HostKey:
    def __init__(self):
        self.down=False
        self.user=ctypes.WinDLL('user32',use_last_error=True)
        self.user.GetForegroundWindow.argtypes=[];self.user.GetForegroundWindow.restype=ctypes.c_void_p
        self.user.GetWindowThreadProcessId.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)]
        self.user.GetWindowThreadProcessId.restype=ctypes.c_uint32
        self.user.GetAsyncKeyState.argtypes=[ctypes.c_int];self.user.GetAsyncKeyState.restype=ctypes.c_int16
    def pressed(self):
        process=ctypes.c_uint32()
        self.user.GetWindowThreadProcessId(self.user.GetForegroundWindow(),ctypes.byref(process))
        down=bool(self.user.GetAsyncKeyState(0x77)&0x8000) # F8
        edge=process.value==os.getpid() and down and not self.down;self.down=down
        return edge
