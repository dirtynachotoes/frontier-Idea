"""V2 spatial wire contract shared by NMS and game-free endpoints."""
import math
import struct
from .ipc import ticks
from .regions import Region
NAME='Local\\DestinyFrontier_Spatial_v2'
HEADER=struct.Struct('<IIIIQ40x')
SLOT=struct.Struct('<QQIIQ15f36x')
MAGIC=0x53544644
VERSION=2
SIZE=320
OFFSETS={'nms':64,'sunrise':192}
class SpatialMapping(Region):
    def __init__(self,test_file=None): super().__init__(NAME,SIZE,test_file)
    def publish(self,role,incarnation,sequence,context=0,player=None,camera=None,forward=None,up=None,right=None):
        floats=[0.0]*15
        flags=0
        for i,vector in enumerate((player,camera,forward,up,right)):
            if vector is not None and len(vector)==3 and all(math.isfinite(float(x)) for x in vector):
                flags |= 1<<i
                floats[i*3:i*3+3]=vector
        with self.locked() as acquired:
            if not acquired:return False
            raw=bytes(self.memory[:64])
            if raw==bytes(64): HEADER.pack_into(self.memory,0,MAGIC,VERSION,SIZE,64,ticks() or 1)
            elif HEADER.unpack(raw)[:4]!=(MAGIC,VERSION,SIZE,64): raise RuntimeError('Spatial V2 ABI mismatch')
            SLOT.pack_into(self.memory,OFFSETS[role],ticks(),incarnation,sequence,flags,context,*floats)
            return True
    def snapshot(self):
        with self.locked() as acquired:
            if not acquired:return None
            if HEADER.unpack_from(self.memory)[:4]!=(MAGIC,VERSION,SIZE,64): return None
            return {role:SLOT.unpack_from(self.memory,offset) for role,offset in OFFSETS.items()}
