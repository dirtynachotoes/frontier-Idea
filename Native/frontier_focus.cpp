// Frontier focus lease. See frontier_focus.h for the measured reason and the exact scope.
#include "frontier_focus.h"
#include <array>
#include <atomic>
#include <cstddef>
#include <intrin.h>
#include "../hooking/detour.h"
#include "../diagnostics/module_range.h"
#include "../../core/logging/log.h"
namespace sunrise::client::frontier::focus {
namespace {
enum Slot : std::size_t {foregroundSlot,activeSlot,focusSlot,cursorSlot,clipSlot,slotCount};
using GetWindowFn=HWND(WINAPI*)();
using SetCursorPosFn=BOOL(WINAPI*)(int,int);
using ClipCursorFn=BOOL(WINAPI*)(const RECT*);
std::array<hooking::detour::Handle,slotCount> handles{};
std::array<void*,slotCount> targets{};
diagnostics::ModuleRange gameRange{};
HMODULE user32=nullptr;
std::atomic_bool installed{false};
std::atomic_uint64_t leaseUntil{0};
std::atomic<HWND> gameWindow{nullptr};
std::array<std::atomic_uint64_t,slotCount> gameCalls{};
std::array<std::atomic_uint64_t,slotCount> answered{};
std::atomic_uint64_t swallowed{0},posted{0};
// Tick-thread state only.
bool leaseWasActive=false;
std::uint64_t lastReport=0;
template<class Function> Function original(Slot slot) noexcept {
 void* entry=handles[slot].original;
 if(entry==nullptr)entry=targets[slot];
 return reinterpret_cast<Function>(entry);
}
bool from_game(const void* caller) noexcept {
 return diagnostics::contains(gameRange,reinterpret_cast<std::uintptr_t>(caller));
}
HWND leased_window() noexcept {
 const std::uint64_t until=leaseUntil.load(std::memory_order_acquire);
 if(until==0||GetTickCount64()>=until)return nullptr;
 return gameWindow.load(std::memory_order_acquire);
}
HWND answer_window(Slot slot,const void* caller) noexcept {
 if(from_game(caller)){
  gameCalls[slot].fetch_add(1,std::memory_order_relaxed);
  if(HWND window=leased_window()){answered[slot].fetch_add(1,std::memory_order_relaxed);return window;}
 }
 const GetWindowFn next=original<GetWindowFn>(slot);
 return next!=nullptr?next():nullptr;
}
__declspec(noinline) HWND WINAPI get_foreground_window() noexcept {return answer_window(foregroundSlot,_ReturnAddress());}
__declspec(noinline) HWND WINAPI get_active_window() noexcept {return answer_window(activeSlot,_ReturnAddress());}
__declspec(noinline) HWND WINAPI get_focus() noexcept {return answer_window(focusSlot,_ReturnAddress());}
__declspec(noinline) BOOL WINAPI set_cursor_pos(int x,int y) noexcept {
 if(from_game(_ReturnAddress())){
  gameCalls[cursorSlot].fetch_add(1,std::memory_order_relaxed);
  // The player's cursor belongs to the host window while leased; the game must not warp it.
  if(leased_window()!=nullptr){answered[cursorSlot].fetch_add(1,std::memory_order_relaxed);return TRUE;}
 }
 const SetCursorPosFn next=original<SetCursorPosFn>(cursorSlot);
 return next!=nullptr?next(x,y):FALSE;
}
__declspec(noinline) BOOL WINAPI clip_cursor(const RECT* rect) noexcept {
 if(from_game(_ReturnAddress())){
  gameCalls[clipSlot].fetch_add(1,std::memory_order_relaxed);
  // Never confine the shared desktop cursor to the hidden guest window while leased.
  if(rect!=nullptr&&leased_window()!=nullptr){answered[clipSlot].fetch_add(1,std::memory_order_relaxed);return TRUE;}
 }
 const ClipCursorFn next=original<ClipCursorFn>(clipSlot);
 return next!=nullptr?next(rect):FALSE;
}
bool process_is_foreground() noexcept {
 const GetWindowFn next=original<GetWindowFn>(foregroundSlot);
 const HWND foreground=next!=nullptr?next():nullptr;
 if(foreground==nullptr)return false;
 DWORD processId=0;(void)GetWindowThreadProcessId(foreground,&processId);
 return processId==GetCurrentProcessId();
}
unsigned long long load(const std::atomic_uint64_t& value) noexcept {
 return static_cast<unsigned long long>(value.load(std::memory_order_relaxed));
}
void report(const char* stage,std::uint64_t keyCalls) noexcept {
 core::log::writef(core::log::Channel::client,core::log::Level::info,
  "ev=frontier_focus stage=%s installed=%u window=%u key_calls=%llu fg=%llu/%llu active=%llu/%llu focus=%llu/%llu cursor=%llu/%llu clip=%llu/%llu swallowed=%llu posted=%llu",
  stage,static_cast<unsigned>(installed.load()),static_cast<unsigned>(gameWindow.load()!=nullptr),
  static_cast<unsigned long long>(keyCalls),
  load(answered[foregroundSlot]),load(gameCalls[foregroundSlot]),load(answered[activeSlot]),load(gameCalls[activeSlot]),
  load(answered[focusSlot]),load(gameCalls[focusSlot]),load(answered[cursorSlot]),load(gameCalls[cursorSlot]),
  load(answered[clipSlot]),load(gameCalls[clipSlot]),load(swallowed),load(posted));
}
}
bool install() noexcept {
 if(installed.load(std::memory_order_acquire))return true;
 if(!diagnostics::module_range(GetModuleHandleW(nullptr),gameRange)){
  core::log::write(core::log::Channel::client,core::log::Level::warn,"ev=frontier_focus stage=install result=fail reason=image");
  return false;
 }
 user32=LoadLibraryExW(L"user32.dll",nullptr,LOAD_LIBRARY_SEARCH_SYSTEM32);
 if(user32==nullptr){gameRange={};return false;}
 targets[foregroundSlot]=reinterpret_cast<void*>(GetProcAddress(user32,"GetForegroundWindow"));
 targets[activeSlot]=reinterpret_cast<void*>(GetProcAddress(user32,"GetActiveWindow"));
 targets[focusSlot]=reinterpret_cast<void*>(GetProcAddress(user32,"GetFocus"));
 targets[cursorSlot]=reinterpret_cast<void*>(GetProcAddress(user32,"SetCursorPos"));
 targets[clipSlot]=reinterpret_cast<void*>(GetProcAddress(user32,"ClipCursor"));
 for(void* target:targets){
  if(target==nullptr){targets={};gameRange={};FreeLibrary(user32);user32=nullptr;return false;}
 }
 const std::array<hooking::detour::Spec,slotCount> specs{
  hooking::detour::Spec{targets[foregroundSlot],reinterpret_cast<void*>(&get_foreground_window)},
  hooking::detour::Spec{targets[activeSlot],reinterpret_cast<void*>(&get_active_window)},
  hooking::detour::Spec{targets[focusSlot],reinterpret_cast<void*>(&get_focus)},
  hooking::detour::Spec{targets[cursorSlot],reinterpret_cast<void*>(&set_cursor_pos)},
  hooking::detour::Spec{targets[clipSlot],reinterpret_cast<void*>(&clip_cursor)},
 };
 if(!hooking::detour::install(specs,handles)){
  targets={};gameRange={};FreeLibrary(user32);user32=nullptr;
  core::log::write(core::log::Channel::client,core::log::Level::warn,"ev=frontier_focus stage=install result=fail reason=attach");
  return false;
 }
 installed.store(true,std::memory_order_release);
 core::log::write(core::log::Channel::client,core::log::Level::info,"ev=frontier_focus stage=install result=ok");
 return true;
}
void uninstall() noexcept {
 leaseUntil.store(0,std::memory_order_release);
 if(!installed.load(std::memory_order_acquire))return;
 if(!hooking::detour::uninstall(handles)){
  core::log::write(core::log::Channel::client,core::log::Level::warn,"ev=frontier_focus stage=uninstall result=fail");
  return;
 }
 installed.store(false,std::memory_order_release);
 targets={};gameRange={};
 if(user32!=nullptr){FreeLibrary(user32);user32=nullptr;}
}
void set_lease(std::uint64_t until,std::uint64_t now,std::uint64_t keyCalls) noexcept {
 const bool active=installed.load(std::memory_order_acquire)&&until>now;
 leaseUntil.store(active?until:0,std::memory_order_release);
 const HWND window=gameWindow.load(std::memory_order_acquire);
 if(active&&!leaseWasActive){
  // The game already saw its deactivation before the host armed; tell it once it is active.
  if(window!=nullptr&&PostMessageW(window,WM_ACTIVATEAPP,TRUE,0)!=FALSE)posted.fetch_add(1,std::memory_order_relaxed);
  report("lease_start",keyCalls);lastReport=now;
 }else if(!active&&leaseWasActive){
  // Return the game to its true state unless the player really put it in front meanwhile.
  if(window!=nullptr&&!process_is_foreground()&&PostMessageW(window,WM_ACTIVATEAPP,FALSE,0)!=FALSE)posted.fetch_add(1,std::memory_order_relaxed);
  report("lease_end",keyCalls);
 }else if(active&&now-lastReport>=2000){
  report("lease",keyCalls);lastReport=now;
 }
 leaseWasActive=active;
}
bool filter_message(HWND window,UINT message,WPARAM word) noexcept {
 if(window!=nullptr&&gameWindow.load(std::memory_order_relaxed)!=window)gameWindow.store(window,std::memory_order_release);
 if(leased_window()==nullptr)return false;
 const bool deactivation=(message==WM_ACTIVATEAPP&&word==0)||
  (message==WM_ACTIVATE&&LOWORD(word)==WA_INACTIVE)||message==WM_KILLFOCUS;
 if(deactivation)swallowed.fetch_add(1,std::memory_order_relaxed);
 return deactivation;
}
}
