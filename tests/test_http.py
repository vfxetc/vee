from . import *


class TestHttpManager(TestCase):

    def test_standalone_c(self):
        pkg = MockPackage('test_standalone_c', 'c_configure_make_install', {'NAME': 'foo'})
        pkg.render_commit()
        vee(['install', mock_url('packages/test_standalone_c.tgz'),
            '--install-name', 'foo/1.0.0',
            '--make-install',
        ])
        self.assertTrue(os.path.exists(sandbox('vee/installs/foo/1.0.0/bin/foo')))

    def test_standalone_python(self):
        pkg = MockPackage('test_standalone_python', 'py_src', {'NAME': 'pyfoo'})
        pkg.render_commit()
        vee(['install', mock_url('packages/test_standalone_python.tgz'),
            '--install-name', 'pyfoo/1.0.0',
        ])
        self.assertTrue(os.path.exists(sandbox('vee/installs/pyfoo/1.0.0/bin/pyfoo')))
        self.assertTrue(os.path.exists(sandbox('vee/installs/pyfoo/1.0.0/bin/pyfoo-ep')))
        self.assertTrue(os.path.exists(sandbox('vee/installs/pyfoo/1.0.0/lib/python2.7/site-packages/pyfoo/__init__.py')))

    def test_foobar_step1_lib(self):
        pkg = MockPackage('test_foobar_step1_lib', 'clib_configure_make_install', {'NAME': 'bar'})
        pkg.render_commit()
        vee(['install', mock_url('packages/test_foobar_step1_lib.tgz'),
            '--install-name', 'libbar/1.0.0',
            '--make-install',
        ])
        self.assertTrue(os.path.exists(sandbox('vee/installs/libbar/1.0.0/lib/libbar.so')))

    def test_foobar_step2_bin(self):
        pkg = MockPackage('test_foobar_step2_bin', 'c_use_clib_configure_make_install', {'NAME': 'baz', 'LIB': 'bar'})
        pkg.render_commit()
        vee(['install', mock_url('packages/test_foobar_step2_bin.tgz'),
            '--install-name', 'baz/1.0.0',
            '--make-install',
            '--environ', 'CFLAGS=-I$VEE/installs/libbar/1.0.0/include,LDFLAGS=-L$VEE/installs/libbar/1.0.0/lib -rpath $VEE/installs/libbar/1.0.0/lib',
        ])
        self.assertTrue(os.path.exists(sandbox('vee/installs/baz/1.0.0/bin/baz')))


