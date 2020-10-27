from . import *


class TestUpdateCommand(TestCase):

    def test_basic_update_upgrade(self):

        repo = MockRepo('tr_basics')
        repo.add_requirements('packages/tr_basics_foo --install-name tr_basics_foo/1.0.0 --make-install')
        
        vee(['repo', 'clone', repo.path, repo.name])

        foo_pkg = MockPackage('tr_basics_foo', 'c_configure_make_install')
        foo_pkg.render_commit()


        vee(['update', '--repo', repo.name])
        vee(['upgrade', '--repo', repo.name])

        commit = repo.rev_list()[0][:8]
        self.assertExists(os.path.join(VEE, 'installs/tr_basics_foo/1.0.0/bin/tr_basics_foo'))
        self.assertExists(os.path.join(VEE, 'environments', repo.name, default_branch, 'bin/tr_basics_foo'))
        self.assertExists(os.path.join(VEE, 'environments', repo.name, 'commits', commit, 'bin/tr_basics_foo'))

        bar_pkg = MockPackage('tr_basics_bar', 'c_configure_make_install')
        bar_pkg.render_commit()

        repo.add_requirements('packages/tr_basics_bar --install-name tr_basics_bar/1.0.0 --make-install')

        vee(['update', '--repo', repo.name])
        vee(['upgrade', '--repo', repo.name])

        commit = repo.rev_list()[0][:8]
        self.assertExists(os.path.join(VEE, 'installs/tr_basics_foo/1.0.0/bin/tr_basics_foo'))
        self.assertExists(os.path.join(VEE, 'environments', repo.name, default_branch, 'bin/tr_basics_foo'))
        self.assertExists(os.path.join(VEE, 'environments', repo.name, 'commits', commit, 'bin/tr_basics_foo'))
        self.assertExists(os.path.join(VEE, 'installs/tr_basics_bar/1.0.0/bin/tr_basics_bar'))
        self.assertExists(os.path.join(VEE, 'environments', repo.name, default_branch, 'bin/tr_basics_bar'))
        self.assertExists(os.path.join(VEE, 'environments', repo.name, 'commits', commit, 'bin/tr_basics_bar'))

