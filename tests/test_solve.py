from . import *

from vee.manifest import Manifest
from vee.package.provides import Provision
from vee.package.requires import RequirementSet, Requirement
from vee.semver import Version, VersionExpr
from vee.solve import solve


class TestSolve(TestCase):

    def test_provides(self):

        self.assertEqual(
            Provision('foo'),
            {'foo': None}
        )

        self.assertEqual(
            Provision('foo,bar'),
            {'foo': None, 'bar': None}
        )

        self.assertEqual(
            Provision('foo=1'),
            {'foo': Version('1')}
        )

        self.assertEqual(
            Provision('foo=bar'),
            {'foo': Version('bar')}
        )

        self.assertEqual(
            Provision('foo=1,bar=2'),
            {'foo': Version('1'), 'bar': Version('2')}
        )


    def test_requires(self):

        self.assertEqual(
            RequirementSet('foo'),
            {'foo': {}}
        )

        self.assertEqual(
            RequirementSet('foo==1'),
            {'foo': {'version': VersionExpr('==1')}}
        )

        self.assertEqual(
            RequirementSet('foo:version~=2'),
            {'foo': {'version': VersionExpr('~=2')}}
        )

        self.assertEqual(
            RequirementSet('foo:bar'),
            {'foo': {'bar': None}}
        )

        self.assertEqual(
            RequirementSet('foo;bar'),
            {'foo': {}, 'bar': {}}
        )

        self.assertEqual(
            RequirementSet('foo:version>1,bar>=2;baz<=3'),
            {'foo': {'version': VersionExpr('>1'), 'bar': VersionExpr('>=2')}, 'baz': {'version': VersionExpr('<=3')}}
        )

    def test_satisfies(self):

        self.assertTrue(Provision('foo').satisfies(Requirement()))
        self.assertTrue(Provision('version=1').satisfies(Requirement('version=1')))
        self.assertFalse(Provision('version=1').satisfies(Requirement('version=2')))

        self.assertTrue(Provision('a=1,b=2').satisfies(Requirement('a=1')))
        self.assertTrue(Provision('a=1,b=2').satisfies(Requirement('a<2,b>1')))
        self.assertFalse(Provision('a=1,b=2').satisfies(Requirement('a<1,b>1')))

        self.assertTrue(Provision('version=2.7.3').satisfies(Requirement('version~=2.7')))
        self.assertFalse(Provision('version=2.7.3').satisfies(Requirement('version~=3.7')))


    def test_basics(self):

        manifest = Manifest()
        manifest.parse_args('a --requires b')
        manifest.parse_args('b')

        sol = solve('a', manifest)
        self.assertEqual(list(sol), ['a', 'b'])

        sol = solve('b', manifest)
        self.assertEqual(list(sol), ['b'])

        sol = solve('b;a', manifest)
        self.assertEqual(list(sol), ['b', 'a'])

    def test_simple_requirement(self):

        manifest = Manifest()
        manifest.parse_args('a --requires b>1')
        manifest.parse_args('b')

        b = manifest.get('b')
        b.provides['version'] = '2'

        sol = solve('a', manifest)
        self.assertEqual(list(sol), ['a', 'b'])

    def test_simple_bad_requirement(self):

        manifest = Manifest()
        manifest.parse_args('a --requires b>1')
        manifest.parse_args('b')

        b = manifest.get('b')
        b.provides['version'] = '1'

        sol = solve('a', manifest)
        self.assertIs(sol, None)

    def test_looped_requirement(self):

        manifest = Manifest()
        manifest.parse_args('a --requires b')
        manifest.parse_args('b --requires a')

        sol = solve('a', manifest)
        self.assertEqual(list(sol), ['a', 'b'])

        sol = solve('b', manifest)
        self.assertEqual(list(sol), ['b', 'a'])

    def test_diamond_requirement(self):

        manifest = Manifest()
        manifest.parse_args('a --requires b;c')
        manifest.parse_args('b --requires d')
        manifest.parse_args('c --requires d')
        manifest.parse_args('d')

        sol = solve('a', manifest)
        self.assertEqual(list(sol), ['a', 'b', 'c', 'd'])

        sol = solve('b', manifest)
        self.assertEqual(list(sol), ['b', 'd'])


