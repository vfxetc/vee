from . import *

from vee import libs


class TestLibs(TestCase):

    def test_name_variants(self):

        self.assertEqual(libs.name_variants('libfoo.so'), ['libfoo.so', 'foo', 'libfoo.dylib'])
        self.assertEqual(libs.name_variants('libfoo.so.1'), ['libfoo.so.1', 'foo', 'libfoo.dylib.1', 'libfoo.dylib', 'libfoo.so'])
        self.assertEqual(libs.name_variants('libfoo.dylib'), ['libfoo.dylib', 'foo', 'libfoo.so'])
        self.assertEqual(libs.name_variants('foo'), ['foo', 'libfoo.dylib', 'libfoo.so'])
