from . import *


class TestHttpManager(TestCase):

    def test_foobar_step1(self):
        vee(['install', asset_url('libfoo-1.0.0.tgz'),
            '--install-name', 'libfoo/1.0.0',
        ])
        self.assertTrue(os.path.exists(sandbox('installs/libfoo/1.0.0/lib/libfoo.so')))

    def test_foobar_step2(self):
        vee(['install', asset_url('bar-1.0.0.tgz'),
            '--install-name', 'bar/1.0.0',
            '--environ', 'CFLAGS=-I$VEE/installs/libfoo/1.0.0/include,LDFLAGS=-L$VEE/installs/libfoo/1.0.0/lib',
        ])
        self.assertTrue(os.path.exists(sandbox('installs/bar/1.0.0/bin/bar')))


