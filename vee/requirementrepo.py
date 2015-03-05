import os
import re

from vee.git import GitRepo
from vee.requirementset import RequirementSet, Header
from vee.utils import cached_property
from vee.exceptions import CliException


class RequirementRepo(GitRepo):

    def __init__(self, *args, **kwargs):
        self.home = kwargs.pop('home')
        super(RequirementRepo, self).__init__(*args, **kwargs)
        self._req_path = os.path.join(self.work_tree, 'requirements.txt')

    @cached_property
    def set(self):
        reqs = RequirementSet(home=self.home)
        if os.path.exists(self._req_path):
            reqs.parse_file(self._req_path)
        return reqs

    @property
    def name(self):
        return os.path.basename(self.work_tree)

    def iter_requirements(self, home):
        for req in self.set.iter_requirements():
            yield req

    def iter_git_requirements(self, home):
        for req in self.iter_requirements(home):
            if req.package.type == 'git':
                yield req

    def dump(self):
        with open(self._req_path, 'wb') as fh:
            for line in self.set.iter_dump():
                fh.write(line)

    def commit(self, message, level=None):

        self.git('add', self._req_path, silent=True)
        
        status = list(self.status())
        if not status:
            raise CliException('nothing to commit')

        # Make sure there are no other changes.
        for idx, tree, name in status:
            if tree.strip():
                raise CliException('work-tree is dirty')

        if level is not None:

            header = self.set.headers.get('version')
            if not header:
                header = Header('Version', '0.0.0')
                self.set.insert(0, ('', header, ''))
            version = []
            for i, x in enumerate(re.split(r'[.-]', header.value)):
                try:
                    version.append(int(x))
                except ValueError:
                    version.append(x)
            while len(version) <= level:
                version.append(0)
            version[level] = (version[level] if isinstance(version[level], int) else 0) + 1
            header.value = '.'.join(str(x) for x in version)

            self.dump()
            self.git('add', self._req_path, silent=True)

        self.git('commit', '-m', message, silent=True)
