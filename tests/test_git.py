from vee.git import normalize_git_url

from . import *


class TestGitURLs(TestCase):

    def test_scp_urls(self):
        self.assertEqual(
            normalize_git_url('user@example.com:path/to/repo'),
            'user@example.com:path/to/repo'
        )
        self.assertEqual(
            normalize_git_url('user@example.com:/path/to/repo'),
            'user@example.com:/path/to/repo'
        )
        self.assertEqual(
            normalize_git_url('example.com:path/to/repo'),
            'example.com:path/to/repo'
        )
        self.assertEqual(
            normalize_git_url('git+user@example.com:path/to/repo'),
            'user@example.com:path/to/repo'
        )

    def test_github(self):
        self.assertEqual(
            normalize_git_url('git@github.com:example/repo.git'),
            'git@github.com:example/repo'
        )

    def test_http_urls(self):
        self.assertEqual(
            normalize_git_url('http://user@example.com/path/to/repo'),
            'http://user@example.com/path/to/repo'
        )
        self.assertEqual(
            normalize_git_url('git+http://example.com/path/to/repo'),
            'http://example.com/path/to/repo'
        )

    def test_ssh_urls(self):
        self.assertEqual(
            normalize_git_url('ssh://user@example.com/path/to/repo'),
            'ssh://user@example.com/path/to/repo'
        )
        self.assertEqual(
            normalize_git_url('git+ssh://example.com/path/to/repo'),
            'ssh://example.com/path/to/repo'
        )

    def test_git_urls(self):
        self.assertEqual(
            normalize_git_url('git://user@example.com/path/to/repo'),
            'git://user@example.com/path/to/repo'
        )
        self.assertEqual(
            normalize_git_url('git:example.com/path/to/repo'),
            'git://example.com/path/to/repo'
        )

    def test_file_urls(self):
        self.assertEqual(
            normalize_git_url('git+file:///path/to/repo'),
            'file:///path/to/repo'
        )
        self.assertEqual(
            normalize_git_url('git+/path/to/repo'),
            '/path/to/repo'
        )
        self.assertEqual(
            normalize_git_url('git+path/to/repo'),
            'path/to/repo'
        )
        self.assertEqual(
            normalize_git_url('git+/path/to/repo', prefix=True),
            'git+/path/to/repo'
        )

    def test_github_transforms(self):
        self.assertEqual(
            normalize_git_url('git@github.com:org/repo.git', prefer='https'),
            'https://github.com/org/repo',
        )
        self.assertEqual(
            normalize_git_url('https://github.com/org/repo.git', prefer='scp'),
            'git@github.com:org/repo',
        )
