"""Deterministic liveness; engine stubs never certify game hooks."""
import ast
import logging
from pathlib import Path
import secrets
import sys
import tempfile
import time
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Core'))
from frontier.ipc import Mapping, HEADER, STATE, COMMAND, MAGIC, VERSION, OFFSETS, COMMANDS

class LivenessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.mapping = Mapping(Path(self.temp.name) / 'ipc')
        self.addCleanup(self.mapping.close)
        self.now = 10000
        clock = patch('frontier.ipc.ticks', side_effect=lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)
        self.seed()

    def seed(self, core=10000, peer=10000, live=1, ready=1, epoch=123):
        HEADER.pack_into(self.mapping.memory, 0, MAGIC, VERSION, epoch, core)
        STATE.pack_into(self.mapping.memory, OFFSETS['sunrise'], peer, 222, 1, ready, 0, 0)
        COMMAND.pack_into(self.mapping.memory, COMMANDS['nms'], 9, live)

    def poll(self, ready=True, incarnation=111):
        return self.mapping.exchange('nms', incarnation, 0, ready)

    def busy(self):
        return patch.object(self.mapping._lock, 'try_acquire', return_value=False)

    def test_single_miss_keeps_valid_effect(self):
        expected = self.poll()
        self.now += 100
        with self.busy(): self.assertEqual(self.poll(), expected)
        self.assertEqual(self.mapping.last_exchange['status'], 'busy_cached')
        self.assertEqual(self.mapping.last_exchange['peer_age_ms'], 100)

    def test_real_file_backend_contention_preserves_live_result(self):
        expected = self.poll()
        results, errors = [], []
        def worker():
            try:
                results.append(self.poll())
            except BaseException as error:
                errors.append(error)
        with Mapping(self.mapping.file.name) as holder:
            with holder.locked() as acquired:
                self.assertTrue(acquired)
                thread = threading.Thread(target=worker)
                thread.start()
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                self.assertEqual(results, [expected])
        self.assertEqual(self.mapping.last_exchange['status'], 'busy_cached')

    def test_repeated_misses_never_extend_peer_deadline(self):
        self.poll()
        with self.busy():
            for elapsed in (100, 500, 1000, 1999):
                self.now = 10000 + elapsed
                self.assertEqual(self.poll(), (123, 9, True))
            self.now = 12000
            self.assertIsNone(self.poll())
            self.assertEqual(self.mapping.last_exchange['status'], 'busy_expired')
            self.now += 1
            self.assertIsNone(self.poll())

    def test_old_peer_timestamp_not_receipt_time_bounds_cache(self):
        self.seed(peer=8500)
        self.assertTrue(self.poll()[2])
        self.now = 10500
        with self.busy(): self.assertIsNone(self.poll())

    def test_original_core_boundary_preserved(self):
        self.seed(core=8500)
        self.assertTrue(self.poll()[2])
        with self.busy():
            self.now = 10500
            self.assertTrue(self.poll()[2])
            self.now = 10501
            self.assertIsNone(self.poll())

    def test_no_sample_or_different_incarnation_cannot_cache(self):
        with self.busy(): self.assertIsNone(self.poll())
        self.poll()
        with self.busy():
            self.assertIsNone(self.poll(incarnation=112))
            self.assertIsNone(self.mapping.exchange('sunrise', 222, 0, True))

    def test_not_ready_clears_cached_effect(self):
        self.poll()
        with self.busy():
            self.assertIsNone(self.poll(ready=False))
            self.assertIsNone(self.poll())

    def test_explicit_disconnect_clears_cache_immediately(self):
        self.poll()
        self.seed(live=0)
        self.assertEqual(self.poll(), (123, 9, False))
        with self.busy(): self.assertIsNone(self.poll())

    def test_stale_peer_overrides_old_live_command(self):
        self.poll()
        self.now = 12000
        HEADER.pack_into(self.mapping.memory, 0, MAGIC, VERSION, 123, self.now)
        self.assertEqual(self.poll(), (123, 9, False))
        self.assertEqual(self.mapping.last_exchange['status'], 'peer_stale')

    def test_peer_not_ready_invalid_epoch_version_and_future_clock(self):
        for case in ('ready', 'epoch', 'version', 'future_peer', 'future_core'):
            self.seed()
            self.poll()
            if case == 'ready': self.seed(ready=0)
            elif case == 'epoch': self.seed(epoch=0)
            elif case == 'version': HEADER.pack_into(self.mapping.memory, 0, MAGIC, VERSION+1, 123, self.now)
            elif case == 'future_peer': self.seed(peer=10001)
            else: self.seed(core=10001)
            self.assertFalse(self.poll() and self.poll()[2], case)
            with self.busy(): self.assertIsNone(self.poll(), case)

    def test_pending_event_published_on_recovery(self):
        self.poll()
        with self.busy(): self.mapping.exchange('nms', 111, 4, True)
        self.assertEqual(STATE.unpack_from(self.mapping.memory, OFFSETS['nms'])[2], 0)
        self.assertTrue(self.mapping.exchange('nms', 111, 4, True)[2])
        self.assertEqual(STATE.unpack_from(self.mapping.memory, OFFSETS['nms'])[2], 4)

    def adapter(self):
        path = Path(__file__).resolve().parents[1] / 'Adapters/NMS/frontier_nms_probe.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        cls = next(x for x in tree.body if isinstance(x, ast.ClassDef))
        for method in cls.body:
            if isinstance(method, ast.FunctionDef): method.decorator_list = []
        engine = SimpleNamespace(GcPlayerGlobals=SimpleNamespace(GroundWalkSpeed=4.400000095367432))
        namespace = dict(Mod=object, Path=Path, __file__=str(Path(self.temp.name)/'frontier_nms_probe.py'), secrets=secrets, time=time, gameData=SimpleNamespace(player_state=object()), globals=engine, Mapping=Mapping, log=logging.getLogger('DestinyFrontier.NMS.test'))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), str(path), 'exec'), namespace)
        adapter = namespace[cls.name]()
        adapter.mapping = self.mapping
        return adapter, engine

    def update(self, adapter):
        adapter.last_poll = 0
        adapter.update(None)

    def test_actual_adapter_boost_contention_expiry_and_recovery(self):
        adapter, engine = self.adapter()
        self.update(adapter)
        boost = 5.5000001192092896
        self.assertEqual(engine.GcPlayerGlobals.GroundWalkSpeed, boost)
        with self.busy():
            self.now += 100
            self.update(adapter)
            self.assertEqual(engine.GcPlayerGlobals.GroundWalkSpeed, boost)
            self.now = 12000
            self.update(adapter)
            self.assertEqual(engine.GcPlayerGlobals.GroundWalkSpeed, adapter.baseline)
        self.seed(core=self.now, peer=self.now)
        self.update(adapter)
        self.assertEqual(engine.GcPlayerGlobals.GroundWalkSpeed, boost)
        self.seed(core=self.now, peer=self.now, live=0)
        self.update(adapter)
        self.assertEqual(engine.GcPlayerGlobals.GroundWalkSpeed, adapter.baseline)

    def test_actual_adapter_manual_pulse_and_speed_logs_preserved(self):
        adapter, engine = self.adapter()
        adapter.manual_trigger.touch()
        with self.assertLogs('DestinyFrontier.NMS.test', level='INFO') as capture: self.update(adapter)
        self.assertFalse(adapter.manual_trigger.exists())
        self.assertEqual(adapter.sequence, 1)
        for message in ('Manual Frontier pulse triggered', 'Frontier speed target=9', 'Frontier IPC status=live'):
            self.assertTrue(any(message in line for line in capture.output))
