from . import *

from vee.manifest import Manifest
from vee.package.provides import Provides
from vee.package.requires import Requires
from vee.solve import *


class TestSolve(TestCase):

    def test_loads_provides(self):

        self.assertEqual(
            Provides('foo'),
            {'foo': None}
        )

        self.assertEqual(
            Provides('foo,bar'),
            {'foo': None, 'bar': None}
        )

        self.assertEqual(
            Provides('foo=1'),
            {'foo': Version('1')}
        )

        self.assertEqual(
            Provides('foo=bar'),
            {'foo': Version('bar')}
        )

        self.assertEqual(
            Provides('foo=1,bar=2'),
            {'foo': Version('1'), 'bar': Version('2')}
        )


    def test_Requires(self):

        self.assertEqual(
            Requires('foo'),
            {'foo': {}}
        )

        self.assertEqual(
            Requires('foo==1'),
            {'foo': {'version': VersionExpr('==1')}}
        )

        self.assertEqual(
            Requires('foo:version~=2'),
            {'foo': {'version': VersionExpr('~=2')}}
        )

        self.assertEqual(
            Requires('foo:bar'),
            {'foo': {'bar': None}}
        )

        self.assertEqual(
            Requires('foo;bar'),
            {'foo': {}, 'bar': {}}
        )

        self.assertEqual(
            Requires('foo:version>1,bar>=2;baz<=3'),
            {'foo': {'version': VersionExpr('>1'), 'bar': VersionExpr('>=2')}, 'baz': {'version': VersionExpr('<=3')}}
        )


    def test_basics(self):

        manifest = Manifest()
        manifest.parse_args('foo --name foo --requires bar')
        manifest.parse_args('bar')

        foo = manifest.get('foo')
        print(foo)
        foo = manifest.get('bar')
        print(foo)

        solve = solve_dependencies({'foo': {}}, manifest)

