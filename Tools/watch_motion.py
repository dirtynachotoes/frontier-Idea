"""Read-only Guardian motion watcher (diagnostic only).

Reads Local\\DestinyFrontier_Motion_v1 and prints whenever the host intent (F9 arm / keys),
Core-routed intent, or the native Guardian result (validity, input-scan reads, measured
displacement) changes. Never writes to the mapping.
"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'Core'))
from frontier.motion import MotionMapping, HEADER, INTENT, RESULT  # noqa: E402
from frontier.ipc import ticks  # noqa: E402
KEYS = ['W', 'S', 'A', 'D', 'Shift', 'Space']
def keys(k): return '+'.join(n for i, n in enumerate(KEYS) if k & (1 << i)) or '-'
def main():
    logs = ROOT / 'Saves' / 'Guardian_Test' / 'Logs'; logs.mkdir(parents=True, exist_ok=True)
    out = logs / f'motion-watch-{int(time.time())}.jsonl'
    print(f'Watching Guardian motion channel. Recording to {out}\n')
    last = None; last_print = 0; last_scans = None
    m = MotionMapping()
    with open(out, 'a', encoding='utf-8') as f:
        while True:
            with m.locked() as ok:
                if not ok: time.sleep(0.005); continue
                h = HEADER.unpack_from(m.memory); hi = INTENT.unpack_from(m.memory, 64)
                ri = INTENT.unpack_from(m.memory, 128); r = RESULT.unpack_from(m.memory, 192)
            now = ticks()
            state = dict(core_epoch=h[4], core_age=now - h[5] if h[5] else None,
                         host_keys=keys(hi[3]), host_armed=hi[4] == 3, host_age=now - hi[0] if hi[0] else None,
                         routed_keys=keys(ri[3]), routed_armed=ri[4] == 3,
                         result_valid=r[7] == 1, result_age=now - r[0] if r[0] else None,
                         scan_reads=r[8], generation=r[9], displacement=[round(v, 3) for v in r[4:7]])
            sig = (state['host_keys'], state['host_armed'], state['routed_keys'], state['routed_armed'],
                   state['result_valid'], state['generation'], tuple(state['displacement']))
            if sig != last or (state['scan_reads'] != last_scans and time.monotonic() - last_print > 0.5):
                stamp = time.strftime('%H:%M:%S') + f'.{int(time.time()*1000)%1000:03d}'
                print(f"{stamp} armed host={int(state['host_armed'])} routed={int(state['routed_armed'])} keys host={state['host_keys']} routed={state['routed_keys']} "
                      f"| result valid={int(state['result_valid'])} scans={state['scan_reads']} gen={state['generation']} disp={state['displacement']}")
                f.write(json.dumps(dict(utc=time.time(), tick=now, **state)) + '\n'); f.flush()
                last = sig; last_print = time.monotonic(); last_scans = state['scan_reads']
            time.sleep(0.02)
if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt: pass
