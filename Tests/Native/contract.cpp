// Standalone Frontier contract/policy, never loads or builds Sunrise.
#include "../../Native/frontier_policy.h"
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
using namespace destiny_frontier;
void check(bool value){if(!value)throw std::runtime_error("Frontier contract assertion failed");}
int main(int argc,char** argv){
 check(sizeof(SpatialSlot)==128&&sizeof(ControlBlock)==128);
 HoverPolicy p;p.world(true,3,10);const auto context=p.context;
 ControlBlock c{};c.magic=control_magic;c.version=1;c.bytes=128;c.headerBytes=64;
 c.epoch=7;c.heartbeat=10000;c.request=1;c.expectedIncarnation=50;c.expectedContext=context;c.opcode=hover_on;c.flags=1;
 p.tick(c,10000,50,true,true);check(p.hovering&&p.ack==1&&p.status==applied);
 p.tick(c,10100,50,true,true);check(p.hovering); // cached read is still bounded by original timestamp
 p.tick(c,12000,50,true,true);check(!p.hovering&&p.status==lease_lost); // exact existing two-second budget
 c.heartbeat=12000;p.tick(c,12001,50,true,true);check(!p.hovering); // no implicit re-arm
 c.request=2;p.tick(c,12001,50,true,true);check(p.hovering);
 p.tick(c,12001,50,true,false);check(!p.hovering); // explicit peer loss is immediate
 c.request=3;p.tick(c,12001,50,true,true);check(p.hovering);
 p.world(true,3,11);check(!p.hovering&&p.context!=context); // local player replacement
 c.request=4;p.tick(c,12001,50,true,true);check(!p.hovering&&p.status==rejected);
 c.expectedContext=p.context;c.expectedIncarnation=49;c.request=5;
 p.tick(c,12001,50,true,true);check(!p.hovering&&p.status==rejected);
 c.expectedIncarnation=50;c.request=6;p.tick(c,12001,50,true,true);check(p.hovering);
 c.opcode=hover_off;c.request=7;p.tick(c,12001,50,true,true);check(!p.hovering&&p.ack==7);
 c.opcode=hover_on;c.request=8;p.tick(c,12001,50,true,true);check(p.hovering);
 p.world(false,-1,0);check(!p.hovering);p.world(true,4,11);check(p.context!=c.expectedContext);
 c.expectedContext=p.context;c.request=9;c.heartbeat=13000;p.tick(c,12001,50,true,true);check(!p.hovering); // future clock
 c.heartbeat=12000;c.version=2;p.tick(c,12001,50,true,true);check(!p.hovering);
 c.version=1;c.opcode=999;c.request=10;p.tick(c,12001,50,true,true);check(p.status==rejected);
 c.opcode=hover_on;c.request=11;p.tick(c,12001,50,true,false);check(!p.hovering&&p.ack==11);
 p.tick(c,12001,50,true,true);check(!p.hovering); // never arm a request first seen during peer loss
 c.request=12;p.tick(c,12001,50,true,true);check(p.hovering);
 check(region_transition(true,2,2,1));check(!region_transition(true,2,2,2));check(!region_transition(false,2,2,1));check(!region_transition(true,2,1,1));
 SpatialSlot slot{};slot.heartbeat=0x1122334455667788ULL;slot.incarnation=0x8877665544332211ULL;
 slot.sequence=0x12345678;slot.flags=31;slot.context=0x1020304050607080ULL;
 for(int i=0;i<3;++i){slot.playerPosition[i]=float(i+1);slot.cameraPosition[i]=float(i+4);slot.forward[i]=float(i+7);slot.up[i]=float(i+10);slot.right[i]=float(i+13);}
 if(argc==2){
  std::ofstream names(std::string(argv[1])+".names",std::ios::binary);
  for(const wchar_t* name:{bridgeName,bridgeMutex,spatialName,spatialMutex,controlName,controlMutex}){
   for(const wchar_t* c=name;*c;++c) { names.put(static_cast<char>(*c)); }
   names.put('\n');
  }
  check(bool(names));
  ControlBlock wire{};wire.magic=control_magic;wire.version=1;wire.bytes=128;wire.headerBytes=64;
  wire.epoch=1;wire.heartbeat=2;wire.request=3;wire.expectedIncarnation=4;wire.expectedContext=5;wire.opcode=1;wire.flags=3;
  wire.nativeHeartbeat=6;wire.nativeIncarnation=7;wire.nativeContext=8;wire.ack=9;wire.nativeReady=1;wire.status=1;wire.hover=1;wire.hostIncarnation=10;wire.hostSequence=11;
  std::ofstream ctrl(std::string(argv[1])+".control",std::ios::binary);ctrl.write(reinterpret_cast<const char*>(&wire),128);check(bool(ctrl));
  std::ofstream out(argv[1],std::ios::binary);out.write(reinterpret_cast<const char*>(&slot),128);check(bool(out));}
 std::puts("PASS: native policy, expiry, context, replay refusal, region predicate and spatial ABI (no games)");
}
