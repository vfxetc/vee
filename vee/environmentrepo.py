import os
import re

from vee.git import GitRepo
from vee.requirementset import RequirementSet, Header
from vee.utils import cached_property
from vee.exceptions import CliMixin


class EnvironmentRepo(GitRepo):

    def __init__(self, dbrow, home):
        super(EnvironmentRepo, self).__init__(
            work_tree=home._abs_path('repos', dbrow['name']),
            remote_name=dbrow['remote'],
            branch_name=dbrow['branch'],
        )
        self.id = dbrow['id']
        self.name = dbrow['name']
        self.home = home
        self._req_path = os.path.join(self.work_tree, 'requirements.txt')

    def fetch(self):
        return super(EnvironmentRepo, self).fetch(self.remote_name, self.branch_name)

    def checkout(self, force=False):
        super(EnvironmentRepo, self).checkout(
            revision='%s/%s' % (self.remote_name, self.branch_name), 
            branch=self.branch_name,
            force=force
        )

    def reqs(self, revision=None, guess_names=True):
        reqs = RequirementSet(home=self.home)
        if revision is not None:
            contents = self.git('show', '%s:requirements.txt' % revision, stdout=True, silent=True)
            reqs.parse_file(contents.splitlines())
        else:
            if os.path.exists(self._req_path):
                reqs.parse_file(self._req_path)
        if guess_names:
            reqs.guess_names()
        return reqs

    def iter_requirements(self):
        for req in self.reqs().iter_requirements():
            yield req

    def iter_git_requirements(self):
        for req in self.iter_requirements():
            if req.package.type == 'git':
                yield req

    def dump(self):
        with open(self._req_path, 'wb') as fh:
            for line in self.reqs.iter_dump():
                fh.write(line)

    def commit(self, message, level=None):

        self.git('add', self._req_path, silent=True)
        
        status = list(self.status())
        if not status:
            raise RuntimeError('nothing to commit')

        # Make sure there are no other changes.
        for idx, tree, name in status:
            if tree.strip():
                raise RuntimeError('work-tree is dirty')

        if level is not None:

            header = self.reqs.headers.get('Version')
            if not header:
                header = Header('Version', '0.0.0')
                self.reqs.insert(0, ('', header, ''))
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
