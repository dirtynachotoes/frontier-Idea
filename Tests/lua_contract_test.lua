-- Fake context only. Verifies candidate script contract with real vendored Lua; not game runtime.
local polls, actions, phase, timers = 0, 0, 0, 0
frontier_probe = {exchange = function(action, ack, detail)
    polls = polls + 1
    actions = actions + action
    return true, 42, true
end}
local context = {
    set_phase = function(self, value) phase = value end,
    start_timer = function(self, name, milliseconds)
        assert(name == "frontier_probe_poll" and milliseconds == 500)
        timers = timers + 1
    end,
}
local mission = dofile("Adapters/Sunrise/frontier_probe.lua")
mission.on_start(context, {})
assert(phase == 42 and timers == 1)
mission.on_event_region_changed(context, {}, {})
assert(actions == 1)
mission.on_event_timer_elapsed(context, {}, {timer_name = "other"})
assert(timers == 1)
mission.on_event_timer_elapsed(context, {}, {timer_name = "frontier_probe_poll"})
assert(timers == 2 and polls == 3)
print("Lua contract test passed (FAKE context; no game runtime)")
