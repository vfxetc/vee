import stat

from . import *

from vee.utils import guess_name, chmod
from vee.git import normalize_git_url


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
            'example',
        )
        self.assertEqual(
            guess_name('homebrew+sqlite3'),
            'sqlite3',
        )
        self.assertEqual(
            guess_name('homebrew:sqlite3'),
            'sqlite3',
        )
        self.assertEqual(
            guess_name('git+https://github.com/PixarAnimationStudios/OpenSubdiv'),
            'opensubdiv',
        )

    def test_guess_name_regressions(self):
        self.assertEqual(
            guess_name('https://pypi.python.org/packages/2.7/S/Sphinx/Sphinx-1.3.1-py2.py3-none-any.whl'),
            'sphinx',
        )



class TestChmod(TestCase):

    def test_chmod(self):

        dir_ = self.sandbox()
        os.makedirs(dir_)

        for start, spec, end in (
            (0o777, '-w'    , 0o555),
            (0o777, '=r'    , 0o444),
            (0o777, 'go-w'  , 0o755),
            (0o555, 'u+w,o=', 0o750),
        ):
            name = '{:o},{},{:o}'.format(start, spec, end)
            path = os.path.join(dir_, name)
            open(path, 'w')
            os.chmod(path, start)
            chmod(path, spec)
            mode = stat.S_IMODE(os.stat(path).st_mode)
            self.assertEqual(oct(mode), oct(end))
