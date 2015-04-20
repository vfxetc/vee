from . import *

from vee.requirements import Requirements
from vee.packageset import PackageSet

class TestPackageSets(TestCase):

    def test_prefix_function(self):

        home = self.home()

        reqs = Requirements()
        reqs.parse_file('''

            first --revision 1.0
            second -e "FIRST=$(prefix first)"

        '''.strip().splitlines())

        pkgs = PackageSet(home=home)
        pkgs.resolve_set(reqs)

        first = pkgs['first']
        first.install_path = '/path/to/first'

        second = pkgs['second']
        env = second.fresh_environ()

        self.assertEqual(env['FIRST'], '/path/to/first')
