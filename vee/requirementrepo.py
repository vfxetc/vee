import os

from vee.git import GitRepo
from vee.requirementset import RequirementSet


class RequirementRepo(GitRepo):

    def __init__(self, *args, **kwargs):
        super(RequirementRepo, self).__init__(*args, **kwargs)
        self._req_path = None
        self._reqs = None

    @property
    def name(self):
        return os.path.basename(self.work_tree)

    def iter_requirements(self, home):
        
        if not self._reqs:
            self._reqs = RequirementSet(home=home)
            self._req_path = os.path.join(self.work_tree, 'requirements.txt')
            if os.path.exists(self._req_path):
                self._reqs.parse_file(self._req_path)

        for req in self._reqs.iter_requirements():
            yield req

    def iter_git_requirements(self, home):
        for req in self.iter_requirements(home):
            if req.package.type == 'git':
                yield req

    def dump(self):
        with open(self._req_path, 'wb') as fh:
            for line in self._reqs.iter_dump():
                fh.write(line)


