from io import StringIO
from subprocess import CalledProcessError
import fnmatch
import os
import re
import shutil

from vee.git import GitRepo
from vee.package import Package
from vee.requirements import Requirements
from vee.utils import makedirs, guess_name


class MockRepo(object):

    def __init__(self, name, home=None):
        self.name = name
        self.path = os.path.abspath(os.path.join(
            __file__, '..', '..', '..', 'sandbox', 'repos', name
        ))
        makedirs(self.path)
        self.repo = GitRepo(self.path)
        self.repo.git('init', silent=True, stdout=True)

        if home is None:
            from tests import home
        self.home = home

        self._rev_count = None

    def rev_list(self):
        try:
            res = self.repo.git('rev-list', '--all', silent=True, stdout=True, stderr=True)
            return res[0].strip().split()
        except CalledProcessError:
            return []

    @property
    def rev_count(self):
        if self._rev_count is None:
            self._rev_count = len(self.rev_list())
        return self._rev_count

    def add_requirements(self, raw, insert=False, commit=True):

        old = Requirements(home=self.home)
        path = os.path.join(self.path, 'requirements.txt')
        if os.path.exists(path):
            old.parse_file(path)

        new = Requirements(home=self.home, file=StringIO(raw))

        new_urls = set()
        new_names = set()
        for req in new.iter_packages():
            new_names.add(req.name or guess_name(req.url))
            new_urls.add(req.url)

        for item in old:
            element = item.value
            if (not isinstance(element, Package) or
                (element.name or guess_name(element.url)) not in new_names or
                element.url not in new_urls
            ):
                if insert:
                    new.append(element)
                else:
                    new.insert(0, element)

        with open(path, 'wb') as fh:
            for line in new.iter_dump():
                fh.write(line)

        if commit:
            self.commit('add requirements')

    def commit(self, message):
        self.repo.git('add', 'requirements.txt', silent=True, stdout=True)
        self.repo.git('commit', '-m', message or 'do something', silent=True, stdout=True)
        self._rev_count = (self._rev_count or 0) + 1



