from . import *

from vee.requirements import Requirements


class TestRequirementss(TestCase):

    def test_global_envvars(self):
        req_set = Requirements()
        req_set.parse_file('''
            first
            KEY=VALUE1
            second
            KEY=VALUE2
            third
        '''.strip().splitlines())
        reqs = list(req_set.iter_packages())
        self.assertEqual(reqs[0].base_environ, {})
        self.assertEqual(reqs[1].base_environ, {'KEY': 'VALUE1'})
        self.assertEqual(reqs[2].base_environ, {'KEY': 'VALUE2'})


    def test_platforms(self):
        req_set = Requirements()
        req_set.parse_file('''

            before
            % if MACOS:
                macos
            % elif LINUX:
                linux
            % endif
            after

        '''.strip().splitlines())

        print req_set

        reqs = list(req_set.iter_packages())
        self.assertEqual(reqs[0].name, 'before')
        if sys.platform == 'darwin':
            self.assertEqual(reqs[1].name, 'macos')
        elif sys.platform == 'linux2':
            self.assertEqual(reqs[1].name, 'linux')
        self.assertEqual(reqs[2].name, 'after')
