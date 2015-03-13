from . import *


class TestWorkflows(TestCase):

    def test_dev_existing_package(self):
        """We will start with an existing package in an existing repo, develop
        against it, commit it, push, and redeploy."""

        test_utils = MockPackage('tdep_test_utils', 'test_utils')
        test_utils.render_commit()

        pkg_origin = MockPackage('tdep_pkg', 'python_source')
        pkg_origin.render_commit()
        pkg_origin.repo.git('config', 'receive.denyCurrentBranch', 'ignore')

        env_repo = MockRepo('tdep_repo')
        env_repo.add_requirements('''
            %s
            %s
        ''' % (pkg_origin.git_url, test_utils.git_url))
        env_repo.repo.git('config', 'receive.denyCurrentBranch', 'ignore')

        vee(['repo', 'clone', env_repo.path, env_repo.name])
        vee(['update', '--repo', env_repo.name])
        vee(['upgrade', '--repo', env_repo.name])

        path = vee(['exec', '--repo', env_repo.name, 'whichpy', pkg_origin.name], stdout=True).strip()
        self.assertEqual(path, sandbox('vee/environments/tdep_repo/master/lib/python2.7/site-packages/tdep_pkg'))

        vee(['dev', 'install', '--repo', env_repo.name, pkg_origin.name])
        self.assertExists(sandbox('vee/dev/tdep_pkg/tdep_pkg/__init__.py'))

        pkg_dev = pkg_origin.clone(sandbox('vee/dev/tdep_pkg'))
        pkg_dev.render_commit()

        status = vee(['status', '--repo', env_repo.name], stdout=True)
        self.assertIn('tdep_pkg is ahead of origin/master', status)

        vee(['add', '--repo', env_repo.name, pkg_dev.name])
        pkg_dev.repo.git('push', 'origin', 'master')

        status = vee(['status', '--repo', env_repo.name], stdout=True)
        self.assertNotIn('tdep_pkg is ahead of origin/master', status)
        self.assertIn('--name=tdep_pkg --revision=%s' % pkg_dev.repo.head[:8], status)

        vee(['commit', '--repo', env_repo.name, '--minor', '-m', 'testing'])
        vee(['push', '--repo', env_repo.name])

        vee(['update', '--repo', env_repo.name])
        vee(['upgrade', '--repo', env_repo.name])


