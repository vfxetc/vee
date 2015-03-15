from . import *


class TestInstaller(TestCase):

    def test_basic_install(self):

        root = self.sandbox()
        os.makedirs(root)

        call([
            'python',
            os.path.abspath(os.path.join(__file__, '..', '..', 'install_vee.py')),
            '--prefix', root,
            '--yes',
            '--url', os.path.abspath(os.path.join(__file__, '..', '..')),
            '--no-bashrc',
        ])

        self.assertExists(os.path.join(root, 'src', 'bin', 'vee'))

