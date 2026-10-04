#pragma once
#include <cstdint>
#include "lua.h"
#include "lauxlib.h"
#include "../../../client/frontier/frontier_native.h"
namespace destiny_frontier_probe {
inline int exchange(lua_State* state) {
 auto action=luaL_checkinteger(state,1),ack=luaL_checkinteger(state,2),detail=luaL_checkinteger(state,3);
 if(action<0||action>1||ack<0||ack>999||detail<0||static_cast<std::uint64_t>(detail)>UINT32_MAX)
  return luaL_error(state,"frontier probe argument out of range");
 std::uint32_t target=0;bool connected=false,live=false;
 sunrise::client::frontier::legacy_status(target,connected,live);
 lua_pushboolean(state,connected);lua_pushinteger(state,target);lua_pushboolean(state,live);return 3;
}
inline void install(lua_State* state){lua_newtable(state);lua_pushcfunction(state,exchange);lua_setfield(state,-2,"exchange");lua_setglobal(state,"frontier_probe");}
}
