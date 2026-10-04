"""Lightweight core tests. Fake packets are NEVER evidence of game integration."""
from contextlib import closing, ExitStack
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Core'))
from frontier.ipc import Mapping, HEADER, STATE, COMMAND, MAGIC, VERSION, SIZE, ticks
from frontier.store import Store


def query_database(path, sql):
    with closing(sqlite3.connect(path)) as connection:
        with closing(connection.execute(sql)) as cursor:
            return cursor.fetchall()


class PersistenceTests(unittest.TestCase):
    def test_restart_dedup_regression_backup(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'test.sqlite3'
            with Store(path) as store:
                self.assertEqual(store.observe('nms', 101, 5), 5)
                self.assertEqual(store.observe('nms', 101, 5), 0)
                self.assertEqual(store.observe('sunrise', 202, 2), 2)
            with Store(path) as store:
                self.assertEqual(store.totals(), {'nms': 5, 'sunrise': 2})
                self.assertEqual(store.observe('nms', 101, 6), 1)
                self.assertEqual(store.observe('nms', 102, 1), 1)
                with self.assertRaises(ValueError):
                    store.observe('nms', 101, 4)
                backup = store.backup()
                self.assertEqual(dict(query_database(backup, 'SELECT role,count FROM totals'))['nms'], 7)

    def test_future_schema_refused(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'future.sqlite3'
            with closing(sqlite3.connect(path)) as connection:
                with closing(connection.execute('PRAGMA user_version=900')):
                    pass
            with self.assertRaisesRegex(RuntimeError, 'Unsupported schema 900'):
                Store(path)
            self.assertEqual(query_database(path, 'PRAGMA user_version'), [(900,)])
            # Retain exception-independent proof of immediate Windows handle release.
            path.unlink()
            self.assertFalse(path.exists())

    def test_corruption_refused(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'broken.sqlite3'
            path.write_bytes(b'not a sqlite database')
            with self.assertRaises(sqlite3.DatabaseError):
                Store(path)
            path.unlink()
            self.assertFalse(path.exists())


class TransportTests(unittest.TestCase):
    def test_abi_and_invalid_or_stale_header(self):
        self.assertEqual((HEADER.size, STATE.size, COMMAND.size), (32, 32, 32))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'ipc'
            with Mapping(path) as mapping:
                self.assertIsNone(mapping.exchange('nms', 1, 1, True))
                HEADER.pack_into(mapping.memory, 0, MAGIC, VERSION, 1, max(0, ticks() - 3000))
                self.assertIsNone(mapping.exchange('nms', 1, 1, True))
                HEADER.pack_into(mapping.memory, 0, MAGIC, VERSION + 1, 1, ticks())
                self.assertIsNone(mapping.exchange('nms', 1, 1, True))
            path.unlink()
            self.assertFalse(path.exists())

    def test_real_core_with_explicit_fake_adapter_packets_and_restart(self):
        # The file-backed core now runs on both Windows and POSIX. No signal APIs.
        with tempfile.TemporaryDirectory(prefix='Frontier test ') as td, ExitStack() as resources:
            root = Path(td)
            mapping = resources.enter_context(Mapping(root / 'ipc'))
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'Core'))
            count = 0

            def cleanup_process(process):
                try:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=10)
                finally:
                    process.stderr.close()

            def start():
                nonlocal count
                count += 1
                stop_path = root / f'stop-{count}'
                process = subprocess.Popen(
                    [sys.executable, '-m', 'frontier.probe', '--database', str(root / 'save.sqlite3'),
                     '--test-file', str(root / 'ipc'), '--test-stop-file', str(stop_path)],
                    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                )
                resources.callback(cleanup_process, process)
                return process, stop_path

            def exchange_until(process, nseq, sseq):
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        self.fail(process.stderr.read().decode())
                    nms = mapping.exchange('nms', 101, nseq, True)
                    sunrise = mapping.exchange('sunrise', 202, sseq, True)
                    if nms and sunrise and nms[1:] == (sseq, True) and sunrise[1:] == (nseq, True):
                        return
                    time.sleep(.01)  # Bounded event polling, not file-handle cleanup retries.
                self.fail('Probe did not route fake test packets in both directions')

            def stop(process, stop_path):
                stop_path.touch()
                process.wait(timeout=10)
                self.assertEqual(process.returncode, 0, process.stderr.read().decode())

            process, marker = start()
            exchange_until(process, 3, 2)
            other, _ = start()
            other.wait(timeout=10)
            self.assertNotEqual(other.returncode, 0)
            stop(process, marker)
            self.assertIsNone(mapping.exchange('nms', 101, 3, True))
            process, marker = start()
            exchange_until(process, 3, 2)
            exchange_until(process, 4, 3)

            # Kill between core critical sections, avoiding an abandoned Windows
            # mutex. Abandonment refusal is tested separately in the lock unit tests.
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                with mapping.locked() as acquired:
                    if acquired:
                        process.kill()
                        process.wait(timeout=10)
                        # Deliberately age the heartbeat; no cleanup sleep/retry.
                        magic, version, epoch, _ = HEADER.unpack_from(mapping.memory)
                        HEADER.pack_into(mapping.memory, 0, magic, version, epoch, max(0, ticks() - 3000))
                        break
                time.sleep(.01)
            else:
                self.fail('Could not acquire test lock to stop the core safely')
            self.assertIsNone(mapping.exchange('nms', 101, 4, True))
            process, marker = start()
            exchange_until(process, 4, 3)
            stop(process, marker)
            self.assertEqual(dict(query_database(root / 'save.sqlite3', 'SELECT role,count FROM totals')), {'nms': 4, 'sunrise': 3})

            mapping.close()
            (root / 'ipc').unlink()
            (root / 'save.sqlite3').unlink()
