"""Opt-in movement routing. Physics is computed by the real Guardian, not this module."""
import math
import struct
from .regions import Region
from .ipc import ticks
NAME='Local\\DestinyFrontier_Motion_v1'
MAGIC=0x4D465444
HEADER=struct.Struct('<IIIIQQQ24x')
INTENT=struct.Struct('<QQQII32x')
RESULT=struct.Struct('<QQQQ3fIQQ')
def fresh(now,hb):return bool(hb and 0<=now-hb<2000)
class MotionMapping(Region):
    def __init__(self,test_file=None):super().__init__(NAME,256,test_file)
    def start(self,epoch):
        with self.locked() as acquired:
            if not acquired:raise RuntimeError('Motion mapping busy at startup')
            HEADER.pack_into(self.memory,0,MAGIC,1,256,64,epoch,ticks(),1)
            self.memory[128:192]=bytes(64)
    def route(self,epoch,peers_live):
        with self.locked() as acquired:
            if not acquired:return False
            h=HEADER.unpack_from(self.memory);now=ticks()
            if h[:4]!=(MAGIC,1,256,64) or h[4]!=epoch:raise RuntimeError('Motion Core ownership changed')
            HEADER.pack_into(self.memory,0,MAGIC,1,256,64,epoch,now,1)
            hb,inc,seq,keys,flags=INTENT.unpack_from(self.memory,64)
            if not(peers_live and fresh(now,hb) and inc and flags==3 and not keys&~63):keys=0;flags=0
            INTENT.pack_into(self.memory,128,hb,inc,seq,keys,flags)
            return True
    def host_exchange(self,incarnation,sequence,keys,flags):
        with self.locked() as acquired:
            if not acquired:return None
            INTENT.pack_into(self.memory,64,ticks(),incarnation,sequence,keys,flags)
            return HEADER.unpack_from(self.memory),RESULT.unpack_from(self.memory,192)
    def stop(self,epoch):
        with self.locked() as acquired:
            if acquired and HEADER.unpack_from(self.memory)[4]==epoch:self.memory[:64]=bytes(64);self.memory[128:192]=bytes(64)
class ResultConsumer:
    def __init__(self):self.identity=None;self.sequence=0;self.previous=(0.0,0.0,0.0)
    def delta(self,header,result,status,enabled,now):
        valid=(enabled and header[:4]==(MAGIC,1,256,64) and header[4] and header[6]==1 and fresh(now,header[5]) and
               fresh(now,result[0]) and result[1] and result[7]==1 and status and status['ready'] and
               result[1]==status['incarnation'] and result[2]==status['context'] and not status['hover'] and
               all(math.isfinite(v) for v in result[4:7]))
        if not valid:self.identity=None;return None
        identity=(header[4],result[1],result[2],result[9]);position=result[4:7]
        if identity!=self.identity:self.identity=identity;self.sequence=result[3];self.previous=position;return (0.0,0.0,0.0)
        if result[3]<self.sequence:self.identity=None;return None
        if result[3]==self.sequence:return (0.0,0.0,0.0)
        delta=tuple(a-b for a,b in zip(position,self.previous));self.previous=position;self.sequence=result[3]
        return delta if all(math.isfinite(v) for v in delta) else None
