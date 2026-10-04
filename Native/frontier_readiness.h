#pragma once
#include "frontier_protocol.h"
#include <cmath>
namespace destiny_frontier {
// Diagnostic sampling has no effect on snapshot lifetime, leases or command policy.
template<class Snapshot>
std::uint32_t guardian_readiness_bits(bool inWorld,bool hasComponent,bool ownsLocalPlayer,const Snapshot& snapshot) noexcept {
 const bool checked=inWorld&&hasComponent;
 const bool finite=std::isfinite(snapshot.position[0])&&std::isfinite(snapshot.position[1])&&std::isfinite(snapshot.position[2]);
 const bool ready=inWorld&&hasComponent&&ownsLocalPlayer&&snapshot.present&&finite;
 return ready_diagnostics|(inWorld?ready_in_world:0U)|(hasComponent?ready_component:0U)|
  (checked&&ownsLocalPlayer?ready_ownership:0U)|(snapshot.present?ready_snapshot:0U)|
  (finite?ready_finite:0U)|(ready?ready_combined:0U)|(checked?ready_ownership_checked:0U);
}
template<class Snapshot>
bool guardian_ready(bool inWorld,bool hasComponent,bool ownsLocalPlayer,const Snapshot& snapshot) noexcept {
 return (guardian_readiness_bits(inWorld,hasComponent,ownsLocalPlayer,snapshot)&ready_combined)!=0;
}
struct ReadinessTransitions {
 std::uint32_t previous=0;
 bool observe(std::uint32_t bits) noexcept {
  if(previous==bits)return false;
  previous=bits;return true;
 }
};
}
