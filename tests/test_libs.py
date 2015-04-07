from . import *

from vee import libs


class TestLibs(TestCase):

    def test_name_variants_libfoo_so(self):
        self.assertEqual(libs.name_variants('libfoo.so'), ['libfoo.so', 'libfoo.dylib', 'libfoo', 'foo.so', 'foo.dylib', 'foo'])

    def test_name_variants_libfoo_dylib(self):
        self.assertEqual(libs.name_variants('libfoo.dylib'), ['libfoo.dylib', 'libfoo.so', 'libfoo', 'foo.dylib', 'foo.so', 'foo'])

    def test_name_variants_libfoo_bare(self):
        self.assertEqual(libs.name_variants('foo'), ['foo', 'foo.dylib', 'foo.so', 'libfoo', 'libfoo.dylib', 'libfoo.so'])

    def test_name_variants_libfoo_so_1(self):
        self.assertEqual(libs.name_variants('libfoo.so.1'), [
            'libfoo.so.1',
            'libfoo.dylib.1',
            'libfoo.1',
            'foo.so.1',
            'foo.dylib.1',
            'foo.1',
            'libfoo.so',
            'libfoo.dylib',
            'libfoo',
            'foo.so',
            'foo.dylib',
            'foo'
    ])

    def test_name_variants_libfoo_1_2_so_1(self):
        self.assertEqual(libs.name_variants('libfoo.1.2.so'), [
            'libfoo.1.2.so',
            'libfoo.1.2.dylib',
            'libfoo.1.2',
            'libfoo.1.so',
            'libfoo.1.dylib',
            'libfoo.1',
            'libfoo.so',
            'libfoo.dylib',
            'libfoo',
            'foo.1.2.so',
            'foo.1.2.dylib',
            'foo.1.2',
            'foo.1.so',
            'foo.1.dylib',
            'foo.1',
            'foo.so',
            'foo.dylib',
            'foo'
    ])


    def test_name_variants_libfoo_1_2_so_1_version_only(self):
        self.assertEqual(libs.name_variants('libfoo.1.2.3.so', version_only=True), [
            'libfoo.1.2.3.so',
            'libfoo.1.2.so',
            'libfoo.1.so',
            'libfoo.so',
    ])
