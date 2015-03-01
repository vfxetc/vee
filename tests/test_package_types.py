from . import *


class TestPackageTypes(TestCase):

    def assert_echo_installs(self, name, package):
        pkg = MockPackage(name, 'c_configure_make_install')
        pkg.render_commit()
        vee(['install', package, '--install-name', '%s/1.0.0' % name, '--make-install',])
        exe = sandbox('vee/installs/%s/1.0.0/bin/%s' % (name, name))
        self.assertTrue(os.path.exists(exe))
        self.assertEqual(subprocess.check_output([exe]).strip(), '%s:1' % name)

    def test_http(self):
        self.assert_echo_installs('type_http', mock_url('packages/type_http.tgz'))

    def test_file(self):
        self.assert_echo_installs('type_file', sandbox('packages/type_file'))

    def test_git(self):
        self.assert_echo_installs('type_git', 'git+' + sandbox('packages/type_git'))

