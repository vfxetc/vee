import os
import re

from vee import log
from vee.cli import style, style_note
from vee.pipeline.base import PipelineStep
from vee.subproc import call
from vee.utils import cached_property
from vee.exceptions import AlreadyInstalled, PipelineError


class RPMChecker(PipelineStep):

    @cached_property
    def installed_packages(self):

        packages = set()

        out = call(['rpm', '-qa'], stdout=True)
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            packages.add(line)

            chunks = line.split('-')
            for i in xrange(1, len(chunks)):
                packages.add('-'.join(chunks[:i]))

            chunks = line.split('.')
            for i in xrange(1, len(chunks)):
                packages.add('.'.join(chunks[:i]))

        return packages

    @classmethod
    def factory(cls, step, pkg):
        if step == 'init' and re.match(r'^rpm:', pkg.url):
            return cls(pkg)

    def init(self):
        pkg = self.package
        pkg.install_path = '/'

    def fetch(self):
        pkg = self.package
        if pkg.name not in self.installed_packages:
            raise PipelineError('RPM %s is not installed.' % pkg.name)
        raise AlreadyInstalled()

    def inspect(self):
        pass
        
    def extract(self):
        pass

    def build(self):
        pass

    def install(self):
        pass

    def optlink(self):
        pass

    def relocate(self):
        pass
