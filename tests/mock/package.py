import fnmatch
import os
import re
from subprocess import CalledProcessError
import shutil

from vee.git import GitRepo, GitError
from vee.utils import makedirs

from .http import mock_url


class MockPackage(object):

    def __init__(self, name, template, defaults=None, path=None):
        self.name = name
        self.template = os.path.abspath(os.path.join(
            __file__, '..', '..', 'package-templates', template
        ))
        self.path = os.path.abspath(os.path.join(
            __file__, '..', '..', '..', 'sandbox', 'packages', path or name
        ))
        makedirs(self.path)
        self.repo = GitRepo(self.path)
        self.repo.git('init', silent=True, stdout=True)

        self.defaults = defaults or {}
        self.defaults.setdefault('NAME', self.name)
        self.defaults.setdefault('VERSION', '1.0.0')

        self.rev_count = 0

    def clone(self, path):
        return MockPackage(self.name, os.path.basename(self.template), self.defaults.copy(), path)

    @property
    def git_url(self):
        return 'git+' + self.path
    
    @property
    def url(self):
        return mock_url(self.path + '.tgz')

    def rev_list(self):
        try:
            return self.repo.git('rev-list', '--all', silent=True, stdout=True, stderr=True)[0].strip().split()
        except GitError:
            return []

    def render(self, **kwargs):

        self.rev_count += 1
        
        params = self.defaults.copy()
        params.update(kwargs)
        params.update(
            REVNO=self.rev_count,
        )

        def render_contents(contents):
            return re.sub(r'MOCK([A-Z0-9]+)', lambda m: str(params.get(m.group(1)) or ''), contents)

        ignore_path = os.path.join(self.template, 'mockignore')
        if os.path.exists(ignore_path):
            patterns = [x.strip() for x in open(ignore_path)] + ['mockignore']
            pattern = re.compile('|'.join(fnmatch.translate(x) for x in patterns if x))
        else:
            pattern = None

        for dir_path, dir_names, file_names in os.walk(self.template):
            for file_name in file_names:
                if pattern and pattern.match(file_name):
                    continue

                src_path = os.path.join(dir_path, file_name)
                rel_path = os.path.relpath(src_path, self.template)
                dst_path = os.path.join(self.path, render_contents(rel_path))
                makedirs(os.path.dirname(dst_path))

                contents = render_contents(open(src_path, 'r').read())
                with open(dst_path, 'w') as fh:
                    fh.write(contents)
                shutil.copystat(src_path, dst_path)

    def commit(self, message=None):
        self.repo.git('add', '--', self.path, silent=True, stdout=True)
        self.repo.git('commit', '-m', message or 'Rendered from template', silent=True, stdout=True)
        self.rev_count = (self.rev_count or 0) + 1

    def render_commit(self, message=None, **kwargs):
        self.render(**kwargs)
        self.commit(message)

