from . import *

from vee.utils import guess_name


class TestGuessName(TestCase):

    def test_guess_name(self):
        self.assertEqual(
            guess_name('https://github.com/exampleorg/example.git'),
            'example',
        )
        self.assertEqual(
            guess_name('git@github.com:exampleorg/example.git'),
            'example',
        )
        self.assertEqual(
            guess_name('git@github.com:exampleorg/prefix-example.git'),
            'prefix-example',
        )
        self.assertEqual(
            guess_name('git@git.exampleorg:exampleorg/example'),
            'example',
        )
        self.assertEqual(
            guess_name('https://pypi.python.org/packages/source/e/example/example-1.0.0.tar.gz#md5=something'),
            'example',
        )
        self.assertEqual(
            guess_name('http://example.org/download/example/Example-v1.0.0-rc1.tar.gz?key=value'),
            'Example',
        )
