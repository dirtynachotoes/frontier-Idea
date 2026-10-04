"""Temporary native Guardian commands. File endpoints are explicit tests only."""
import argparse
import json
import struct
from .regions import Region
from .ipc import ticks
NAME='Local\\DestinyFrontier_Control_v1'
CORE=struct.Struct('<IIII5QII')
NATIVE=struct.Struct('<4Q4I2Q')
MAGIC=0x43465444
class ControlMapping(Region):
    def __init__(self,test_file=None): super().__init__(NAME,128,test_file)
    def start(self,epoch):
        with self.locked() as acquired:
            if not acquired: raise RuntimeError('Control IPC busy at startup')
            CORE.pack_into(self.memory,0,MAGIC,1,128,64,epoch,ticks(),0,0,0,0,0)
    def refresh(self,epoch,both_live,scout_link=False):
        with self.locked() as acquired:
            if not acquired:return False
            c=list(CORE.unpack_from(self.memory))
            if c[:4]!=[MAGIC,1,128,64] or c[4]!=epoch:raise RuntimeError('Control epoch changed')
            c[5]=ticks(); c[10]=int(both_live) | (2 if scout_link else 0)
            CORE.pack_into(self.memory,0,*c)
            return True
    def stop(self,epoch):
        with self.locked() as acquired:
            if acquired and CORE.unpack_from(self.memory)[4]==epoch:
                self.memory[:64]=bytes(64)
    def status(self):
        with self.locked() as acquired:
            if not acquired:return None
            c=CORE.unpack_from(self.memory); n=NATIVE.unpack_from(self.memory,64)
            return dict(core_valid=c[:4]==(MAGIC,1,128,64) and bool(c[4]) and 0<=ticks()-c[5]<2000,
                        peers_live=bool(c[10]&1),scout_link=bool(c[10]&2),request=c[6],native_heartbeat=n[0],incarnation=n[1],context=n[2],
                        ack=n[3],ready=bool(n[4]),status=n[5],hover=bool(n[6]),host_incarnation=n[8],host_sequence=n[9])
    def request_hover(self,enabled):
        with self.locked() as acquired:
            if not acquired:raise RuntimeError('Control IPC busy; command not submitted')
            c=list(CORE.unpack_from(self.memory)); n=NATIVE.unpack_from(self.memory,64); now=ticks()
            if c[:4]!=[MAGIC,1,128,64] or not c[4] or not 0<=now-c[5]<2000:
                raise RuntimeError('No live Core')
            if enabled and (not c[10]&1 or not n[1] or not n[4] or not 0<=now-n[0]<2000):
                raise RuntimeError('Both peers and native Guardian must be ready')
            c[6]+=1; c[7]=n[1]; c[8]=n[2]; c[9]=1 if enabled else 2
            CORE.pack_into(self.memory,0,*c)
            return c[6]
def main():
    p=argparse.ArgumentParser(description='Temporary Guardian hover lease; no native preferences/save writes')
    p.add_argument('command',choices=['status','on','off']);p.add_argument('--test-file')
    a=p.parse_args()
    with ControlMapping(a.test_file) as m:
        if a.command!='status': print(json.dumps({'request':m.request_hover(a.command=='on')}))
        print(json.dumps(m.status()))
if __name__=='__main__':main()
