#pragma once
#include "frontier_protocol.h"
namespace destiny_frontier {
// Platform-independent policy, used verbatim by native consumer and standalone harness.
struct HoverPolicy {
 std::uint64_t context=1,lastEpoch=0,lastRequest=0,ack=0;
 std::uint32_t status=idle;
 bool hovering=false,wasReady=false;
 int lastSlice=-1;
 std::uint64_t lastPlayer=0;
 void world(bool ready,int slice,std::uint64_t player=0) noexcept {
  if (ready!=wasReady || (ready && (lastSlice!=slice || lastPlayer!=player))) { ++context; hovering=false; status=lease_lost; }
  wasReady=ready; lastSlice=slice; lastPlayer=player;
 }
 void tick(const ControlBlock& c,std::uint64_t now,std::uint64_t incarnation,bool ready,bool peerLive) noexcept {
  const bool wire=c.magic==control_magic && c.version==1 && c.bytes==128 && c.headerBytes==64 && c.epoch;
  if (wire && c.epoch!=lastEpoch) { lastEpoch=c.epoch; lastRequest=0; hovering=false; }
  const bool valid=wire && fresh(now,c.heartbeat);
  if (!valid || !ready || !peerLive || !(c.flags&1U)) {
   // Consume pending requests seen during loss too: returning readiness must never arm them.
   if (wire && c.request>lastRequest) {lastRequest=c.request;ack=c.request;}
   hovering=false; status=lease_lost; return;
  }
  if (!c.request || c.request==lastRequest) return;
  // Monotonic Core request IDs; do not replay older desired state.
  if (c.request<lastRequest) { hovering=false; status=rejected; return; }
  lastRequest=c.request; ack=c.request;
  if (c.opcode==hover_off) { hovering=false; status=applied; return; }
  if (c.opcode!=hover_on || c.expectedIncarnation!=incarnation || c.expectedContext!=context) {
   hovering=false; status=rejected; return;
  }
  hovering=true; status=applied;
 }
};
}
