#pragma once
#include <cstdint>
namespace sunrise::client::frontier {
void start(bool hooksReady) noexcept;
void tick() noexcept;
void shutdown() noexcept;
void observe_region(bool has_current,int current,int held,int previous) noexcept;
void legacy_status(std::uint32_t& target,bool& connected,bool& live) noexcept;
}
