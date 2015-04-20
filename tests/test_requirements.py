from . import *

from vee.requirements import Requirements


class TestRequirements(TestCase):

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

    def test_local_envvars(self):
        reqs = Requirements()
        reqs.parse_file('''
            url -e KEY=VALUE
        '''.strip().splitlines())

        flat = ''.join(reqs.iter_dump()).strip()
        self.assertEqual(flat, 'file:url --environ=KEY=VALUE')

    def test_elif(self):
        reqs = Requirements()
        reqs.parse_file('''
            % if 0:
                zero
            % elif 1:
                one
            % else:
                two
            % endif
        '''.strip().splitlines())
        pkgs = list(reqs.iter_packages())
        self.assertEqual(len(pkgs), 1)
        self.assertEqual(pkgs[0].name, 'one')

    def test_else(self):
        reqs = Requirements()
        reqs.parse_file('''
            % if 0:
                zero
            % elif 0:
                one
            % else:
                two
            % endif
        '''.strip().splitlines())
        pkgs = list(reqs.iter_packages())
        self.assertEqual(len(pkgs), 1)
        self.assertEqual(pkgs[0].name, 'two')

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
