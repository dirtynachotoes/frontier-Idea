#pragma once
#include <cstdint>
namespace sunrise::client::frontier {
void start(bool hooksReady) noexcept;
void tick() noexcept;
void shutdown() noexcept;
// Called only by existing game-caller input guards; does not change OS input or focus.
bool motion_key(unsigned virtualKey,bool& held) noexcept;
void observe_region(bool has_current,int current,int held,int previous) noexcept;
void legacy_status(std::uint32_t& target,bool& connected,bool& live) noexcept;
}
