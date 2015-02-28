from . import *


class TestHttpManager(TestCase):

    def test_standalone_c(self):
        pkg = MockPackage('test_standalone_c', 'c_echo', {'NAME': 'foo'})
        pkg.render_commit()
        vee(['install', mock_url('packages/test_standalone_c.tgz'),
            '--install-name', 'foo/1.0.0',
            '--make-install',
        ])
        self.assertTrue(os.path.exists(sandbox('vee/installs/foo/1.0.0/bin/foo')))

    def test_foobar_step1_lib(self):
        pkg = MockPackage('test_foobar_step1_lib', 'c_libecho', {'NAME': 'bar'})
        pkg.render_commit()
        vee(['install', mock_url('packages/test_foobar_step1_lib.tgz'),
            '--install-name', 'libbar/1.0.0',
            '--make-install',
        ])
        self.assertTrue(os.path.exists(sandbox('vee/installs/libbar/1.0.0/lib/libbar.so')))

    def test_foobar_step2_bin(self):
        pkg = MockPackage('test_foobar_step2_bin', 'c_use_libecho', {'NAME': 'baz', 'LIB': 'bar'})
        pkg.render_commit()
        vee(['install', mock_url('packages/test_foobar_step2_bin.tgz'),
            '--install-name', 'baz/1.0.0',
            '--make-install',
            '--environ', 'CFLAGS=-I$VEE/installs/libbar/1.0.0/include,LDFLAGS=-L$VEE/installs/libbar/1.0.0/lib -rpath $VEE/installs/libbar/1.0.0/lib',
        ])
        self.assertTrue(os.path.exists(sandbox('vee/installs/baz/1.0.0/bin/baz')))


