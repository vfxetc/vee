from . import *

from vee.utils import guess_name
from vee.packages.git import normalize_git_url


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


class TestGitURLs(TestCase):

    def test_scp_urls(self):
        self.assertEqual(
            normalize_git_url('user@example.com:path/to/git'),
            'git+ssh://user@example.com/path/to/git'
        )
        self.assertEqual(
            normalize_git_url('user@example.com:/path/to/git'),
            'git+ssh://user@example.com/path/to/git'
        )
        self.assertEqual(
            normalize_git_url('example.com:path/to/git'),
            'git+ssh://example.com/path/to/git'
        )
        self.assertEqual(
            normalize_git_url('git+user@example.com:path/to/git'),
            'git+ssh://user@example.com/path/to/git'
        )

    def test_http_urls(self):
        self.assertEqual(
            normalize_git_url('http://user@example.com/path/to/git'),
            'git+http://user@example.com/path/to/git'
        )
        self.assertEqual(
            normalize_git_url('git+http://example.com/path/to/git'),
            'git+http://example.com/path/to/git'
        )

    def test_ssh_urls(self):
        self.assertEqual(
            normalize_git_url('ssh://user@example.com/path/to/git'),
            'git+ssh://user@example.com/path/to/git'
        )
        self.assertEqual(
            normalize_git_url('git+ssh://example.com/path/to/git'),
            'git+ssh://example.com/path/to/git'
        )

    def test_git_urls(self):
        self.assertEqual(
            normalize_git_url('git://user@example.com/path/to/git'),
            'git://user@example.com/path/to/git'
        )
        self.assertEqual(
            normalize_git_url('git:example.com/path/to/git'),
            'git://example.com/path/to/git'
        )

    def test_file_urls(self):
        self.assertEqual(
            normalize_git_url('git+file:///path/to/git'),
            'git+file:///path/to/git'
        )
        self.assertEqual(
            normalize_git_url('git+/path/to/git'),
            'git+file:///path/to/git'
        )

