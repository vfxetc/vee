from . import *


class TestRepos(TestCase):

    def test_only_one_default(self):
        for name in 'aaa', 'bbb', 'ccc':
            vee(['repo', '--add', '--default', 'count_defaults_' + name, 'git+git@github.com:example/veerepo'])
        vee(['repo', '--add', 'count_defaults_update', 'url'])
        vee(['repo', '--add', '--default', 'count_defaults_update'])

        defaults = 0
        for row in home.db.execute('SELECT is_default FROM repositories'):
            if row[0]:
                defaults += 1
        self.assertEqual(defaults, 1)
