"""Canonical TEST observations only. Does not modify native saves."""
from contextlib import closing
from pathlib import Path
import sqlite3
import uuid


def _rows(connection, sql, parameters=()):
    """Own even short-lived SQLite cursors explicitly (including PRAGMAs)."""
    with closing(connection.execute(sql, parameters)) as cursor:
        return cursor.fetchall()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.db = None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.db = sqlite3.connect(self.path)
            if _rows(self.db, 'PRAGMA quick_check') != [('ok',)]:
                raise RuntimeError('Canonical database failed quick_check')
            version = _rows(self.db, 'PRAGMA user_version')[0][0]
            if version not in (0, 1):
                raise RuntimeError(f'Unsupported schema {version}')
            _rows(self.db, 'PRAGMA journal_mode=WAL')
            _rows(self.db, 'PRAGMA synchronous=FULL')
            with self.db:  # Transaction context, NOT connection ownership.
                _rows(self.db, 'CREATE TABLE IF NOT EXISTS observations(role TEXT, incarnation TEXT, seq INTEGER, PRIMARY KEY(role,incarnation))')
                _rows(self.db, 'CREATE TABLE IF NOT EXISTS totals(role TEXT PRIMARY KEY, count INTEGER NOT NULL)')
                _rows(self.db, 'PRAGMA user_version=1')
            self.backup()
        except BaseException:
            # A constructor that fails cannot be used in a caller's with block.
            # Close directly: do not try to back up an invalid/uninitialized DB.
            if self.db is not None:
                connection, self.db = self.db, None
                connection.close()
            raise

    def _connection(self):
        if self.db is None:
            raise RuntimeError('Store is closed')
        return self.db

    def __enter__(self):
        self._connection()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def observe(self, role, incarnation, seq):
        db = self._connection()
        if role not in ('nms', 'sunrise') or not 0 < incarnation < 2**64 or not 0 <= seq <= 1_000_000:
            raise ValueError('Invalid observation')
        with db:
            rows = _rows(db, 'SELECT seq FROM observations WHERE role=? AND incarnation=?', (role, str(incarnation)))
            previous = rows[0][0] if rows else 0
            if seq < previous:
                raise ValueError('Sequence regressed within same incarnation')
            if rows and seq == previous:
                return 0
            delta = seq - previous
            _rows(db, 'INSERT INTO observations VALUES(?,?,?) ON CONFLICT(role,incarnation) DO UPDATE SET seq=excluded.seq', (role, str(incarnation), seq))
            _rows(db, 'INSERT INTO totals VALUES(?,?) ON CONFLICT(role) DO UPDATE SET count=count+excluded.count', (role, delta))
        return delta

    def totals(self):
        return dict(_rows(self._connection(), 'SELECT role,count FROM totals'))

    def backup(self):
        db = self._connection()
        if db.in_transaction:
            raise RuntimeError('Cannot back up while a source transaction is active')
        directory = self.path.parent / 'Backups'
        directory.mkdir(exist_ok=True)
        target = directory / f'{self.path.stem}-{uuid.uuid4().hex}.sqlite3'
        temporary = target.with_suffix('.partial')
        try:
            # closing() releases the handle; `with sqlite3.connect()` alone does not.
            with closing(sqlite3.connect(temporary)) as destination:
                _rows(destination, 'PRAGMA synchronous=FULL')
                db.backup(destination)
                destination.commit()
                if _rows(destination, 'PRAGMA quick_check') != [('ok',)]:
                    raise RuntimeError('Backup database failed quick_check')
            # Same-directory promotion happens only AFTER all destination handles close.
            temporary.replace(target)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return target

    def close(self):
        if self.db is None:
            return
        try:
            self.backup()
        finally:
            # A failed closing backup still closes the source; its error propagates.
            connection, self.db = self.db, None
            connection.close()
