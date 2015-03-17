from . import *


class TestHomebrew(TestCase):

    def test_brew_1_install(self):

        home = self.class_home()
        home.main(['brew', 'install', 'sqlite'])

    def test_brew_2_link(self):

        home = self.class_home()
        home.main(['link', '-e', 'test', 'homebrew+sqlite'])

        self.assertExists(os.path.join(home.root, 'environments', 'test', 'bin', 'sqlite3'))
        
