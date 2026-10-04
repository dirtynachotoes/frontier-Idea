# One readiness-lifetime runtime session

Install this single consolidated diagnostics-only candidate once using the existing backed-up installer, known paths and offline fingerprint. Keep configuration/saves/loaders unchanged. Close Core and both games for installation; no individual DLL copying is required.

This session resolves only which readiness condition changes after the Guardian becomes ready. No speculative lifetime fix is included. Already-proven bridge, heartbeat, Spatial V2, F8/control and native lifecycle need no separate tests.

1. Start Core with the existing configuration, start one already-supported offline Sunrise activity and let the Guardian become active normally. Start NMS and keep it foreground.
2. From the existing Core command environment run `python -m frontier.control status`. Read the ready_* predicates and readiness_diagnostics. If Guardian-ready becomes true, leave the Guardian idle and sample status for about 30 seconds to cover the previously observed roughly two-second loss. In PowerShell, `1..30 | ForEach-Object { python -m frontier.control status; Start-Sleep -Seconds 1 }` performs those samples without relaunching games.
3. If readiness drops or never becomes true, keep the status output and matching Sunrise ev=frontier_readiness transition lines (including tick_ms/context), then stop. Null ready_ownership with ready_ownership_checked=false means skipped evaluation, not proven ownership failure. ready_combined=true with ready_host=false identifies the separate host gate. Several false predicates are reported together; do not infer unseen engine behavior.
4. If readiness remains stable, press F8 once to confirm the existing command still acknowledges/activates hover and NMS assist, then once more for clean disable/baseline. Stop and retain the status/logs.

The predicate evidence determines the next narrow fix. This candidate neither claims the lifetime problem is fixed nor schedules another speculative runtime test.
