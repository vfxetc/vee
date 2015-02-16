from . import *


class TestHttpManager(TestCase):

    def test_libfoo(self):
        vee('install', http('libfoo-1.0.0.tgz'), '--install-name', 'libfoo/1.0.0')
        self.assertTrue(os.path.exists(sandbox('installs/libfoo/1.0.0/libfoo.so')))

    def test_bar(self):
        vee('install', http('bar-1.0.0.tgz'), '--install-name', 'bar/1.0.0')
        self.assertTrue(os.path.exists(sandbox('installs/bar/1.0.0/bar')))

