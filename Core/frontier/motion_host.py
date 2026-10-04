"""Foreground input and returned displacement consumer, with injected dependencies for tests."""
import ctypes
import os
from .host_input import HostKey
from .motion import MotionMapping,ResultConsumer,fresh,MAGIC
from .ipc import ticks
class MovementKeys(HostKey):
    def __init__(self):super().__init__();self.toggle_down=False
    def focused(self):
        process=ctypes.c_uint32()
        self.user.GetWindowThreadProcessId(self.user.GetForegroundWindow(),ctypes.byref(process))
        return process.value==os.getpid()
    def sample(self):
        focused=self.focused()
        toggle=bool(self.user.GetAsyncKeyState(0x78)&0x8000) # F9 development arm switch
        edge=focused and toggle and not self.toggle_down;self.toggle_down=toggle
        bits=0
        if focused:
            for key,bit in ((0x57,1),(0x53,2),(0x41,4),(0x44,8),(0x10,16),(0x20,32)):
                if self.user.GetAsyncKeyState(key)&0x8000:bits|=bit
        return focused,edge,bits
class HostMotion:
    def __init__(self,key_reader=None,mapping=None):
        self.keys=key_reader or MovementKeys();self.mapping=mapping;self.consumer=ResultConsumer()
        self.armed=False;self.sequence=0;self.last_result=None;self.last_header=None;self.valid_until=0
    def exchange(self,incarnation,status):
        if self.mapping is None:self.mapping=MotionMapping()
        self.valid_until=0
        focused,edge,keys=self.keys.sample()
        if edge:self.armed=not self.armed
        self.sequence+=1
        data=self.mapping.host_exchange(incarnation,self.sequence,keys,3 if focused and self.armed else 0)
        if data is None:
            if self.last_header is None:return None
            data=(self.last_header,self.last_result) # Original leases; never refresh cached timestamps.
        header,result=data;self.last_header=header;now=ticks()
        core_motion=header[:4]==(MAGIC,1,256,64) and header[4] and header[6]==1 and fresh(now,header[5])
        if not core_motion:self.armed=False
        self.last_result=result
        delta=self.consumer.delta(header,result,status,focused and self.armed,now)
        if delta is not None:self.valid_until=min(header[5],result[0])+2000
        return delta
    def close(self):
        if self.mapping:self.mapping.close();self.mapping=None
        self.armed=False;self.consumer.identity=None
