from . import *

from vee.manifest import Manifest
from vee.solve import *


class TestSolve(TestCase):

    def test_loads_provides(self):

        self.assertEqual(
            loads_provides('foo'),
            {'foo': None}
        )

        self.assertEqual(
            loads_provides('foo,bar'),
            {'foo': None, 'bar': None}
        )

        self.assertEqual(
            loads_provides('foo=1'),
            {'foo': Version('1')}
        )

        self.assertEqual(
            loads_provides('foo=bar'),
            {'foo': Version('bar')}
        )

        self.assertEqual(
            loads_provides('foo=1,bar=2'),
            {'foo': Version('1'), 'bar': Version('2')}
        )


    def test_loads_requires(self):

        self.assertEqual(
            loads_requires('foo'),
            {'foo': {}}
        )

        self.assertEqual(
            loads_requires('foo==1'),
            {'foo': {'version': VersionExpr('==1')}}
        )

        self.assertEqual(
            loads_requires('foo:version~=2'),
            {'foo': {'version': VersionExpr('~=2')}}
        )

        self.assertEqual(
            loads_requires('foo:bar'),
            {'foo': {'bar': None}}
        )

        self.assertEqual(
            loads_requires('foo;bar'),
            {'foo': {}, 'bar': {}}
        )

        self.assertEqual(
            loads_requires('foo:version>1,bar>=2;baz<=3'),
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

