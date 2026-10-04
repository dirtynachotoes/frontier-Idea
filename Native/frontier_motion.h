#pragma once
#include "frontier_protocol.h"
#include <array>
#include <cmath>
namespace destiny_frontier {
constexpr wchar_t motionName[]=LR"(Local\DestinyFrontier_Motion_v1)";
constexpr wchar_t motionMutex[]=LR"(Local\DestinyFrontier_Motion_v1_mutex)";
constexpr std::uint32_t motion_magic=0x4D465444;
struct MotionHeader {std::uint32_t magic,version,bytes,headerBytes;std::uint64_t epoch,heartbeat,enabled;unsigned char reserved[24];};
struct MotionIntent {std::uint64_t heartbeat,incarnation,sequence;std::uint32_t keys,flags;unsigned char reserved[32];};
struct MotionResult {std::uint64_t heartbeat,incarnation,context,sequence;float displacement[3];std::uint32_t flags;std::uint64_t scanReads,generation;};
struct MotionBlock {MotionHeader header;MotionIntent host,routed;MotionResult guest;};
static_assert(sizeof(MotionHeader)==64&&sizeof(MotionIntent)==64&&sizeof(MotionResult)==64&&sizeof(MotionBlock)==256);
static_assert(offsetof(MotionBlock,host)==64&&offsetof(MotionBlock,routed)==128&&offsetof(MotionBlock,guest)==192);
static_assert(offsetof(MotionIntent,keys)==24&&offsetof(MotionResult,displacement)==32&&offsetof(MotionResult,scanReads)==48);
enum MotionKey : std::uint32_t {move_forward=1,move_back=2,move_left=4,move_right=8,move_sprint=16,move_jump=32};
inline bool motion_valid(const MotionHeader& h,const MotionIntent& i,std::uint64_t now,std::uint64_t hostIncarnation) noexcept {
 return h.magic==motion_magic&&h.version==1&&h.bytes==256&&h.headerBytes==64&&h.epoch&&h.enabled==1&&fresh(now,h.heartbeat)&&
  i.incarnation&&i.incarnation==hostIncarnation&&fresh(now,i.heartbeat)&&i.flags==3&&!(i.keys&~63U);
}
struct MotionKeys {
 std::array<bool,256> members{},pressed{};
 std::uint64_t until=0;
 bool answer(unsigned key,std::uint64_t now,bool& held) const noexcept {
  if(key>=members.size()||!until||now>=until||!members[key])return false;
  held=pressed[key];return true;
 }
};
// Translation only: actual Guardian displacement projected into its captured camera basis.
// No acceleration, gravity, jump impulse, collision or speed model here.
struct MotionAccumulator {
 std::uint64_t epoch=0,hostIncarnation=0,context=0,generation=0;
 std::array<float,3> previous{},total{};
 bool tracking=false;
 void reset() noexcept {tracking=false;total={};}
 template<class Position,class Vector>
 bool sample(std::uint64_t e,std::uint64_t host,std::uint64_t ctx,const Position& position,const Vector& forward,const SpatialSlot& hostPose) noexcept {
  for(unsigned lane=0;lane<3;++lane)if(!std::isfinite(position[lane])||!std::isfinite(forward[lane])||!std::isfinite(hostPose.forward[lane])||!std::isfinite(hostPose.right[lane])||!std::isfinite(hostPose.up[lane])){reset();return false;}
  if(!tracking||e!=epoch||host!=hostIncarnation||ctx!=context){++generation;epoch=e;hostIncarnation=host;context=ctx;previous=position;total={};tracking=true;return true;}
  const float length=std::sqrt(forward[0]*forward[0]+forward[1]*forward[1]);
  if(!std::isfinite(length)||length<=0.0F){reset();return false;}
  const float fx=forward[0]/length,fy=forward[1]/length;
  const float dx=position[0]-previous[0],dy=position[1]-previous[1],dz=position[2]-previous[2];
  const float f=dx*fx+dy*fy,r=dx*fy-dy*fx;
  std::array<float,3> next{};
  for(unsigned lane=0;lane<3;++lane){next[lane]=total[lane]+f*hostPose.forward[lane]+r*hostPose.right[lane]+dz*hostPose.up[lane];if(!std::isfinite(next[lane])){reset();return false;}}
  previous=position;total=next;return true;
 }
};
}
