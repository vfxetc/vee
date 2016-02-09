import os
import re

from vee import log
from vee.cli import style, style_note
from vee.pipeline.base import PipelineStep
from vee.subproc import call
from vee.utils import makedirs
from vee.package import Package



class GemManager(PipelineStep):

    factory_priority = 1000

    _system_gems = {}

    @property
    def system_gems(self):
        if not self._system_gems:
            out = call(['gem', 'list', '--no-details'], stdout=True)
            for line in out.splitlines():
                m = re.match(r'^(\w+) \((.+?)\)', line.strip())
                if m:
                    self._system_gems[m.group(1)] = m.group(2)
        return self._system_gems

    @classmethod
    def factory(cls, step, pkg):
        if step == 'init' and re.match(r'^gem:', pkg.url):
            return cls(pkg)

    def get_next(self, step):
        if step != 'optlink':
            return self

    def init(self):
        return
        # Normalize the name.
        pkg = self.package
        pkg.package_name = re.sub(r'^gem:', '', pkg.url)

    def fetch(self):
        pass

    def inspect(self):
        # TODO: Figure out what the dependencies are, and list them here.
        #       Otherwise, each package will install a copy of shared dependencies.
        return

    def extract(self):
        pass

    def build(self):
        pass

    def install(self):
        pkg = self.package
        pkg._assert_paths(install=True)
        # TODO: Find the Ruby version.
        root = os.path.join(pkg.install_path, 'lib/ruby/2.0.0')
        makedirs(root)
        cmd = ['gem', 'install', pkg.name]
        if pkg.config:
            cmd.append('--')
            cmd.extend(pkg.render_template(x) for x in pkg.config)
        call(cmd, env={'GEM_HOME': root})

    def relocate(self):
        pass
