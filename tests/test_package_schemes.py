from . import *


class TestPackageSchemes(TestCase):

    def test_static_file(self):
        pkg = MockPackage('scheme_static', 'static_file', {'PATH': 'etc/scheme_static'})
        pkg.render_commit()
        vee(['install', sandbox('packages/scheme_static'), '--install-name', 'scheme_static/1.0.0'])
        self.assertExists(sandbox('vee/installs/scheme_static/1.0.0/etc/scheme_static'))

    def assert_echo(self, type, call=True):
        name = 'scheme_' + type
        pkg = MockPackage(name, type)
        pkg.render_commit()
        vee(['install', sandbox('packages/%s' % name), '--install-name', '%s/1.0.0' % name])
        exe = sandbox('vee/installs/%s/1.0.0/bin/%s' % (name, name))
        self.assertTrue(os.path.exists(exe))
        if call:
            self.assertEqual(subprocess.check_output([exe]).strip(), '%s:1' % name)

    def test_make(self):
        self.assert_echo('c_make')

    def test_configure_make_install(self):
        self.assert_echo('c_configure_make_install')

    def test_py_src(self):
        self.assert_echo('py_src', call=False)
