// Source-level integration only. No new engine signatures, offsets or foreign threads.
#include "frontier_native.h"
#include "frontier_policy.h"
#include "frontier_readiness.h"
#include "frontier_motion.h"
#include <Windows.h>
#include <atomic>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <utility>
#include "../hooks/teleport/runtime.h"
#include "../hooks/bootflow/bootflow_hook_lifecycle.h"
#include "../player/player_position.h"
#include "../hooks/polled_input/runtime.h"
#include "../../state/account/account_state.h"
#include "../../state/runtime/runtime.h"
#include "../movement/movement_settings_store.h"
#include "../../core/logging/log.h"
namespace sunrise::client::frontier {
namespace {
using namespace destiny_frontier;
struct Region {
 HANDLE mapping=nullptr,mutex=nullptr; unsigned char* view=nullptr;
 ~Region(){close();}
 void close() noexcept {if(view)UnmapViewOfFile(view);if(mapping)CloseHandle(mapping);if(mutex)CloseHandle(mutex);view=nullptr;mapping=nullptr;mutex=nullptr;}
 bool open(const wchar_t* name,const wchar_t* lock,std::size_t bytes,bool create) noexcept {
  if(view)return true;
  mutex=create?CreateMutexW(nullptr,FALSE,lock):OpenMutexW(SYNCHRONIZE|MUTEX_MODIFY_STATE,FALSE,lock);
  mapping=create?CreateFileMappingW(INVALID_HANDLE_VALUE,nullptr,PAGE_READWRITE,0,static_cast<DWORD>(bytes),name):OpenFileMappingW(FILE_MAP_ALL_ACCESS,FALSE,name);
  if(mapping&&mutex)view=static_cast<unsigned char*>(MapViewOfFile(mapping,FILE_MAP_ALL_ACCESS,0,0,bytes));
  if(!view){close();return false;}return true;
 }
 bool acquire() noexcept {const DWORD result=WaitForSingleObject(mutex,0);if(result==WAIT_ABANDONED){ReleaseMutex(mutex);close();return false;}return result==WAIT_OBJECT_0;}
 void release() noexcept {ReleaseMutex(mutex);}
};
Region bridge,spatial,control,motion;
SRWLOCK motionKeysGate=SRWLOCK_INIT;
destiny_frontier::MotionKeys motionKeys;
destiny_frontier::MotionAccumulator motionAccumulator;
std::atomic_uint64_t motionScanReads{0};
std::uint64_t motionSequence=0;
MotionHeader motionHeader{};MotionIntent motionIntent{};
SRWLOCK gate=SRWLOCK_INIT;
std::atomic_bool enabled{false},cachedConnected{false},cachedLive{false};
std::atomic_uint32_t sequence{0},cachedTarget{0};
std::atomic_uint64_t cachedUntil{0};
HoverPolicy policy;
ControlBlock command{};
BridgeBlock legacy{};
SpatialSlot host{};
std::uint64_t incarnation=0,lastPoll=0;
std::uint32_t spatialSequence=0;
bool lastHover=false;
std::uint64_t lastAck=0;
std::uint32_t lastStatus=idle;
ReadinessTransitions readinessTransitions;
bool finite(const hooks::teleport::Vector& v) noexcept {return std::isfinite(v[0])&&std::isfinite(v[1])&&std::isfinite(v[2]);}
bool peer_live(std::uint64_t now) noexcept {
 return legacy.header.magic==bridge_magic&&legacy.header.version==1&&legacy.header.epoch&&fresh(now,legacy.header.heartbeat)&&
 legacy.nms.incarnation&&legacy.nms.ready==1&&fresh(now,legacy.nms.heartbeat)&&legacy.to_sunrise.live==1;
}
void poll_bridge(std::uint64_t now,bool ready) noexcept {
 if(!bridge.open(bridgeName,bridgeMutex,192,false)||!bridge.acquire())return;
 std::memcpy(&legacy,bridge.view,192);
 const bool valid=legacy.header.magic==bridge_magic&&legacy.header.version==1&&legacy.header.epoch&&fresh(now,legacy.header.heartbeat);
 if(valid){State s{now,incarnation,sequence.load(),static_cast<std::uint32_t>(ready),legacy.to_sunrise.target<=999?legacy.to_sunrise.target:0,0};std::memcpy(bridge.view+64,&s,32);}
 bridge.release();
 cachedConnected.store(valid);cachedLive.store(valid&&ready&&peer_live(now));
 cachedTarget.store(valid&&legacy.to_sunrise.target<=999?legacy.to_sunrise.target:0);
 cachedUntil.store(valid?(std::min)(legacy.header.heartbeat,legacy.nms.heartbeat)+timeout_ms:0);
}
void poll_spatial(std::uint64_t now,bool ready,const hooks::teleport::Vector& position) noexcept {
 if(!spatial.open(spatialName,spatialMutex,320,true)||!spatial.acquire())return;
 SpatialHeader h{};std::memcpy(&h,spatial.view,64);
 const SpatialHeader zero{};
 if(std::memcmp(&h,&zero,64)==0){h.magic=spatial_magic;h.version=spatial_version;h.bytes=320;h.headerBytes=64;h.epoch=now?now:1;std::memcpy(spatial.view,&h,64);}
 if(h.magic!=spatial_magic||h.version!=spatial_version||h.bytes!=320||h.headerBytes!=64){host={};spatial.release();return;}
 std::memcpy(&host,spatial.view+64,128);
 SpatialSlot slot{};slot.heartbeat=now;slot.incarnation=incarnation;slot.sequence=++spatialSequence;slot.context=policy.context;
 if(ready){slot.flags|=1;for(int i=0;i<3;++i)slot.playerPosition[i]=position[i];}
 hooks::teleport::CameraPose pose{};
 if(ready&&hooks::teleport::camera_pose(pose)&&finite(pose.position)&&finite(pose.forward)&&finite(pose.up)){
  slot.flags|=2|4|8;
  for(int i=0;i<3;++i){slot.cameraPosition[i]=pose.position[i];slot.forward[i]=pose.forward[i];slot.up[i]=pose.up[i];}
  // No guessed handedness/right vector: publish only verified camera fields.
 }
 std::memcpy(spatial.view+192,&slot,128);spatial.release();
}
void read_control() noexcept {
 if(!control.open(controlName,controlMutex,128,true)||!control.acquire())return;
 std::memcpy(&command,control.view,64);control.release();
}
void publish_status(std::uint64_t now,bool ready,bool hostReady,std::uint32_t readinessBits) noexcept {
 if(!control.view||!control.acquire())return;
 ControlBlock result{};result.nativeHeartbeat=now;result.nativeIncarnation=incarnation;result.nativeContext=policy.context;
 result.ack=policy.ack;result.nativeReady=static_cast<std::uint32_t>(ready&&hostReady);result.status=policy.status;result.hover=static_cast<std::uint32_t>(policy.hovering);
 result.readinessBits=readinessBits;
 result.hostIncarnation=hostReady?host.incarnation:0;result.hostSequence=hostReady?host.sequence:0;
 std::memcpy(control.view+64,reinterpret_cast<unsigned char*>(&result)+64,64);control.release();
}
void poll_motion(std::uint64_t now,bool ready,bool hostReady,const hooks::teleport::Vector& position) noexcept {
 MotionKeys nextKeys{};MotionHeader header{};MotionIntent intent{};bool valid=false;
 if(motion.open(motionName,motionMutex,256,false)){
  if(motion.acquire()){std::memcpy(&motionHeader,motion.view,64);std::memcpy(&motionIntent,motion.view+128,64);motion.release();}
  // A busy mutex is not peer loss. Retain the last atomic packet only under its ORIGINAL lease.
  header=motionHeader;intent=motionIntent;
  valid=motion.view&&ready&&hostReady&&peer_live(now)&&header.epoch==legacy.header.epoch&&command.epoch==header.epoch&&fresh(now,command.heartbeat)&&!policy.hovering&&!movement::get().flyEnabled&&
   hooks::polled_input::is_installed()&&motion_valid(header,intent,now,host.incarnation)&&
   (host.flags&29U)==29U;
 }
 hooks::teleport::CameraPose pose{};
 valid=valid&&hooks::teleport::camera_pose(pose)&&finite(pose.forward)&&
  (pose.forward[0]*pose.forward[0]+pose.forward[1]*pose.forward[1]>0.0F);
 if(valid){
  using Action=state::account::settings::bindings::Action;
  const auto account=state::account_snapshot();
  const std::array<Action,6> actions{Action::moveForward,Action::moveBackward,Action::moveLeft,Action::moveRight,Action::holdSprint,Action::jump};
  for(unsigned i=0;i<actions.size();++i){
   const auto& binding=account.settings.keyBindings.values[static_cast<std::size_t>(actions[i])];
   const auto authored=binding.primary.has_value()?binding.primary:binding.secondary;
   if(!authored.has_value()){if(intent.keys&(1U<<i))valid=false;continue;}
   const auto code=*authored;const unsigned key=hooks::teleport::action_key(code);
   if(!key||key>=256){if(intent.keys&(1U<<i))valid=false;continue;}
   nextKeys.members[key]=true;nextKeys.pressed[key]=nextKeys.pressed[key]||((intent.keys&(1U<<i))!=0);
   if(intent.keys&(1U<<i)){
    for(const auto modifier:{std::pair<unsigned,unsigned>{0x0100U,VK_MENU},{0x0200U,VK_CONTROL},{0x0400U,VK_SHIFT}}){
     if(code&modifier.first){nextKeys.members[modifier.second]=true;nextKeys.pressed[modifier.second]=true;}
    }
   }
  }
  nextKeys.until=(std::min)((std::min)(header.heartbeat,intent.heartbeat),
   (std::min)(host.heartbeat,(std::min)(legacy.header.heartbeat,legacy.nms.heartbeat)))+timeout_ms;
 }
 if(!valid){nextKeys={};motionAccumulator.reset();}
 AcquireSRWLockExclusive(&motionKeysGate);motionKeys=nextKeys;ReleaseSRWLockExclusive(&motionKeysGate);
 bool resultValid=valid&&motionAccumulator.sample(header.epoch,intent.incarnation,policy.context,position,pose.forward,host);
 if(!resultValid){motionAccumulator.reset();AcquireSRWLockExclusive(&motionKeysGate);motionKeys={};ReleaseSRWLockExclusive(&motionKeysGate);}
 if(motion.view&&motion.acquire()){
  MotionHeader current{};std::memcpy(&current,motion.view,64);
  MotionResult result{};result.heartbeat=now;result.incarnation=incarnation;result.context=policy.context;
  result.sequence=++motionSequence;result.flags=static_cast<std::uint32_t>(resultValid&&current.epoch==header.epoch&&fresh(now,current.heartbeat));
  result.scanReads=motionScanReads.load();result.generation=motionAccumulator.generation;
  if(result.flags)for(unsigned lane=0;lane<3;++lane)result.displacement[lane]=motionAccumulator.total[lane];
  std::memcpy(motion.view+192,&result,64);motion.release();
 }
}

}
void start(bool hooksReady) noexcept {
 AcquireSRWLockExclusive(&gate);
 if(hooksReady&&!enabled.load()){incarnation=(static_cast<std::uint64_t>(GetCurrentProcessId())<<32)^GetTickCount64();if(!incarnation)incarnation=1;policy={};command={};legacy={};host={};lastPoll=0;sequence.store(0);spatialSequence=0;lastHover=false;lastAck=0;lastStatus=idle;readinessTransitions={};enabled.store(true);}
 ReleaseSRWLockExclusive(&gate);
 core::log::write(core::log::Channel::client,core::log::Level::info,hooksReady?"ev=frontier_native stage=start abi=spatial_v2":"ev=frontier_native stage=blocked reason=movement_hooks");
}
void observe_region(bool has_current,int current,int held,int previous) noexcept {
 if(!enabled.load()||!destiny_frontier::region_transition(has_current,current,held,previous))return;
 auto value=sequence.load();while(value<1000000&&!sequence.compare_exchange_weak(value,value+1)){}
}
void tick() noexcept {
 if(!enabled.load()||!TryAcquireSRWLockExclusive(&gate))return;
 if(!enabled.load()){ReleaseSRWLockExclusive(&gate);return;}
 using namespace destiny_frontier;
 const auto now=GetTickCount64();
 const auto playerSnapshot=player::position::snapshot();
 const auto position=playerSnapshot.position;
 void* component=player::position::component();
 const bool inWorld=hooks::bootflow::in_world();
 const bool ownsLocal=inWorld&&component&&hooks::teleport::owns_local_player(component);
 auto readinessBits=guardian_readiness_bits(inWorld,component!=nullptr,ownsLocal,playerSnapshot);
 const bool ready=(readinessBits&ready_combined)!=0;
 const auto slice=hooks::bootflow::current_slice_set();
 policy.world(ready,slice.available&&slice.present?slice.index:-1,reinterpret_cast<std::uintptr_t>(component));
 const bool polling=now-lastPoll>=100;
 if(polling){lastPoll=now;poll_bridge(now,ready);poll_spatial(now,ready,position);read_control();}
 const bool hostReady=host.incarnation&&fresh(now,host.heartbeat)&&(host.flags&1U)&&!(host.flags&~31U)&&
 std::isfinite(host.playerPosition[0])&&std::isfinite(host.playerPosition[1])&&std::isfinite(host.playerPosition[2]);
 readinessBits|=hostReady?ready_host:0U;
 if(readinessTransitions.observe(readinessBits)){
  core::log::writef(core::log::Channel::client,core::log::Level::info,
   "ev=frontier_readiness bits=%u in_world=%u component_present=%u owns_local_player=%u ownership_checked=%u snapshot_present=%u position_finite=%u combined_ready=%u host_ready=%u ready=%u context=%llu tick_ms=%llu",
   readinessBits,static_cast<unsigned>((readinessBits&ready_in_world)!=0),static_cast<unsigned>((readinessBits&ready_component)!=0),
   static_cast<unsigned>((readinessBits&ready_ownership)!=0),static_cast<unsigned>((readinessBits&ready_ownership_checked)!=0),
   static_cast<unsigned>((readinessBits&ready_snapshot)!=0),static_cast<unsigned>((readinessBits&ready_finite)!=0),
   static_cast<unsigned>(ready),static_cast<unsigned>(hostReady),static_cast<unsigned>(ready&&hostReady),
   static_cast<unsigned long long>(policy.context),static_cast<unsigned long long>(now));
 }
 policy.tick(command,now,incarnation,ready&&hostReady,peer_live(now)&&command.epoch==legacy.header.epoch);
 // Expiry is also checked by the physics-side runtime settings accessor if camera ticks stop.
 const auto expiry=(std::min)((std::min)(command.heartbeat,legacy.header.heartbeat), (std::min)(legacy.nms.heartbeat,host.heartbeat))+timeout_ms;
 movement::set_frontier_hover(policy.hovering,expiry);
 if(lastHover!=policy.hovering||lastAck!=policy.ack||lastStatus!=policy.status){
  core::log::writef(core::log::Channel::client,core::log::Level::info,"ev=frontier_native hover=%u ack=%llu status=%u context=%llu host_seq=%u",static_cast<unsigned>(policy.hovering),static_cast<unsigned long long>(policy.ack),policy.status,static_cast<unsigned long long>(policy.context),host.sequence);
  lastHover=policy.hovering;lastAck=policy.ack;lastStatus=policy.status;
 }
 poll_motion(now,ready,hostReady,position);
 if(polling)publish_status(now,ready,hostReady,readinessBits);
 ReleaseSRWLockExclusive(&gate);
}
void legacy_status(std::uint32_t& target,bool& connected,bool& live) noexcept {
 target=cachedTarget.load();connected=enabled.load()&&cachedConnected.load()&&GetTickCount64()<cachedUntil.load();live=connected&&cachedLive.load();
}
bool motion_key(unsigned virtualKey,bool& held) noexcept {
 if(!TryAcquireSRWLockShared(&motionKeysGate))return false;
 const bool overrideKey=motionKeys.answer(virtualKey,GetTickCount64(),held);
 ReleaseSRWLockShared(&motionKeysGate);
 if(overrideKey)motionScanReads.fetch_add(1,std::memory_order_relaxed);
 return overrideKey;
}
void shutdown() noexcept {
 enabled.store(false);AcquireSRWLockExclusive(&gate);
 AcquireSRWLockExclusive(&motionKeysGate);motionKeys={};ReleaseSRWLockExclusive(&motionKeysGate);motionAccumulator.reset();
 movement::set_frontier_hover(false,0);cachedConnected.store(false);cachedLive.store(false);cachedUntil.store(0);
 if(control.view&&control.acquire()){std::memset(control.view+64,0,64);control.release();}
 bridge.close();spatial.close();control.close();motion.close();motionHeader={};motionIntent={};ReleaseSRWLockExclusive(&gate);
}
}
