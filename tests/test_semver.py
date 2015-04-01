from . import *

from vee.semver import Version, VersionExpr


class TestVersions(TestCase):

    def test_release(self):

        v = Version('1.0.0')
        self.assertEqual(v.release, (1, 0, 0))
        self.assertEqual(str(v), '1.0.0')

        v = Version('0.5')
        self.assertEqual(v.release, (0, 5))
        self.assertEqual(str(v), '0.5')

    def test_pep_epoch(self):

        v = Version('1.0.0')
        self.assertEqual(v.epoch, 0)
        self.assertEqual(str(v), '1.0.0')

        v = Version('123!1.0.0')
        self.assertEqual(v.epoch, 123)
        self.assertEqual(str(v), '123!1.0.0')

    def test_pep_pre_release(self):

        v = Version('0.5b1')
        self.assertEqual(v.release, (0, 5))
        self.assertEqual(v.pep_pre_release, ('b', 1))
        self.assertEqual(str(v), '0.5b1')
        
        v = Version('0.5beta1')
        self.assertEqual(v.release, (0, 5))
        self.assertEqual(v.pep_pre_release, ('beta', 1))
        self.assertEqual(str(v), '0.5beta1')

        v = Version('0.5rc6')
        self.assertEqual(v.release, (0, 5))
        self.assertEqual(v.pep_pre_release, ('rc', 6))
        self.assertEqual(str(v), '0.5rc6')

    def test_pep_post_release(self):

        v = Version('1.2.3.post5')
        self.assertEqual(v.release, (1, 2, 3))
        self.assertEqual(v.post_release, ('post', 5))
        self.assertEqual(str(v), '1.2.3.post5')

    def test_pep_dev_release(self):

        v = Version('0.5.dev2')
        self.assertEqual(v.release, (0, 5))
        self.assertEqual(v.dev_release, ('dev', 2))
        self.assertEqual(str(v), '0.5.dev2')

    def test_sem_pre_release(self):

        v = Version('0.5-alpha')
        self.assertEqual(v.release, (0, 5))
        self.assertEqual(v.sem_pre_release, ('alpha', ))
        self.assertEqual(str(v), '0.5-alpha')

        v = Version('0.5-alpha.1')
        self.assertEqual(v.release, (0, 5))
        self.assertEqual(v.sem_pre_release, ('alpha', 1))
        self.assertEqual(str(v), '0.5-alpha.1')

    def test_build_metadata(self):

        v = Version('0.5-alpha+abcdef')
        self.assertEqual(v.release, (0, 5))
        self.assertEqual(v.build_metadata, ('abcdef', ))
        self.assertEqual(str(v), '0.5-alpha+abcdef')

        v = Version('0.5-alpha+abcdef.20150325')
        self.assertEqual(v.release, (0, 5))
        self.assertEqual(v.build_metadata, ('abcdef', 20150325))
        self.assertEqual(str(v), '0.5-alpha+abcdef.20150325')

    def test_unknown(self):

        v = Version('0.5@unknown')
        self.assertEqual(v.release, (0, 5))
        self.assertEqual(v.unknown, ('@unknown', ))

    def test_git_rev(self):

        v = Version('abcdef')
        self.assertEqual(v.release, None)
        self.assertEqual(v.unknown, ('abcdef', ))

    def test_comparisons(self):

        a = Version('1.0.0')
        b = Version('1.0.0')

        self.assertTrue(a == b)
        self.assertFalse(a != b)

        a = Version('1.0')
        b = Version('2.0')

        self.assertTrue(a != b)
        self.assertTrue(a <= b)
        self.assertTrue(a < b)
        self.assertFalse(a == b)
        self.assertFalse(a >= b)
        self.assertFalse(a > b)

        a = Version('1.0.0a')
        b = Version('1.0.0')

        self.assertTrue(a != b)
        self.assertTrue(a <= b)
        self.assertTrue(a < b)
        self.assertFalse(a == b)
        self.assertFalse(a >= b)
        self.assertFalse(a > b)

    def test_ordering(self):

        vs = [Version(x) for x in '''

            2.1.1
            1.0.0
            2.0.0
            2.1.0
            0.5.9
            0.5
            1
            2

            1.0.0a
            1.0.0a1
            1.0.0b
            1.0.0rc4
            1.0.0rc1
            1.0.0.dev1
            1.0.0.dev2
            1.0.0.post1

            1.0.0-alpha
            1.0.0-alpha.1
            1.0.0-alpha.beta
            1.0.0-beta
            1.0.0-beta.2
            1.0.0-beta.11
            1.0.0-rc.1

            1.0.0@unknown

        '''.strip().split()]
        vs = [str(v) for v in sorted(vs)]

        self.assertEqual(vs, '''
            0.5
            0.5.9
            1
            1.0.0a0
            1.0.0a1
            1.0.0b0
            1.0.0rc1
            1.0.0rc4
            1.0.0.dev1
            1.0.0.dev2
            1.0.0-alpha
            1.0.0-alpha.1
            1.0.0-alpha.beta
            1.0.0-beta
            1.0.0-beta.2
            1.0.0-beta.11
            1.0.0-rc.1
            1.0.0@unknown
            1.0.0
            1.0.0.post1
            2
            2.0.0
            2.1.0
            2.1.1
        '''.strip().split(), '\n'.join(vs))

    def test_noop_expr(self):
        expr = VersionExpr('1.0.0')
        self.assertTrue(expr.eval('1.0.0'))
        self.assertFalse(expr.eval('1.0.0a1'))
        self.assertFalse(expr.eval('2'))

    def test_eq_expr(self):
        expr = VersionExpr('== 1.0.0')
        self.assertTrue(expr.eval('1.0.0'))
        self.assertFalse(expr.eval('1.0.0a1'))
        self.assertFalse(expr.eval('2'))

    def test_ne_expr(self):
        expr = VersionExpr('!= 1.0.0')
        self.assertFalse(expr.eval('1.0.0'))
        self.assertTrue(expr.eval('1.0.0a1'))
        self.assertTrue(expr.eval('2'))

    def test_gt_expr(self):
        expr = VersionExpr('> 1.0.0')
        self.assertFalse(expr.eval('1.0.0'))
        self.assertFalse(expr.eval('1.0.0a1'))
        self.assertTrue(expr.eval('2'))

    def test_gte_expr(self):
        expr = VersionExpr('>= 1.0.0')
        self.assertTrue(expr.eval('1.0.0'))
        self.assertFalse(expr.eval('1.0.0a1'))
        self.assertTrue(expr.eval('2'))

    def test_lt_expr(self):
        expr = VersionExpr('< 1.0.0')
        self.assertFalse(expr.eval('1.0.0'))
        self.assertTrue(expr.eval('1.0.0a1'))
        self.assertFalse(expr.eval('2'))

    def test_lte_expr(self):
        expr = VersionExpr('<= 1.0.0')
        self.assertTrue(expr.eval('1.0.0'))
        self.assertTrue(expr.eval('1.0.0a1'))
        self.assertFalse(expr.eval('2'))

    def test_compatibility_expr(self):

        expr = VersionExpr('~= 1.0.0')
        self.assertTrue(expr.eval('1.0.0'))
        self.assertTrue(expr.eval('1.0.1'))
        self.assertFalse(expr.eval('1.0.0a1'))
        self.assertFalse(expr.eval('2.0.0'))


    def test_multiple_exprs(self):

        expr = VersionExpr('>= 1.0.0, < 2.0.0')
        self.assertTrue(expr.eval('1.0.0'))
        self.assertTrue(expr.eval('1.0.1'))
        self.assertFalse(expr.eval('2.0.0'))
        self.assertFalse(expr.eval('1.0.0a'))
        self.assertFalse(expr.eval('0.9.0'))






