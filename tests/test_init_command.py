from . import *


class TestInitCommand(TestCase):


    def test_init_without_repo(self):

        home = self.home()

        home.main(['init'])

        # Should not have a repo.
        self.assertRaises(ValueError, home.get_repo)

    def test_init_with_repo(self):

        home = self.home()

        mock_package  = self.package('foo', 'c_configure_make_install')
        mock_package.render_commit()

        mock_repo = self.repo()
        mock_repo.add_requirements('%s --make-install' % mock_package.url)

        home.main(['init', mock_repo.path])

        # Should have a repo.
        repo = home.get_repo()

        # Lets install our package.
        home.main(['update'])
        home.main(['upgrade'])

        self.assertExists(home._abs_path('environments/primary/origin/master/bin/foo'))

