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

    def test_basic_update_upgrade(self):

        repo = MockRepo('tr_basics')
        vee(['repo', '--add', repo.name, repo.path])

        foo_pkg = MockPackage('tr_basics_foo', 'c_configure_make_install')
        foo_pkg.render_commit()

        repo.add_requirements('packages/tr_basics_foo --install-name tr_basics_foo/1.0.0 --make-install')

        vee(['update', repo.name])
        vee(['upgrade', repo.name])

        commit = repo.rev_list()[0][:8]
        self.assertExists(os.path.join(VEE, 'installs/tr_basics_foo/1.0.0/bin/tr_basics_foo'))
        self.assertExists(os.path.join(VEE, 'environments', repo.name, 'origin/master/bin/tr_basics_foo'))
        self.assertExists(os.path.join(VEE, 'environments', repo.name, 'commits', commit, 'bin/tr_basics_foo'))

        bar_pkg = MockPackage('tr_basics_bar', 'c_configure_make_install')
        bar_pkg.render_commit()

        repo.add_requirements('packages/tr_basics_bar --install-name tr_basics_bar/1.0.0 --make-install')

        vee(['update', repo.name])
        vee(['upgrade', repo.name])

        commit = repo.rev_list()[0][:8]
        self.assertExists(os.path.join(VEE, 'installs/tr_basics_foo/1.0.0/bin/tr_basics_foo'))
        self.assertExists(os.path.join(VEE, 'environments', repo.name, 'origin/master/bin/tr_basics_foo'))
        self.assertExists(os.path.join(VEE, 'environments', repo.name, 'commits', commit, 'bin/tr_basics_foo'))
        self.assertExists(os.path.join(VEE, 'installs/tr_basics_bar/1.0.0/bin/tr_basics_bar'))
        self.assertExists(os.path.join(VEE, 'environments', repo.name, 'origin/master/bin/tr_basics_bar'))
        self.assertExists(os.path.join(VEE, 'environments', repo.name, 'commits', commit, 'bin/tr_basics_bar'))

