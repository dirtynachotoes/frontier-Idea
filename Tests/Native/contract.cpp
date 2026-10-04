// Standalone Frontier contract/policy, never loads or builds Sunrise.
#include "../../Native/frontier_policy.h"
#include "../../Native/frontier_readiness.h"
#include "../../Native/frontier_motion.h"
#include <array>
#include <limits>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
using namespace destiny_frontier;
void check(bool value){if(!value)throw std::runtime_error("Frontier contract assertion failed");}
int main(int argc,char** argv){
 // Fake position publisher models the pinned Sunrise failed-read retention contract.
 struct Snapshot { std::array<float,3> position{};bool present=false; } cached;
 auto publish=[&](bool bodyReadable,const std::array<float,3>& position){
  if(bodyReadable){cached.position=position;cached.present=true;}return bodyReadable;
 };
 check(!guardian_ready(true,true,true,cached));
 check(publish(true,{1.0f,2.0f,3.0f}));
 check(guardian_ready(true,true,true,cached));
 check(!publish(false,{0.0f,0.0f,0.0f})); // same-frame rigid body unavailable
 check(guardian_ready(true,true,true,cached)&&cached.position[1]==2.0f);
 check(!guardian_ready(false,true,true,cached));
 check(!guardian_ready(true,false,true,cached));
 check(!guardian_ready(true,true,false,cached));
 cached.present=false;check(!guardian_ready(true,true,true,cached));cached.present=true;
 for(int axis=0;axis<3;++axis){const float saved=cached.position[axis];
  cached.position[axis]=std::numeric_limits<float>::infinity();check(!guardian_ready(true,true,true,cached));
  cached.position[axis]=std::numeric_limits<float>::quiet_NaN();check(!guardian_ready(true,true,true,cached));
  cached.position[axis]=saved;
 }
 // Exhaustive readiness bit diagnostics, including guarded ownership and nonfinite position.
 for(unsigned inputs=0;inputs<32;++inputs){
  const bool world=(inputs&1U)!=0,component=(inputs&2U)!=0,owns=(inputs&4U)!=0;
  cached.present=(inputs&8U)!=0;cached.position={1.0f,2.0f,(inputs&16U)?3.0f:std::numeric_limits<float>::quiet_NaN()};
  const auto bits=guardian_readiness_bits(world,component,owns,cached);
  const auto expected=ready_diagnostics|(inputs&1U)|(inputs&2U)|((world&&component&&owns)?4U:0U)|
   (inputs&8U)|(inputs&16U)|((inputs==31U)?32U:0U)|((world&&component)?128U:0U);
  check(bits==expected);check(guardian_ready(world,component,owns,cached)==(inputs==31U));
 }
 cached.present=true;cached.position={1.0f,2.0f,3.0f};
 const auto goodBits=guardian_readiness_bits(true,true,true,cached)|ready_host;
 ReadinessTransitions transitions;
 check(transitions.observe(goodBits));check(!transitions.observe(goodBits));
 check(transitions.observe(goodBits&~ready_ownership));check(!transitions.observe(goodBits&~ready_ownership));
 check(transitions.observe(goodBits));
 // Diagnostics and their transition observer do not participate in hover policy.
 HoverPolicy observed,unobserved;observed.world(true,3,10);unobserved.world(true,3,10);
 ControlBlock diagnosticCommand{};diagnosticCommand.magic=control_magic;diagnosticCommand.version=1;
 diagnosticCommand.bytes=128;diagnosticCommand.headerBytes=64;diagnosticCommand.epoch=1;
 diagnosticCommand.heartbeat=10000;diagnosticCommand.request=1;diagnosticCommand.expectedIncarnation=50;
 diagnosticCommand.expectedContext=observed.context;diagnosticCommand.opcode=hover_on;diagnosticCommand.flags=1;
 for(const auto now:{10000ULL,10100ULL,12000ULL}){
  diagnosticCommand.readinessBits=goodBits;transitions.observe(goodBits);
  observed.tick(diagnosticCommand,now,50,true,true);
  diagnosticCommand.readinessBits=0;unobserved.tick(diagnosticCommand,now,50,true,true);
  check(observed.hovering==unobserved.hovering&&observed.ack==unobserved.ack&&observed.status==unobserved.status&&observed.context==unobserved.context);
 }
 check(sizeof(MotionBlock)==256);
 MotionHeader mh{};mh.magic=motion_magic;mh.version=1;mh.bytes=256;mh.headerBytes=64;mh.epoch=7;mh.heartbeat=10000;mh.enabled=1;
 MotionIntent mi{};mi.heartbeat=10000;mi.incarnation=99;mi.sequence=1;mi.keys=move_forward|move_sprint;mi.flags=3;
 check(motion_valid(mh,mi,10000,99));check(!motion_valid(mh,mi,10000,98));check(!motion_valid(mh,mi,12000,99));
 mi.flags=0;check(!motion_valid(mh,mi,10000,99));mi.flags=3;mi.keys=64;check(!motion_valid(mh,mi,10000,99));mi.keys=1;
 MotionKeys keys;keys.until=12000;keys.members[87]=true;keys.members[83]=true;keys.pressed[87]=true;
 bool held=false;check(keys.answer(87,10000,held)&&held);check(keys.answer(83,10000,held)&&!held);
 check(!keys.answer(87,12000,held));check(!keys.answer(256,10000,held));
 MotionAccumulator accumulated;SpatialSlot hostBasis{};hostBasis.forward[2]=1;hostBasis.right[0]=1;hostBasis.up[1]=1;
 std::array<float,3> pos{10,20,30},guardianForward{1,0,0};
 check(accumulated.sample(7,99,3,pos,guardianForward,hostBasis));check(accumulated.total[2]==0);
 pos[0]+=2;pos[1]-=1;pos[2]+=3;check(accumulated.sample(7,99,3,pos,guardianForward,hostBasis));
 check(accumulated.total[0]==1&&accumulated.total[1]==3&&accumulated.total[2]==2); // Different actual host/guest frames
 check(accumulated.sample(7,99,3,pos,guardianForward,hostBasis));check(accumulated.total[2]==2); // Idle does not create motion
 const auto generation=accumulated.generation;accumulated.reset();check(accumulated.sample(7,99,3,pos,guardianForward,hostBasis));
 check(accumulated.generation!=generation&&accumulated.total[2]==0); // Explicit re-arm cannot replay earlier travel
 check(accumulated.sample(8,99,3,pos,guardianForward,hostBasis));check(accumulated.total[2]==0);
 guardianForward={0,0,0};check(!accumulated.sample(8,99,3,pos,guardianForward,hostBasis));
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
   for(const wchar_t* character=name;*character;++character) { names.put(static_cast<char>(*character)); }
   names.put('\n');
  }
  check(bool(names));
  ControlBlock wire{};wire.magic=control_magic;wire.version=1;wire.bytes=128;wire.headerBytes=64;
  wire.epoch=1;wire.heartbeat=2;wire.request=3;wire.expectedIncarnation=4;wire.expectedContext=5;wire.opcode=1;wire.flags=3;
  wire.nativeHeartbeat=6;wire.nativeIncarnation=7;wire.nativeContext=8;wire.ack=9;wire.nativeReady=1;wire.status=1;wire.hover=1;wire.hostIncarnation=10;wire.hostSequence=11;
  std::ofstream ctrl(std::string(argv[1])+".control",std::ios::binary);ctrl.write(reinterpret_cast<const char*>(&wire),128);check(bool(ctrl));
  wire.readinessBits=goodBits;
  std::ofstream diagnostic(std::string(argv[1])+".diagnostics",std::ios::binary);
  diagnostic.write(reinterpret_cast<const char*>(&wire),128);check(bool(diagnostic));
  MotionBlock motionWire{};motionWire.header=mh;motionWire.host=mi;motionWire.routed=mi;
  motionWire.guest.heartbeat=10000;motionWire.guest.incarnation=50;motionWire.guest.context=3;motionWire.guest.sequence=4;
  motionWire.guest.displacement[0]=1;motionWire.guest.displacement[1]=2;motionWire.guest.displacement[2]=3;
  motionWire.guest.flags=1;motionWire.guest.scanReads=12;motionWire.guest.generation=5;
  std::ofstream motionFile(std::string(argv[1])+".motion",std::ios::binary);
  motionFile.write(reinterpret_cast<const char*>(&motionWire),256);check(bool(motionFile));
  std::ofstream out(argv[1],std::ios::binary);out.write(reinterpret_cast<const char*>(&slot),128);check(bool(out));}
 std::puts("PASS: cached Guardian readiness, predicate diagnostics, transition observer isolation, native policy, expiry, context, replay refusal, region predicate and spatial ABI (no games)");
}
