"""Protocol 1: Win32 named mapping/mutex or an explicit file-backed test mapping.

File-backed tests use the same Win32 mutex abstraction on Windows and flock on
POSIX. Neither test backend loads game hooks or accesses native game saves.
"""
import contextlib
import ctypes
import hashlib
import mmap
import os
import struct
import time
from functools import lru_cache

MAGIC = 0x52465444  # DTFR
VERSION = 1
SIZE = 192
NAME = 'Local\\DestinyFrontier_Probe_v1'
HEADER = struct.Struct('<IIQQ8x')
STATE = struct.Struct('<QQIIII')
COMMAND = struct.Struct('<II24x')
OFFSETS = {'nms': 32, 'sunrise': 64}
COMMANDS = {'nms': 96, 'sunrise': 128}
_IS_WINDOWS = os.name == 'nt'
HEARTBEAT_TIMEOUT_MS = 2000  # Existing protocol-1 threshold, unchanged.


@lru_cache(maxsize=1)
def _kernel32():
    """Configure handle-sized arguments/results once, including BOOL results."""
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
    kernel.ReleaseMutex.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.GetTickCount64.argtypes = []
    kernel.GetTickCount64.restype = ctypes.c_uint64
    return kernel


def _windows_error():
    return ctypes.WinError(ctypes.get_last_error())


def ticks():
    if _IS_WINDOWS:
        return _kernel32().GetTickCount64()
    return time.monotonic_ns() // 1_000_000


class _WindowsMutex:
    """Zero-wait mutex. API injection allows status/cleanup tests off Windows."""
    def __init__(self, name, api=None, error_factory=None):
        self.api = api if api is not None else _kernel32()
        self.error_factory = error_factory or _windows_error
        self.handle = self.api.CreateMutexW(None, False, name)
        if not self.handle:
            raise self.error_factory()

    def try_acquire(self):
        if self.handle is None:
            raise RuntimeError('Mutex is closed')
        status = self.api.WaitForSingleObject(self.handle, 0)
        if status == 0:  # WAIT_OBJECT_0
            return True
        if status == 0x102:  # WAIT_TIMEOUT
            return False
        if status == 0x80:  # WAIT_ABANDONED also grants ownership to this thread
            self.release()
            raise RuntimeError('Abandoned IPC mutex: stop and restart the probe')
        if status == 0xFFFFFFFF:  # WAIT_FAILED
            raise self.error_factory()
        raise RuntimeError(f'Unexpected mutex wait status: {status}')

    def release(self):
        if not self.api.ReleaseMutex(self.handle):
            raise self.error_factory()

    def close(self):
        if self.handle is not None:
            if not self.api.CloseHandle(self.handle):
                raise self.error_factory()
            self.handle = None


class _PosixFileLock:
    def __init__(self, file):
        import fcntl  # Imported only for a POSIX file-backed mapping.
        self.file = file
        self.api = fcntl

    def try_acquire(self):
        try:
            self.api.flock(self.file.fileno(), self.api.LOCK_EX | self.api.LOCK_NB)
            return True
        except BlockingIOError:
            return False  # Expected zero-wait contention, not a cleanup failure.

    def release(self):
        self.api.flock(self.file.fileno(), self.api.LOCK_UN)

    def close(self):
        # No extra handle: Mapping owns the file, and locked() owns each acquisition.
        return None


def _test_mutex_name(path):
    canonical = os.path.normcase(os.path.realpath(os.fspath(path)))
    digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    return 'Local\\DestinyFrontier_Probe_Test_' + digest + '_mutex'


class Mapping:
    def __init__(self, test_file=None):
        self.file = None
        self.memory = None
        self._lock = None
        self._resources = contextlib.ExitStack()
        self._lock_active = False
        self._closed = False
        self._live_cache = {}
        self.last_exchange = {}
        try:
            if test_file is None:
                if not _IS_WINDOWS:
                    raise RuntimeError('Real runtime mapping requires Windows; use --test-file only for IPC tests')
                self._lock = _WindowsMutex(NAME + '_mutex')
                self._resources.callback(self._lock.close)
                self.memory = mmap.mmap(-1, SIZE, tagname=NAME)
                self._resources.callback(self.memory.close)
            else:
                # File-backed tests use a separate namespace; never the game mapping.
                if _IS_WINDOWS:
                    self._lock = _WindowsMutex(_test_mutex_name(test_file))
                    self._resources.callback(self._lock.close)
                self.file = open(test_file, 'a+b')
                self._resources.callback(self.file.close)
                if not _IS_WINDOWS:
                    self._lock = _PosixFileLock(self.file)
                    self._resources.callback(self._lock.close)
                # Never truncate an already mapped file, even to its existing size.
                # SetEndOfFile may fail on Windows while another view exists.
                if os.fstat(self.file.fileno()).st_size != SIZE:
                    with self.locked() as acquired:
                        if not acquired:
                            raise RuntimeError('IPC test file is busy during initialization')
                        length = os.fstat(self.file.fileno()).st_size
                        if length == 0:
                            self.file.truncate(SIZE)
                            self.file.flush()
                        elif length != SIZE:
                            raise ValueError(f'IPC test file has size {length}; expected {SIZE}')
                self.memory = mmap.mmap(self.file.fileno(), SIZE)
                self._resources.callback(self.memory.close)
        except BaseException:
            self.close()  # ExitStack releases every acquired resource before re-raising.
            raise

    def __enter__(self):
        if self._closed:
            raise RuntimeError('Mapping is closed')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    @contextlib.contextmanager
    def locked(self):
        if self._closed:
            raise RuntimeError('Mapping is closed')
        if self._lock_active:
            raise RuntimeError('Nested locking on one Mapping is unsupported')
        acquired = self._lock.try_acquire()
        self._lock_active = True
        try:
            yield acquired
        finally:
            try:
                if acquired:
                    self._lock.release()
            finally:
                self._lock_active = False

    def _diagnostic(self, status, now, core_heartbeat=None, peer_heartbeat=None):
        self.last_exchange = dict(
            status=status,
            core_age_ms=None if core_heartbeat is None else now - core_heartbeat,
            peer_age_ms=None if peer_heartbeat is None else now - peer_heartbeat,
        )

    def exchange(self, role, incarnation, seq, ready, ack=0, detail=0):
        # A missed lock is an unknown sample, not evidence of peer loss. Hold
        # only the last validated effect, bounded by the ORIGINAL timestamps.
        # Never refresh a deadline from a failed poll or cached response.
        key = (role, incarnation)
        peer = {'nms': 'sunrise', 'sunrise': 'nms'}[role]
        with self.locked() as acquired:
            now = ticks()
            if not acquired:
                cached = self._live_cache.get(key)
                if cached is not None:
                    response, core_heartbeat, peer_heartbeat = cached
                    valid = (ready and 0 <= now - core_heartbeat <= HEARTBEAT_TIMEOUT_MS
                             and 0 <= now - peer_heartbeat < HEARTBEAT_TIMEOUT_MS)
                    self._diagnostic('busy_cached' if valid else 'busy_expired', now,
                                     core_heartbeat, peer_heartbeat)
                    if valid:
                        return response
                    self._live_cache.pop(key, None)
                else:
                    self._diagnostic('busy_no_cache', now)
                return None
            magic, version, epoch, heartbeat = HEADER.unpack_from(self.memory)
            if (magic, version) != (MAGIC, VERSION) or not epoch:
                self._live_cache.clear()
                self._diagnostic('core_invalid', now, heartbeat)
                return None
            if not 0 <= now - heartbeat <= HEARTBEAT_TIMEOUT_MS:
                self._live_cache.clear()
                self._diagnostic('core_stale', now, heartbeat)
                return None
            STATE.pack_into(self.memory, OFFSETS[role], now, incarnation, seq, int(ready), ack, detail)
            target, live = COMMAND.unpack_from(self.memory, COMMANDS[role])
            if target > 999 or live > 1:
                self._live_cache.clear()
                raise RuntimeError('Invalid command payload')
            peer_heartbeat, peer_incarnation, _, peer_ready, _, _ = STATE.unpack_from(self.memory, OFFSETS[peer])
            peer_fresh = 0 <= now - peer_heartbeat < HEARTBEAT_TIMEOUT_MS
            effective_live = bool(live and ready and peer_incarnation and peer_ready == 1 and peer_fresh)
            response = epoch, target, effective_live
            if effective_live:
                self._live_cache[key] = response, heartbeat, peer_heartbeat
                status = 'live'
            else:
                self._live_cache.pop(key, None)
                status = ('local_not_ready' if not ready else
                          'peer_not_ready' if not peer_incarnation or peer_ready != 1 else
                          'peer_stale' if not peer_fresh else 'command_not_live')
            self._diagnostic(status, now, heartbeat, peer_heartbeat)
            return response

    def close(self):
        if self._closed:
            return
        if self._lock_active:
            raise RuntimeError('Cannot close a Mapping inside its lock context')
        self._closed = True
        # Reverse order closes mmap before its backing file; all callbacks run
        # even if another callback raises. Cleanup errors are never suppressed.
        self._resources.close()
