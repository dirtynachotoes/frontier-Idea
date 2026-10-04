#pragma once
#include <cstddef>
#include <cstdint>
namespace destiny_frontier {
constexpr std::uint64_t timeout_ms = 2000;
constexpr std::uint32_t bridge_magic = 0x52465444;
struct Header { std::uint32_t magic, version; std::uint64_t epoch, heartbeat, pad; };
struct State { std::uint64_t heartbeat, incarnation; std::uint32_t seq, ready, ack, detail; };
struct Command { std::uint32_t target, live; std::uint64_t pad[3]; };
struct BridgeBlock { Header header; State nms, sunrise; Command to_nms, to_sunrise; std::uint64_t reserved[4]; };
static_assert(sizeof(BridgeBlock)==192 && offsetof(BridgeBlock,sunrise)==64 && offsetof(BridgeBlock,to_sunrise)==128);
constexpr std::uint32_t spatial_magic=0x53544644, spatial_version=2;
struct SpatialHeader { std::uint32_t magic,version,bytes,headerBytes; std::uint64_t epoch; unsigned char reserved[40]; };
struct SpatialSlot {
 std::uint64_t heartbeat,incarnation; std::uint32_t sequence,flags; std::uint64_t context;
 float playerPosition[3],cameraPosition[3],forward[3],up[3],right[3]; unsigned char reserved[36];
};
struct SpatialBlock { SpatialHeader header; SpatialSlot nms,sunrise; };
static_assert(sizeof(SpatialHeader)==64 && sizeof(SpatialSlot)==128 && sizeof(SpatialBlock)==320);
static_assert(offsetof(SpatialSlot,heartbeat)==0 && offsetof(SpatialSlot,incarnation)==8);
static_assert(offsetof(SpatialSlot,sequence)==16 && offsetof(SpatialSlot,flags)==20 && offsetof(SpatialSlot,context)==24);
static_assert(offsetof(SpatialSlot,playerPosition)==32 && offsetof(SpatialSlot,cameraPosition)==44);
static_assert(offsetof(SpatialSlot,forward)==56 && offsetof(SpatialSlot,up)==68 && offsetof(SpatialSlot,right)==80 && offsetof(SpatialSlot,reserved)==92);
static_assert(offsetof(SpatialBlock,nms)==64 && offsetof(SpatialBlock,sunrise)==192);
constexpr std::uint32_t control_magic=0x43465444;
// First 64 bytes owned by Core; last 64 by native Sunrise.
struct ControlBlock {
 std::uint32_t magic,version,bytes,headerBytes;
 std::uint64_t epoch,heartbeat,request,expectedIncarnation,expectedContext;
 std::uint32_t opcode,flags;
 std::uint64_t nativeHeartbeat,nativeIncarnation,nativeContext,ack;
 std::uint32_t nativeReady,status,hover,reserved;
 std::uint64_t hostIncarnation,hostSequence;
};
static_assert(sizeof(ControlBlock)==128 && offsetof(ControlBlock,nativeHeartbeat)==64);
static_assert(offsetof(ControlBlock,opcode)==56 && offsetof(ControlBlock,ack)==88 && offsetof(ControlBlock,status)==100);
static_assert(offsetof(ControlBlock,epoch)==16 && offsetof(ControlBlock,heartbeat)==24 && offsetof(ControlBlock,request)==32);
static_assert(offsetof(ControlBlock,expectedIncarnation)==40 && offsetof(ControlBlock,expectedContext)==48 && offsetof(ControlBlock,flags)==60);
static_assert(offsetof(ControlBlock,nativeIncarnation)==72 && offsetof(ControlBlock,nativeContext)==80 && offsetof(ControlBlock,nativeReady)==96);
static_assert(offsetof(ControlBlock,hover)==104 && offsetof(ControlBlock,hostIncarnation)==112 && offsetof(ControlBlock,hostSequence)==120);
enum Opcode : std::uint32_t { none=0,hover_on=1,hover_off=2 };
enum Status : std::uint32_t { idle=0,applied=1,rejected=2,lease_lost=3 };
inline bool fresh(std::uint64_t now,std::uint64_t heartbeat) noexcept {
 return heartbeat && now>=heartbeat && now-heartbeat<timeout_ms;
}
inline bool region_transition(bool has_current,int current,int held,int previous) noexcept {
 return has_current && current>=0 && current==held && current!=previous;
}
}
