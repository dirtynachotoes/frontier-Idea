"""Ownership regressions. Fake Win32 tests do not certify native Windows."""
from collections import deque
from contextlib import closing, ExitStack
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Core'))
from frontier.ipc import Mapping, _WindowsMutex
from frontier.store import Store


class StoreResourceTests(unittest.TestCase):
    def assert_closed(self, connection):
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute('SELECT 1')

    def test_future_constructor_closes_retained_connection(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'future.sqlite3'
            with closing(sqlite3.connect(path)) as seed:
                with closing(seed.execute('PRAGMA user_version=900')):
                    pass
            connections = []
            connect = sqlite3.connect
            def track(*args, **kwargs):
                connection = connect(*args, **kwargs)
                connections.append(connection)  # Keep alive: GC cannot mask missing close().
                return connection
            with patch('frontier.store.sqlite3.connect', side_effect=track):
                with self.assertRaisesRegex(RuntimeError, 'Unsupported schema'):
                    Store(path)
            self.assertEqual(len(connections), 1)
            self.assert_closed(connections[0])
            path.unlink()

    def test_constructor_initial_backup_failure_closes_source(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'test.sqlite3'
            connections = []
            connect = sqlite3.connect
            def track(*args, **kwargs):
                connection = connect(*args, **kwargs)
                connections.append(connection)
                return connection
            with patch('frontier.store.sqlite3.connect', side_effect=track), patch.object(Store, 'backup', side_effect=OSError('injected failure')):
                with self.assertRaisesRegex(OSError, 'injected failure'):
                    Store(path)
            self.assert_closed(connections[0])
            path.unlink()

    def test_idempotent_close_preserves_committed_state(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'test.sqlite3'
            with Store(path) as store:
                connection = store.db
                store.observe('nms', 11, 3)
                store.close()
                backups = list((path.parent / 'Backups').glob('*.sqlite3'))
                store.close()
                self.assertEqual(list((path.parent / 'Backups').glob('*.sqlite3')), backups)
                self.assert_closed(connection)
                with self.assertRaisesRegex(RuntimeError, 'Store is closed'):
                    store.totals()
            with Store(path) as reopened:
                self.assertEqual(reopened.totals(), {'nms': 3})
            path.unlink()

    def test_backup_destination_closed_before_promotion(self):
        with tempfile.TemporaryDirectory() as td, Store(Path(td) / 'test.sqlite3') as store:
            store.observe('sunrise', 7, 2)
            connect, replace = sqlite3.connect, Path.replace
            destinations = []
            def track(*args, **kwargs):
                connection = connect(*args, **kwargs)
                destinations.append(connection)
                return connection
            def promote(source, target):
                self.assert_closed(destinations[-1])
                return replace(source, target)
            with patch('frontier.store.sqlite3.connect', side_effect=track), patch.object(Path, 'replace', autospec=True, side_effect=promote):
                backup = store.backup()
            self.assertEqual(len(destinations), 1)
            self.assert_closed(destinations[0])
            self.assertFalse(list(backup.parent.glob('*.partial')))
            renamed = backup.with_name('renamed.sqlite3')
            backup.replace(renamed)
            with closing(sqlite3.connect(renamed)) as connection:
                with closing(connection.execute('SELECT role,count FROM totals')) as cursor:
                    self.assertEqual(dict(cursor.fetchall()), {'sunrise': 2})
            renamed.unlink()

    def test_promotion_failure_cleans_partial_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as td, Store(Path(td) / 'test.sqlite3') as store:
            store.observe('nms', 12, 4)
            with patch.object(Path, 'replace', side_effect=OSError('injected promotion failure')):
                with self.assertRaisesRegex(OSError, 'injected promotion failure'):
                    store.backup()
            self.assertFalse(list((store.path.parent / 'Backups').glob('*.partial')))
            self.assertEqual(store.totals(), {'nms': 4})

    def test_failed_close_backup_still_closes_source(self):
        with tempfile.TemporaryDirectory() as td, Store(Path(td) / 'test.sqlite3') as store:
            connection = store.db
            with patch.object(store, 'backup', side_effect=OSError('injected failure')):
                with self.assertRaisesRegex(OSError, 'injected failure'):
                    store.close()
            self.assert_closed(connection)
            store.close()
            store.path.unlink()

    def test_store_context_exception_releases_source(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'test.sqlite3'
            with self.assertRaisesRegex(ValueError, 'test exception'):
                with Store(path) as store:
                    connection = store.db
                    raise ValueError('test exception')
            self.assert_closed(connection)
            path.unlink()

    def test_active_transaction_backup_refused_without_hanging(self):
        with tempfile.TemporaryDirectory() as td, Store(Path(td) / 'test.sqlite3') as store:
            with closing(store.db.execute('INSERT INTO totals VALUES(?,?)', ('nms', 2))):
                pass
            try:
                with self.assertRaisesRegex(RuntimeError, 'transaction is active'):
                    store.backup()
            finally:
                store.db.rollback()


class MappingResourceTests(unittest.TestCase):
    def test_repeated_lock_release_and_exception(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'ipc'
            with Mapping(path) as mapping:
                for _ in range(10):
                    with mapping.locked() as acquired:
                        self.assertTrue(acquired)
                with self.assertRaisesRegex(ValueError, 'test exception'):
                    with mapping.locked() as acquired:
                        self.assertTrue(acquired)
                        raise ValueError('test exception')
                with mapping.locked() as acquired:
                    self.assertTrue(acquired)
                memory, file = mapping.memory, mapping.file
            self.assertTrue(memory.closed)
            self.assertTrue(file.closed)
            mapping.close()
            path.unlink()

    def test_two_views_never_retruncate_existing_mapping(self):
        with tempfile.TemporaryDirectory() as td, ExitStack() as resources:
            path = Path(td) / 'ipc'
            first = resources.enter_context(Mapping(path))
            first.memory[0:4] = b'test'
            second = resources.enter_context(Mapping(path))
            self.assertEqual(second.memory[0:4], b'test')
            second.memory[4:8] = b'data'
            self.assertEqual(first.memory[4:8], b'data')
            resources.close()
            path.unlink()

    def test_contending_thread_skips_then_acquires(self):
        with tempfile.TemporaryDirectory() as td, Mapping(Path(td) / 'ipc') as first, Mapping(Path(td) / 'ipc') as second:
            results, errors = [], []
            def attempt():
                try:
                    with second.locked() as acquired:
                        results.append(acquired)
                except BaseException as error:
                    errors.append(error)
            with first.locked() as acquired:
                self.assertTrue(acquired)
                thread = threading.Thread(target=attempt)
                thread.start()
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                self.assertEqual(results, [False])
            with second.locked() as acquired:
                self.assertTrue(acquired)

    def test_constructor_mmap_failure_closes_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'ipc'
            opened, original_open = [], open
            def track(*args, **kwargs):
                file = original_open(*args, **kwargs)
                opened.append(file)
                return file
            with patch('frontier.ipc.open', side_effect=track, create=True), patch('frontier.ipc.mmap.mmap', side_effect=OSError('injected mmap failure')):
                with self.assertRaisesRegex(OSError, 'injected mmap failure'):
                    Mapping(path)
            self.assertEqual(len(opened), 1)
            self.assertTrue(opened[0].closed)
            path.unlink()

    def test_invalid_file_size_refused_without_handle(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'ipc'
            path.write_bytes(b'invalid')
            with self.assertRaisesRegex(ValueError, 'expected 192'):
                Mapping(path)
            self.assertEqual(path.read_bytes(), b'invalid')
            path.unlink()

    def test_close_during_lock_refused_then_context_cleans_up(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'ipc'
            with Mapping(path) as mapping:
                with mapping.locked() as acquired:
                    self.assertTrue(acquired)
                    with self.assertRaisesRegex(RuntimeError, 'inside its lock context'):
                        mapping.close()
                with mapping.locked() as acquired:
                    self.assertTrue(acquired)
            with self.assertRaisesRegex(RuntimeError, 'Mapping is closed'):
                with mapping.locked():
                    self.fail('Closed mapping allowed locking')
            path.unlink()


class FakeWin32:
    """Status test double only; never a substitute for native kernel tests."""
    def __init__(self, statuses=(), create=0x123456789):
        self.statuses, self.create, self.calls = deque(statuses), create, []
        self.release_result = self.close_result = 1
    def CreateMutexW(self, security, owner, name):
        self.calls.append(('create', name))
        return self.create
    def WaitForSingleObject(self, handle, timeout):
        self.calls.append(('wait', handle, timeout))
        return self.statuses.popleft() if self.statuses else 0
    def ReleaseMutex(self, handle):
        self.calls.append(('release', handle))
        return self.release_result
    def CloseHandle(self, handle):
        self.calls.append(('close', handle))
        return self.close_result


def fake_error():
    return OSError('injected Win32 failure')


class WindowsLockAbstractionTests(unittest.TestCase):
    def test_acquire_timeout_release_idempotent_close(self):
        api = FakeWin32([0, 0x102, 0])
        mutex = _WindowsMutex('test', api=api, error_factory=fake_error)
        try:
            self.assertTrue(mutex.try_acquire())
            mutex.release()
            self.assertFalse(mutex.try_acquire())
            self.assertTrue(mutex.try_acquire())
            mutex.release()
        finally:
            mutex.close()
        mutex.close()
        self.assertEqual(len([c for c in api.calls if c[0] == 'release']), 2)
        self.assertEqual(len([c for c in api.calls if c[0] == 'close']), 1)
        with self.assertRaisesRegex(RuntimeError, 'Mutex is closed'):
            mutex.try_acquire()

    def test_abandoned_mutex_released_before_refusal(self):
        api = FakeWin32([0x80, 0])
        mutex = _WindowsMutex('test', api=api, error_factory=fake_error)
        try:
            with self.assertRaisesRegex(RuntimeError, 'Abandoned IPC mutex'):
                mutex.try_acquire()
            self.assertEqual(len([c for c in api.calls if c[0] == 'release']), 1)
            self.assertTrue(mutex.try_acquire())
            mutex.release()
        finally:
            mutex.close()

    def test_create_failure_reported(self):
        api = FakeWin32(create=0)
        with self.assertRaisesRegex(OSError, 'injected Win32 failure'):
            _WindowsMutex('test', api=api, error_factory=fake_error)
        self.assertFalse(any(c[0] == 'close' for c in api.calls))

    def test_wait_failure_reported_without_release(self):
        api = FakeWin32([0xFFFFFFFF])
        mutex = _WindowsMutex('test', api=api, error_factory=fake_error)
        try:
            with self.assertRaisesRegex(OSError, 'injected Win32 failure'):
                mutex.try_acquire()
            self.assertFalse(any(c[0] == 'release' for c in api.calls))
        finally:
            mutex.close()

    def test_release_and_close_errors_propagate(self):
        api = FakeWin32()
        mutex = _WindowsMutex('test', api=api, error_factory=fake_error)
        try:
            api.release_result = 0
            with self.assertRaisesRegex(OSError, 'injected Win32 failure'):
                mutex.release()
            api.close_result = 0
            with self.assertRaisesRegex(OSError, 'injected Win32 failure'):
                mutex.close()
            self.assertIsNotNone(mutex.handle)
        finally:
            api.close_result = 1
            mutex.close()

    def test_windows_file_backend_selects_mutex_abstraction(self):
        api, original_mutex = FakeWin32(), _WindowsMutex
        def create(name):
            return original_mutex(name, api=api, error_factory=fake_error)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'ipc'
            with patch('frontier.ipc._IS_WINDOWS', True), patch('frontier.ipc._WindowsMutex', side_effect=create), patch('frontier.ipc._PosixFileLock', side_effect=AssertionError('Windows selected POSIX lock')):
                with Mapping(path) as mapping:
                    with mapping.locked() as acquired:
                        self.assertTrue(acquired)
                    with self.assertRaisesRegex(ValueError, 'test exception'):
                        with mapping.locked():
                            raise ValueError('test exception')
                mapping.close()
            self.assertTrue(api.calls[0][1].startswith('Local\\DestinyFrontier_Probe_Test_'))
            self.assertEqual(len([c for c in api.calls if c[0] == 'close']), 1)
            path.unlink()

    def test_windows_named_mapping_failure_closes_mutex(self):
        api, original_mutex = FakeWin32(), _WindowsMutex
        with patch('frontier.ipc._IS_WINDOWS', True), patch('frontier.ipc._WindowsMutex', side_effect=lambda name: original_mutex(name, api=api, error_factory=fake_error)), patch('frontier.ipc.mmap.mmap', side_effect=OSError('injected map failure')):
            with self.assertRaisesRegex(OSError, 'injected map failure'):
                Mapping()
        self.assertEqual(len([c for c in api.calls if c[0] == 'close']), 1)


@unittest.skipUnless(os.name == 'nt', 'Requires native Windows kernel; mocked Win32 unit tests run on all platforms')
class NativeWindowsTests(unittest.TestCase):
    def test_named_mapping_views_and_close(self):
        name = 'Local\\DestinyFrontier_Probe_TEST_' + uuid.uuid4().hex
        with patch('frontier.ipc.NAME', name), Mapping() as first, Mapping() as second:
            first.memory[0:4] = b'test'
            self.assertEqual(second.memory[0:4], b'test')
            for _ in range(10):
                with first.locked() as acquired:
                    self.assertTrue(acquired)
            first.close()
            first.close()
            self.assertTrue(first.memory.closed)
            self.assertIsNone(first._lock.handle)
            self.assertEqual(second.memory[0:4], b'test')
        self.assertTrue(second.memory.closed)
        self.assertIsNone(second._lock.handle)

    def test_real_abandoned_mutex_released_and_refused(self):
        name = 'Local\\DestinyFrontier_Probe_TEST_' + uuid.uuid4().hex
        mutex = _WindowsMutex(name)
        try:
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'Core'))
            code = 'import os; from frontier.ipc import _WindowsMutex; m = _WindowsMutex(' + repr(name) + '); assert m.try_acquire(); os._exit(0)'
            completed = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr.decode())
            with self.assertRaisesRegex(RuntimeError, 'Abandoned IPC mutex'):
                mutex.try_acquire()
            acquired = mutex.try_acquire()
            try:
                self.assertTrue(acquired)
            finally:
                if acquired:
                    mutex.release()
        finally:
            mutex.close()
