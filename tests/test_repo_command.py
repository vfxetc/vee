from . import *


class TestRepos(TestCase):

    def test_only_one_default(self):

        home = self.home()

        mock_repo = self.repo()
        mock_repo.add_requirements('dummy-requirement')

        def defaults():
            defaults = []
            for row in home.db.execute('SELECT name, is_default FROM repositories'):
                if row[1]:
                    defaults.append(row[0])
            return defaults

        # After every step below, we should only have one default repo.

        # Add several defaults.
        for name in 'ABC':
            home.main(['repo', 'clone', '--default', mock_repo.path, name])
        self.assertEqual(defaults(), ['C'])

        # Add a non-default.
        home.main(['repo', 'clone', mock_repo.path, 'D'])
        # self.assertEqual(defaults(), ['C'])

        # Add a new default.
        home.main(['repo', 'clone', '--default', mock_repo.path, 'E'])
        self.assertEqual(defaults(), ['E'])

        # Set another to be default.
        home.main(['repo', 'set', '--default', 'B'])
        self.assertEqual(defaults(), ['B'])

    def test_single_repo_is_default(self):

        home = self.home()

        # Make a generic repo.
        repo = home.create_repo(is_default=False)

        # There is only the one.
        self.assertEqual(len(list(home.iter_repos())), 1)

        # It is also the default.
        repo2 = home.get_repo()
        self.assertTrue(repo2 is not None)
        self.assertEqual(repo.name, repo2.name)

