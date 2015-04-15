import os
import fcntl


class LockError(RuntimeError):
    pass


class Lockfile(object):

    def __init__(self, path):
        self._path = path
        self._fd = None
        self._locked = False

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self._path)

    def __del__(self):
        if self._locked:
            self.release()
        if self._fd:
            os.close(self._fd)
            # We don't unlink here, because that could be a race condition.
            # If we really wanted to unlink, we would do it before we release
            # the lock.

    def fileno(self):
        if self._fd is None:
            self._fd = os.open(self._path, os.O_CREAT | os.O_WRONLY)
        return self._fd

    def acquire(self, blocking=True):
        if self._locked:
            raise LockError('already locked')
        fcntl.lockf(self.fileno(), fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        self._locked = True

    def release(self):
        if not self._locked:
            raise LockError('not locked')
        fcntl.lockf(self.fileno(), fcntl.LOCK_UN)
        self._locked = False

    def __enter__(self):
        self.acquire()

    def __exit__(self, *args):
        self.release()

