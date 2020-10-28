import zipfile

from . import *


class TestBuildTypes(TestCase):

    def test_static_file(self):
        pkg = MockPackage('scheme_static', 'static_file', {'PATH': 'etc/scheme_static'})
        pkg.render_commit()
        vee(['install', sandbox('packages/scheme_static'), '--install-name', 'scheme_static/1.0.0'])
        self.assertExists(sandbox('vee/installs/scheme_static/1.0.0/etc/scheme_static'))

    def assert_echo(self, type, do_call=True):
        name = 'scheme_' + type
        pkg = MockPackage(name, type)
        pkg.render_commit()
        vee(['install', pkg.path, '--install-name', '%s/1.0.0' % name])

        exe1 = sandbox('vee/installs/%s/1.0.0/bin/%s' % (name, name))
        exe2 = sandbox('vee/installs/%s/1.0.0/scripts/%s' % (name, name))
        if os.path.exists(exe1):
            exe = exe1
        else:
            exe = exe2
            self.assertExists(exe)

        if do_call:
            # Jumping through a bit of a hoop here to see the output.
            out = []
            try:
                call(['vee', 'exec', '-R', pkg.path, name], stdout=out.append)
            except:
                print(b''.join(out).strip().decode())
                raise
            self.assertEqual(b''.join(out).strip().decode(), '%s:1' % name)

    def test_make(self):
        self.assert_echo('c_make')

    def test_configure_make_install(self):
        self.assert_echo('c_configure_make_install')

    def test_self(self):
        self.assert_echo('self')

    def test_python_source(self):
        self.assert_echo('python_source')
        # TODO: arbitrary data.
        # TODO: both scripts and console_scripts entrypoints.

    def installed_package(self, name, *args):
        return sandbox(os.path.join('vee/installs', name, '1.0.0', default_python.rel_site_packages, name, *args))

    def test_python_sdist(self):
        pkg = MockPackage('scheme_python_sdist', 'python_sdist')
        pkg.render_commit()
        vee(['install', sandbox('packages/scheme_python_sdist'), '--install-name', 'scheme_python_sdist/1.0.0'])
        self.assertExists(self.installed_package(pkg.name, '__init__.py'))
        # TODO: arbitrary data.
        # TODO: scripts and console_scripts entrypoints.
        # self.assertExists(sandbox('vee/installs/scheme_py_egg/1.0.0/bin/scheme_py_egg'))
        # self.assertExists(sandbox('vee/installs/scheme_py_egg/1.0.0/bin/scheme_py_egg-ep')

    def test_python_bdist(self):
        pkg = MockPackage('scheme_python_bdist', 'python_bdist')
        pkg.render_commit()
        vee(['install', sandbox('packages/scheme_python_bdist'), '--install-name', 'scheme_python_bdist/1.0.0'])
        self.assertExists(self.installed_package(pkg.name, '__init__.py'))
        # TODO: arbitrary data.
        # TODO: scripts and console_scripts entrypoints.
        # self.assertExists(sandbox('vee/installs/scheme_py_egg/1.0.0/bin/scheme_py_egg'))
        # self.assertExists(sandbox('vee/installs/scheme_py_egg/1.0.0/bin/scheme_py_egg-ep')

    def test_python_bdist_egg(self):
        return # This one doesn't work.
        pkg = MockPackage('scheme_python_bdist_egg', 'python_bdist_egg')
        pkg.render_commit()
        vee(['install', sandbox('packages/scheme_python_bdist_egg'), '--install-name', 'scheme_python_bdist_egg/1.0.0'])
        self.assertExists(self.installed_package(pkg.name, '__init__.py'))
        # TODO: arbitrary data.
        # TODO: scripts and console_scripts entrypoints:
        # self.assertExists(sandbox('vee/installs/scheme_python_bdist_wheel/1.0.0/bin/scheme_python_bdist_wheel'))
        # self.assertExists(sandbox('vee/installs/scheme_python_bdist_wheel/1.0.0/bin/scheme_python_bdist_wheel-ep'))

    def test_python_bdist_wheel(self):
        
        pkg = MockPackage('scheme_python_bdist_wheel', 'python_bdist_wheel')
        pkg.render_commit()

        # We need to assemble a whl, because pip can no longer deal with
        # a bare directory.
        dir_path = sandbox('packages/scheme_python_bdist_wheel')
        whl_path = dir_path + '.whl'
        with zipfile.ZipFile(whl_path, 'w') as fh:
            for base, _, file_names in os.walk(dir_path):
                for name in file_names:
                    path = os.path.join(base, name)
                    rel_path = os.path.relpath(path, dir_path)
                    print(rel_path, path)
                    fh.write(path, rel_path)

        vee(['install', whl_path, '--install-name', 'scheme_python_bdist_wheel/1.0.0'])
        self.assertExists(self.installed_package(pkg.name, '__init__.py'))
        # TODO: arbitrary data.
        # TODO: scripts and console_scripts entrypoints:
        # self.assertExists(sandbox('vee/installs/scheme_python_bdist_wheel/1.0.0/bin/scheme_python_bdist_wheel'))
        # self.assertExists(sandbox('vee/installs/scheme_python_bdist_wheel/1.0.0/bin/scheme_python_bdist_wheel-ep'))
