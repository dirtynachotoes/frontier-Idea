#pragma once
#include <cmath>
namespace destiny_frontier {
// Consume Sunrise's published snapshot. A failed fresh body read does not invalidate it.
// World/component/ownership checks remain mandatory; lease handling stays in HoverPolicy.
template<class Snapshot>
bool guardian_ready(bool inWorld,bool hasComponent,bool ownsLocalPlayer,const Snapshot& snapshot) noexcept {
 return inWorld&&hasComponent&&ownsLocalPlayer&&snapshot.present&&
  std::isfinite(snapshot.position[0])&&std::isfinite(snapshot.position[1])&&std::isfinite(snapshot.position[2]);
}
}
