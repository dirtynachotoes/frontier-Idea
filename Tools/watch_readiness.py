"""Read-only Guardian readiness watcher (diagnostic only, 2026-10-04).

Polls the existing native Control status block (Local\\DestinyFrontier_Control_v1) and
prints/records every change of the native readiness bits the 5ee57985 guest already
publishes. It never writes to the Control block, never submits commands, and does not
change any lease, timeout or readiness policy.

Run from the Frontier root (or via WatchReadiness.cmd) while Sunrise is running.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'Core'))
from frontier.control import ControlMapping, READINESS_BITS  # noqa: E402
from frontier.ipc import ticks  # noqa: E402

ORDER = ['ready_in_world', 'ready_component', 'ready_ownership_checked', 'ready_ownership',
         'ready_snapshot', 'ready_finite', 'ready_combined', 'ready_host']
SHORT = dict(ready_in_world='in_world', ready_component='component',
             ready_ownership_checked='own_checked', ready_ownership='owns_local',
             ready_snapshot='snapshot', ready_finite='finite', ready_combined='GUARDIAN',
             ready_host='host')


def key(s):
    return (s['readiness_bits'], s['ready'], s['incarnation'], s['context'])


def main():
    logs = ROOT / 'Saves' / 'Guardian_Test' / 'Logs'
    logs.mkdir(parents=True, exist_ok=True)
    out = logs / f'readiness-watch-{int(time.time())}.jsonl'
    print(f'Watching native readiness. Recording to {out}\nCtrl+C to stop.\n')
    last = None
    busy = 0
    with ControlMapping() as m, open(out, 'a', encoding='utf-8') as f:
        while True:
            s = m.status()
            if s is None:
                busy += 1
                time.sleep(0.01)
                continue
            now = ticks()
            s['native_age_ms'] = now - s['native_heartbeat'] if s['native_heartbeat'] else None
            if last is None or key(s) != key(last):
                changed = []
                if last is not None:
                    for name in ORDER:
                        if s.get(name) != last.get(name):
                            changed.append(f"{SHORT[name]} {last.get(name)}->{s.get(name)}")
                    if s['context'] != last['context']:
                        changed.append(f"context {last['context']}->{s['context']}")
                    if s['incarnation'] != last['incarnation']:
                        changed.append('INCARNATION CHANGED')
                bits = ' '.join(f"{SHORT[n]}={'-' if s.get(n) is None else int(s.get(n))}" for n in ORDER)
                stamp = time.strftime('%H:%M:%S') + f'.{int(time.time()*1000)%1000:03d}'
                print(f"{stamp} tick={now} ready={int(s['ready'])} age={s['native_age_ms']}ms | {bits}")
                if changed:
                    print('           CHANGED: ' + '; '.join(changed))
                f.write(json.dumps(dict(utc=time.time(), tick=now, changed=changed, busy_misses=busy, **s)) + '\n')
                f.flush()
                last = s
            time.sleep(0.02)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
