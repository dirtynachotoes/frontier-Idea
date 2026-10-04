-- Standalone TEST mission only. Do not wrap a campaign mission: this controls its phase.
-- Requires the pinned Sunrise native binding. Real region_changed events increment sequence.
-- In-game Sunrise mission script HUD displays phase = NMS positive nanite award count modulo 1000.
local acknowledgement = 0
local region = 0
local timer = "frontier_probe_poll"
local function poll(context)
    local connected, target, live = frontier_probe.exchange(0, acknowledgement, region)
    if connected and live then
        context:set_phase(target)
        acknowledgement = target
    end
    context:start_timer(timer, 500)
end
return {
    on_start = function(context, state)
        poll(context)
    end,
    on_load = function(context, state)
        poll(context)
    end,
    on_event_region_changed = function(context, state, event)
        frontier_probe.exchange(1, acknowledgement, region)
        -- Region is diagnostic only; never use an unverified field offset.
        region = 0
    end,
    on_event_timer_elapsed = function(context, state, event)
        if event.timer_name == timer then poll(context) end
    end,
}
