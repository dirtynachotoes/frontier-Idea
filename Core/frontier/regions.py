"""Owned byte regions using the established platform lock backend, no game hooks."""
from contextlib import ExitStack, contextmanager
import mmap
import os
from pathlib import Path
from .ipc import _IS_WINDOWS, _WindowsMutex, _PosixFileLock, _test_mutex_name

class Region:
    def __init__(self, name, size, test_file=None):
        self.size=size
        self.memory=None
        self.file=None
        self._closed=False
        self._resources=ExitStack()
        try:
            if test_file is None:
                if not _IS_WINDOWS: raise RuntimeError('Named runtime regions require Windows')
                self.lock=_WindowsMutex(name+'_mutex')
                self._resources.callback(self.lock.close)
                self.memory=mmap.mmap(-1,size,tagname=name)
            else:
                if _IS_WINDOWS:
                    self.lock=_WindowsMutex(_test_mutex_name(test_file))
                    self._resources.callback(self.lock.close)
                self.file=open(test_file,'a+b')
                self._resources.callback(self.file.close)
                if not _IS_WINDOWS:
                    self.lock=_PosixFileLock(self.file)
                with self.locked() as acquired:
                    if not acquired: raise RuntimeError('Test region busy during construction')
                    length=os.fstat(self.file.fileno()).st_size
                    if length==0: self.file.truncate(size); self.file.flush()
                    elif length!=size: raise ValueError('Test region size mismatch')
                self.memory=mmap.mmap(self.file.fileno(),size)
            self._resources.callback(self.memory.close)
        except BaseException:
            self.close()
            raise
    @contextmanager
    def locked(self):
        if self._closed: raise RuntimeError('Region closed')
        acquired=self.lock.try_acquire()
        try: yield acquired
        finally:
            if acquired: self.lock.release()
    def close(self):
        if not self._closed:
            self._closed=True
            self._resources.close()
    def __enter__(self): return self
    def __exit__(self,*args): self.close()
