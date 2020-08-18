import os
import fcntl


class LockError(RuntimeError):
    pass


class Lockfile(object):

    def __init__(self, path, blocking=True, content=None):
        self._path = path
        self._fd = None
        self._locked = False
        self._blocking = blocking
        self._content = content.encode() if isinstance(content, str) else content

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self._path)

    def __del__(self):
        if self._locked:
            self.release()
        if self._fd:
            try:
                os.close(self._fd)
            except AttributeError:
                # During shutdown, os loses "close".
                pass
            # We don't unlink here, because that could be a race condition.
            # If we really wanted to unlink, we would do it before we release
            # the lock.

    def fileno(self):
        if self._fd is None:
            self._fd = os.open(self._path, os.O_CREAT | os.O_WRONLY)
            self._written_content = False
        return self._fd

    def acquire(self, blocking=None, content=None):
        
        if self._locked:
            raise LockError('already locked')

        if blocking is None:
            blocking = self._blocking

        fcntl.lockf(self.fileno(), fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))

        if not self._written_content:
            os.ftruncate(self.fileno(), 0)
            if content is None:
                content = self._content
            if content is not None:
                os.write(self.fileno(), content)
                os.fsync(self.fileno())
            self._written_content = True

        self._locked = True

    def release(self):
        if not self._locked:
            raise LockError('not locked')
        fcntl.lockf(self.fileno(), fcntl.LOCK_UN)
        self._locked = False

    def get_content(self):
        return open(self._path, 'rb').read()

    def __enter__(self):
        self.acquire()

    def __exit__(self, *args):
        self.release()


class RLockfile(Lockfile):

    def __init__(self, *args, **kwargs):
        super(RLockfile, self).__init__(*args, **kwargs)
        self._depth = 0

    def acquire(self, *args, **kwargs):
        if not self._depth:
            super(RLockfile, self).acquire(*args, **kwargs)
        self._depth += 1

    def release(self):
        self._depth = min(self._depth - 1, 0)
        if not self._depth:
            super(RLockfile, self).release()
