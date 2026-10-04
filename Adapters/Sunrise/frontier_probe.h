// Original Destiny Frontier code. Inserted into Sunrise under GPL-3.0-or-later.
// Existing Protocol 1 bridge is preserved unchanged. Spatial telemetry uses a separate
// read-only diagnostics mapping and never writes player/camera transforms.
#pragma once
#include <cstdint>
#include <cstring>
#include <windows.h>
#include "lua.h"
#include "lauxlib.h"

#include "../../../client/player/player_position.h"

namespace destiny_frontier_probe {
constexpr wchar_t name[] = L"Local\\DestinyFrontier_Probe_v1";
constexpr wchar_t mutex_name[] = L"Local\\DestinyFrontier_Probe_v1_mutex";
struct Header { std::uint32_t magic, version; std::uint64_t epoch, heartbeat; std::uint64_t pad; };
struct State { std::uint64_t heartbeat, incarnation; std::uint32_t seq, ready, ack, detail; };
struct Command { std::uint32_t target, live; std::uint64_t pad[3]; };
static_assert(sizeof(Header) == 32 && sizeof(State) == 32 && sizeof(Command) == 32);
struct Bridge {
    HANDLE mapping = nullptr, mutex = nullptr;
    unsigned char* view = nullptr;
    std::uint64_t incarnation = (static_cast<std::uint64_t>(GetCurrentProcessId()) << 32) ^ GetTickCount64();
    ~Bridge() { close(); }
    void close() {
        if (view) UnmapViewOfFile(view);
        if (mapping) CloseHandle(mapping);
        if (mutex) CloseHandle(mutex);
        view = nullptr; mapping = nullptr; mutex = nullptr;
    }
    bool exchange(std::uint32_t sequence, std::uint32_t ack, std::uint32_t detail, std::uint32_t& target, bool& live) {
        if (!view) {
            mutex = OpenMutexW(SYNCHRONIZE | MUTEX_MODIFY_STATE, FALSE, mutex_name);
            mapping = OpenFileMappingW(FILE_MAP_ALL_ACCESS, FALSE, name);
            if (!mutex || !mapping) { close(); return false; }
            view = static_cast<unsigned char*>(MapViewOfFile(mapping, FILE_MAP_ALL_ACCESS, 0, 0, 192));
            if (!view) { close(); return false; }
        }
        const DWORD result = WaitForSingleObject(mutex, 0);
        if (result == WAIT_ABANDONED) { ReleaseMutex(mutex); close(); return false; }
        if (result != WAIT_OBJECT_0) return false;
        Header h{};
        std::memcpy(&h, view, sizeof(h));
        const auto now = GetTickCount64();
        if (h.magic != 0x52465444 || h.version != 1 || !h.epoch || now < h.heartbeat || now - h.heartbeat > 2000) {
            ReleaseMutex(mutex); return false;
        }
        State s{now, incarnation ? incarnation : 1, sequence, 1, ack, detail};
        std::memcpy(view + 64, &s, sizeof(s));
        Command c{};
        std::memcpy(&c, view + 128, sizeof(c));
        ReleaseMutex(mutex);
        if (c.target > 999 || c.live > 1) return false;
        target = c.target; live = c.live == 1;
        return true;
    }
};

// Separate read-only spatial diagnostics ABI.
// Layout: 64-byte header, 128-byte NMS slot, 128-byte Sunrise slot.
constexpr wchar_t spatial_name[] = L"Local\\DestinyFrontier_Spatial_v1";
constexpr wchar_t spatial_mutex_name[] = L"Local\\DestinyFrontier_Spatial_v1_mutex";
constexpr std::uint32_t spatial_magic = 0x53544644; // "DFTS" in little-endian bytes
constexpr std::uint32_t spatial_version = 1;
constexpr std::uint32_t spatial_bytes = 320;
constexpr std::uint32_t spatial_header_bytes = 64;
constexpr std::uint32_t spatial_sunrise_offset = 192;

enum SpatialFlags : std::uint32_t {
    spatial_player_position = 1U << 0,
    spatial_camera_position = 1U << 1,
    spatial_forward = 1U << 2,
    spatial_up = 1U << 3,
    spatial_right = 1U << 4,
};

struct SpatialHeader {
    std::uint32_t magic{};
    std::uint32_t version{};
    std::uint32_t bytes{};
    std::uint32_t headerBytes{};
    std::uint64_t epoch{};
    unsigned char reserved[40]{};
};
struct SpatialSlot {
    std::uint64_t heartbeat{};
    std::uint64_t incarnation{};
    std::uint32_t sequence{};
    std::uint32_t flags{};
    std::uint64_t context{};
    float playerPosition[3]{};
    float cameraPosition[3]{};
    float forward[3]{};
    float up[3]{};
    float right[3]{};
    unsigned char reserved[36]{};
};
static_assert(sizeof(SpatialHeader) == 64);
static_assert(sizeof(SpatialSlot) == 128);

struct SpatialBridge {
    HANDLE mapping = nullptr, mutex = nullptr;
    unsigned char* view = nullptr;
    std::uint64_t incarnation =
        (static_cast<std::uint64_t>(GetCurrentProcessId()) << 32) ^ GetTickCount64();
    std::uint32_t sequence = 0;

    ~SpatialBridge() { close(); }

    void close() {
        if (view) UnmapViewOfFile(view);
        if (mapping) CloseHandle(mapping);
        if (mutex) CloseHandle(mutex);
        view = nullptr; mapping = nullptr; mutex = nullptr;
    }

    bool ensure_open() {
        if (view) return true;
        mutex = CreateMutexW(nullptr, FALSE, spatial_mutex_name);
        mapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0,
                                     spatial_bytes, spatial_name);
        if (!mutex || !mapping) { close(); return false; }
        view = static_cast<unsigned char*>(
            MapViewOfFile(mapping, FILE_MAP_ALL_ACCESS, 0, 0, spatial_bytes));
        if (!view) { close(); return false; }
        return true;
    }

    bool publish() {
        if (!ensure_open()) return false;

        const DWORD wait = WaitForSingleObject(mutex, 0);
        if (wait == WAIT_ABANDONED) { ReleaseMutex(mutex); close(); return false; }
        if (wait != WAIT_OBJECT_0) return false;

        SpatialHeader header{};
        std::memcpy(&header, view, sizeof(header));
        if (header.magic == 0 && header.version == 0 && header.bytes == 0) {
            header.magic = spatial_magic;
            header.version = spatial_version;
            header.bytes = spatial_bytes;
            header.headerBytes = spatial_header_bytes;
            header.epoch = GetTickCount64();
            if (!header.epoch) header.epoch = 1;
            std::memcpy(view, &header, sizeof(header));
        } else if (header.magic != spatial_magic || header.version != spatial_version
                   || header.bytes != spatial_bytes || header.headerBytes != spatial_header_bytes) {
            ReleaseMutex(mutex);
            return false;
        }

        SpatialSlot slot{};
        slot.heartbeat = GetTickCount64();
        slot.incarnation = incarnation ? incarnation : 1;
        if (sequence != UINT32_MAX) ++sequence;
        slot.sequence = sequence;

        const auto player = sunrise::client::player::position::snapshot();
        if (player.present) {
            slot.flags |= spatial_player_position;
            for (std::size_t i = 0; i < 3; ++i) slot.playerPosition[i] = player.position[i];
        }

        sunrise::client::hooks::teleport::CameraPose camera{};
        if (sunrise::client::hooks::teleport::camera_pose(camera)) {
            slot.flags |= spatial_camera_position | spatial_forward | spatial_up;
            for (std::size_t i = 0; i < 3; ++i) {
                slot.cameraPosition[i] = camera.position[i];
                slot.forward[i] = camera.forward[i];
                slot.up[i] = camera.up[i];
            }
        }

        std::memcpy(view + spatial_sunrise_offset, &slot, sizeof(slot));
        ReleaseMutex(mutex);
        return true;
    }
};

// Narrow binding: all arguments validated BEFORE acquiring mutex. No Lua allocations while locked.
inline int exchange(lua_State* state) {
    auto action = luaL_checkinteger(state, 1);
    auto ack = luaL_checkinteger(state, 2);
    auto detail = luaL_checkinteger(state, 3);
    if (action < 0 || action > 1 || ack < 0 || ack > 999 || detail < 0 || detail > UINT32_MAX)
        return luaL_error(state, "frontier probe argument out of range");
    static Bridge bridge;
    static SpatialBridge spatial;
    static std::uint32_t sequence = 0;
    if (action == 1 && sequence < 1000000) ++sequence;
    std::uint32_t target = 0;
    bool live = false;
    const bool connected = bridge.exchange(sequence, static_cast<std::uint32_t>(ack),
                                           static_cast<std::uint32_t>(detail), target, live);

    // Diagnostics only. This reads existing Sunrise snapshots and publishes them to a
    // separate mapping. It never writes a game transform, velocity, camera, or save.
    (void)spatial.publish();

    lua_pushboolean(state, connected);
    lua_pushinteger(state, target);
    lua_pushboolean(state, live);
    return 3;
}
inline void install(lua_State* state) {
    lua_newtable(state);
    lua_pushcfunction(state, exchange);
    lua_setfield(state, -2, "exchange");
    lua_setglobal(state, "frontier_probe");
}
}
