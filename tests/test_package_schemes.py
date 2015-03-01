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
        # TODO: arbitrary data.
        # TODO: both scripts and console_scripts entrypoints.

    def test_py_bdist(self):
        pkg = MockPackage('scheme_py_egg', 'py_bdist')
        pkg.render_commit()
        vee(['install', sandbox('packages/scheme_py_egg'), '--install-name', 'scheme_py_egg/1.0.0'])
        self.assertExists(sandbox('vee/installs/scheme_py_egg/1.0.0/lib/python2.7/site-packages/scheme_py_egg/__init__.py'))
        # TODO: arbitrary data.
        # TODO: scripts and console_scripts entrypoints.
        # self.assertExists(sandbox('vee/installs/scheme_py_egg/1.0.0/bin/scheme_py_egg'))
        # self.assertExists(sandbox('vee/installs/scheme_py_egg/1.0.0/bin/scheme_py_egg-ep'))

    def test_py_wheel(self):
        pkg = MockPackage('scheme_py_whl', 'py_wheel')
        pkg.render_commit()
        vee(['install', sandbox('packages/scheme_py_whl'), '--install-name', 'scheme_py_whl/1.0.0'])
        self.assertExists(sandbox('vee/installs/scheme_py_whl/1.0.0/lib/python2.7/site-packages/scheme_py_whl/__init__.py'))
        # TODO: arbitrary data.
        # TODO: scripts and console_scripts entrypoints:
        # self.assertExists(sandbox('vee/installs/scheme_py_whl/1.0.0/bin/scheme_py_whl'))
        # self.assertExists(sandbox('vee/installs/scheme_py_whl/1.0.0/bin/scheme_py_whl-ep'))
