#pragma once
// Frontier focus lease (opt-in, lease-bounded).
// Measured 2026-10-04: with NMS in front, the offline guest made zero game-image GetKeyState /
// GetAsyncKeyState calls for the authored movement keys, so Guardian locomotion never ran.
// While (and only while) an armed, fresh Frontier motion lease exists, game-image callers are told
// that the game's own window still has focus, deactivation messages are held back from the game,
// and game cursor warps/clips are not applied to the shared desktop. Sunrise, Dear ImGui and the
// OS keep seeing real state. No SetForegroundWindow, no SendInput, no OS-wide input injection.
#include <Windows.h>
#include <cstdint>
namespace sunrise::client::frontier::focus {
// Attaches the game-caller focus guards. Failure leaves everything detached and is logged.
bool install() noexcept;
void uninstall() noexcept;
// Called from the native frame tick. until==0 ends the lease; otherwise the lease expires on its
// own at `until` (GetTickCount64 ms) even if ticks stop. keyCalls is the running count of
// game-image polled key calls that reached Frontier, reported for diagnostics.
void set_lease(std::uint64_t until,std::uint64_t now,std::uint64_t keyCalls) noexcept;
// Called first by the subclassed game window procedure. Records the game window and returns true
// when a deactivation message must be held back from the game because the lease is active.
bool filter_message(HWND window,UINT message,WPARAM word) noexcept;
}
