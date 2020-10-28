from . import *


class TestPackageTypes(TestCase):

    def assert_echo_installs(self, name, package):
        pkg = MockPackage(name, 'c_configure_make_install')
        pkg.render_commit()
        vee(['install', package, '--install-name', '%s/1.0.0' % name, '--make-install',])
        exe = sandbox('vee/installs/%s/1.0.0/bin/%s' % (name, name))
        self.assertTrue(os.path.exists(exe))
        self.assertEqual(subprocess.check_output([exe]).decode().strip(), '%s:1' % name)

    def test_http(self):
        self.assert_echo_installs('type_http', mock_url('packages/type_http.tgz'))

    def test_file(self):
        self.assert_echo_installs('type_file', sandbox('packages/type_file'))

    def test_git(self):
        self.assert_echo_installs('type_git', 'git+' + sandbox('packages/type_git'))

    def installed_package(self, name, *args):
        return sandbox('vee/installs', name, '1.0.0', default_python.rel_site_packages, name, *args)

    def test_pypi(self):

        pkg = MockPackage('tpt_pypi', 'python_sdist')
        pkg.render_commit()

        vee(['install', 'pypi:tpt_pypi', '--revision', '1.0.0'])
        self.assertExists(self.installed_package(pkg.name, '__init__.py'))

    def test_pypi_deps(self):

        pkg = MockPackage('tpt_pypi_depa', 'python_source')
        pkg.render_commit()

        pkg = MockPackage('tpt_pypi_depb', 'python_source', {'REQUIRES': 'tpt_pypi_depa'})
        pkg.render_commit()

        vee(['link', '-e', 'tpt_pypi_env', 'pypi:tpt_pypi_depb', '--revision', '1.0.0'])
        self.assertExists(self.installed_package('tpt_pypi_depb', '__init__.py'))
        self.assertExists(self.installed_package('tpt_pypi_depa', '__init__.py'))

