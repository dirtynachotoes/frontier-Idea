"""Core ownership tests: no game processes or native hooks are used."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Core'))
from frontier import probe
from frontier.ipc import Mapping
from frontier.store import Store


class CoreLifecycleTests(unittest.TestCase):
    def check_closed(self, stores, mappings):
        for store, connection in stores:
            self.assertIsNone(store.db)
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute('SELECT 1')
        for mapping in mappings:
            self.assertTrue(mapping.memory.closed)
            self.assertTrue(mapping.file.closed)

    def scenario(self, failure):
        with tempfile.TemporaryDirectory(prefix='frontier lifecycle ') as td:
            root = Path(td)
            stores, mappings, logs = [], [], []
            def make_store(path):
                store = Store(path)
                stores.append((store, store.db))
                return store
            def make_mapping(path):
                if failure == 'mapping':
                    raise OSError('injected mapping failure')
                mapping = Mapping(path)
                mappings.append(mapping)
                return mapping
            original_open = open
            def make_log(*args, **kwargs):
                if failure == 'log':
                    raise OSError('injected log failure')
                log = original_open(*args, **kwargs)
                logs.append(log)
                return log
            stop = root / 'stop'
            stop.touch()
            with patch.object(probe, 'Store', side_effect=make_store), patch.object(probe, 'Mapping', side_effect=make_mapping), patch('frontier.probe.open', side_effect=make_log, create=True), redirect_stdout(io.StringIO()):
                if failure == 'reset':
                    with patch.object(probe, '_clear_owned_state', side_effect=OSError('injected reset failure')):
                        with self.assertRaisesRegex(OSError, 'injected reset failure'):
                            probe.run(root / 'state.sqlite3', root / 'ipc', stop)
                else:
                    with self.assertRaisesRegex(OSError, 'injected ' + failure + ' failure'):
                        probe.run(root / 'state.sqlite3', root / 'ipc', stop)
            self.check_closed(stores, mappings)
            self.assertTrue(all(log.closed for log in logs))
            (root / 'state.sqlite3').unlink()
            if mappings:
                (root / 'ipc').unlink()

    def test_mapping_constructor_failure_closes_store(self):
        self.scenario('mapping')

    def test_log_open_failure_closes_mapping_and_store(self):
        self.scenario('log')

    def test_shutdown_reset_failure_closes_all_resources(self):
        self.scenario('reset')

    def test_stop_marker_requires_isolated_backend(self):
        with self.assertRaisesRegex(ValueError, 'explicit file-backed'):
            probe.run('must-not-be-created.sqlite3', test_stop_file='stop')
