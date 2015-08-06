from . import *


class TestInstaller(TestCase):

    def test_basic_install(self):

        # This currently doesn't work on Travis.
        if is_travis:
            return skip()

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

        vee = os.path.join(root, 'src', 'bin', 'vee')
        self.assertExists(vee)
        
        subprocess.check_call([vee, 'doctor'])
