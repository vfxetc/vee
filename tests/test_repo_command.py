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
