from . import *


class TestRepos(TestCase):

    def test_only_one_default(self):

        home = self.home()

        def defaults():
            defaults = []
            for row in home.db.execute('SELECT name, is_default FROM repositories'):
                if row[1]:
                    defaults.append(row[0])
            return defaults

        # After every step below, we should only have one default repo.

        # Add several defaults.
        for name in 'ABC':
            home.main(['repo', '--add', '--default', name, 'url'])
        self.assertEqual(defaults(), ['C'])

        # Add a non-default.
        home.main(['repo', '--add', 'D', 'url'])
        self.assertEqual(defaults(), ['C'])

        # Add a new default.
        home.main(['repo', '--add', '--default', 'E', 'url'])
        self.assertEqual(defaults(), ['E'])

        # Set another to be default.
        home.main(['repo', '--set', '--default', 'B'])
        self.assertEqual(defaults(), ['B'])
