import os
import hashlib
import tarfile


class HashingWriter(object):

    def __init__(self, fh, hasher=None):
        self._fh = fh
        self._hasher = hasher or hashlib.sha1()

    def write(self, data):
        self._fh.write(data)
        self._hasher.update(data)

    def hexdigest(self):
        return self._hasher.hexdigest()


fh = HashingWriter(open('test.tgz', 'wb'))
tar = tarfile.open(fileobj=fh, mode='w:gz')
tar.add(__file__, os.path.basename(__file__))
tar.close()

print fh.hexdigest()
