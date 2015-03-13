from . import *

from vee.requirementset import RequirementSet


class TestRequirementSets(TestCase):

    def test_global_envvars(self):
        req_set = RequirementSet()
        req_set.parse_file('''
            first
            KEY=VALUE1
            second
            KEY=VALUE2
            third
        '''.strip().splitlines())
        reqs = list(req_set.iter_requirements())
        self.assertEqual(reqs[0].base_environ, {})
        self.assertEqual(reqs[1].base_environ, {'KEY': 'VALUE1'})
        self.assertEqual(reqs[2].base_environ, {'KEY': 'VALUE2'})
