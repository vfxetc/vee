import fnmatch
import os
import re
from subprocess import CalledProcessError
import shutil

from vee.git import GitRepo
from vee.utils import makedirs


class MockPackage(object):

    def __init__(self, name, template, defaults=None):
        self.name = name
        self.template = os.path.abspath(os.path.join(
            __file__, '..', '..', 'package-templates', template
        ))
        self.path = os.path.abspath(os.path.join(
            __file__, '..', '..', 'sandbox', 'packages', name
        ))
        makedirs(self.path)
        self.repo = GitRepo(self.path)
        self.repo.git('init', silent=True, stdout=True)

        self.defaults = defaults or {}
        self.defaults.setdefault('NAME', self.name)

        self._rev_count = None

    def rev_list(self):
        try:
            return self.repo.git('rev-list', '--all', silent=True, stdout=True, stderr=True)[0].strip().split()
        except CalledProcessError:
            return []

    @property
    def rev_count(self):
        if self._rev_count is None:
            self._rev_count = len(self.rev_list())
        return self._rev_count

    def render_commit(self, message=None, **kwargs):

        params = self.defaults.copy()
        params.update(kwargs)
        params.update(
            REV_NO=self.rev_count + 1,
        )

        def render(contents):
            return re.sub(r'__MOCK_(\w+)__', lambda m: str(params.get(m.group(1)) or ''), contents)

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
                dst_path = os.path.join(self.path, render(rel_path))
                makedirs(os.path.dirname(dst_path))

                contents = render(open(src_path, 'rb').read())
                with open(dst_path, 'wb') as fh:
                    fh.write(contents)
                shutil.copystat(src_path, dst_path)

        self.repo.git('add', '--', self.path, silent=True, stdout=True)
        self.repo.git('commit', '-m', message or 'Rendered from template', silent=True, stdout=True)
