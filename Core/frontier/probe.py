import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import secrets
import time

from .ipc import Mapping, HEADER, STATE, COMMAND, MAGIC, VERSION, SIZE, OFFSETS, COMMANDS, ticks
from .store import Store
from .control import ControlMapping
from .motion import MotionMapping


def _clear_owned_state(mapping, epoch):
    with mapping.locked() as acquired:
        if acquired and HEADER.unpack_from(mapping.memory)[2] == epoch:
            HEADER.pack_into(mapping.memory, 0, MAGIC, VERSION, 0, 0)
            for offset in COMMANDS.values():
                COMMAND.pack_into(mapping.memory, offset, 0, 0)


def run(database, test_file=None, test_stop_file=None, control_file=None, scout_link=False,guardian_locomotion=False,motion_file=None):
    if test_stop_file is not None and test_file is None:
        raise ValueError('A test stop file requires the explicit file-backed test backend')
    stop_path = Path(test_stop_file) if test_stop_file is not None else None
    epoch = secrets.randbits(63) or 1
    # Register ownership immediately, before subsequent constructors/log setup.
    # ExitStack runs every cleanup even if shutdown/reset/backup itself fails.
    with ExitStack() as resources:
        store = resources.enter_context(Store(database))
        mapping = resources.enter_context(Mapping(test_file))
        path = Path(database).parent / 'Logs'
        path.mkdir(exist_ok=True)
        log = resources.enter_context(open(path / f'probe-{epoch}.jsonl', 'a', buffering=1, encoding='utf-8'))

        def emit(event, **fields):
            data = dict(event=event, utc=time.time(), test_backend=test_file is not None, **fields)
            log.write(json.dumps(data) + '\n')
            print(json.dumps(data), flush=True)

        control = None
        motion = None
        try:
            with mapping.locked() as acquired:
                if not acquired:
                    raise RuntimeError('IPC busy at startup')
                magic, version, old_epoch, heartbeat = HEADER.unpack_from(mapping.memory)
                if magic == MAGIC and old_epoch and 0 <= ticks() - heartbeat < 2000:
                    raise RuntimeError('Another core is active')
                # Adapter incarnations/counters survive a core restart in the mapping.
                if (magic, version) != (MAGIC, VERSION):
                    mapping.memory[:] = bytes(SIZE)
                HEADER.pack_into(mapping.memory, 0, MAGIC, VERSION, epoch, ticks())
            control = resources.enter_context(ControlMapping(control_file)) if test_file is None or control_file is not None else None
            if control: control.start(epoch)
            if guardian_locomotion:
                motion=resources.enter_context(MotionMapping(motion_file));motion.start(epoch)
            emit('core_started', epoch=epoch, pid=os.getpid(), scout_link=scout_link)
            previous_live = {}
            both_live = False
            nms_pulse = False
            guest = None
            while stop_path is None or not stop_path.exists():
                nms_pulse = False
                if control:
                    sample = control.status()
                    if sample is not None: guest = sample
                with mapping.locked() as acquired:
                    if acquired:
                        if HEADER.unpack_from(mapping.memory)[2] != epoch:
                            raise RuntimeError('Core epoch changed unexpectedly')
                        now = ticks()
                        HEADER.pack_into(mapping.memory, 0, MAGIC, VERSION, epoch, now)
                        live = {}
                        for role, offset in OFFSETS.items():
                            heartbeat, incarnation, seq, ready, ack, detail = STATE.unpack_from(mapping.memory, offset)
                            live[role] = bool(incarnation and ready == 1 and 0 <= now - heartbeat < 2000)
                            if live[role]:
                                delta = store.observe(role, incarnation, seq)
                                if delta:
                                    if role == 'nms': nms_pulse = True
                                    emit('runtime_observation', source=role, delta=delta, seq=seq, incarnation=incarnation, detail=detail)
                            if previous_live.get(role) != live[role]:
                                emit('adapter_status', role=role, live=live[role], ack=ack,
                                     heartbeat_age_ms=now - heartbeat, ready=ready, incarnation=incarnation,
                                     reason='live' if live[role] else
                                     'not_ready' if not incarnation or ready != 1 else 'heartbeat_stale')
                        totals = store.totals()
                        both_live = all(live.values())
                        for destination, source in [('nms', 'sunrise'), ('sunrise', 'nms')]:
                            target = totals.get(source, 0) % 1000
                            if scout_link and destination == 'nms':
                                target = int(bool(guest and guest['ready'] and guest['hover']
                                                  and guest['status'] == 1 and guest['host_incarnation']
                                                  and 0 <= now-guest['native_heartbeat'] < 2000))
                            COMMAND.pack_into(mapping.memory, COMMANDS[destination], target, int(both_live))
                        previous_live = live
                if control:
                    control.refresh(epoch,both_live,scout_link)
                    if scout_link and nms_pulse and both_live:
                        try:
                            request=control.request_hover(not bool(guest and guest['hover']))
                            emit('guardian_hover_requested',request=request,source='nms_pulse')
                        except RuntimeError as error:
                            emit('guardian_hover_not_submitted',reason=str(error))
                if motion:motion.route(epoch,both_live)
                time.sleep(.02)
            emit('core_stopped', reason='test_stop_file')
        except KeyboardInterrupt:
            emit('core_stopped', reason='keyboard_interrupt')
        finally:
            try:
                try:
                    if motion:motion.stop(epoch)
                finally:
                    if control: control.stop(epoch)
            finally:
                _clear_owned_state(mapping, epoch)


def main():
    parser = argparse.ArgumentParser(description='Destiny Frontier TEST probe — NOT A PLAYABLE GAME')
    parser.add_argument('--database', default='Saves/Guardian_Test/probe.sqlite3')
    parser.add_argument('--test-file', help='Explicit isolated transport test backend, no game integration')
    parser.add_argument('--test-stop-file', help='Graceful shutdown marker for file-backed tests only')
    parser.add_argument('--control-file', help='Isolated native control test backend')
    parser.add_argument('--scout-link', action='store_true', help='NMS bridge pulse toggles temporary native Guardian hover')
    parser.add_argument('--guardian-locomotion',action='store_true',help='Experimental Guardian movement guest; F9 in NMS arms')
    parser.add_argument('--motion-file',help='Isolated motion mapping test file')
    args = parser.parse_args()
    if args.test_stop_file is not None and args.test_file is None:
        parser.error('--test-stop-file requires --test-file')
    run(args.database, args.test_file, args.test_stop_file, args.control_file, args.scout_link,args.guardian_locomotion,args.motion_file)


if __name__ == '__main__':
    main()
