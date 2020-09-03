import functools

from vee.pipeline.base import PipelineStep


class MetaStep(PipelineStep):
    
    factory_priority = 9001

    @classmethod
    def factory(cls, step, pkg):
        if pkg.get_meta(step):
            return cls(pkg)

    def fetch(self):
        self.package.get_meta('fetch')(self.package)

    def extract(self):
        self.package.get_meta('extract')(self.package)

    def inspect(self):
        self.package.get_meta('inspect')(self.package)

    def build(self):
        self.package.get_meta('build')(self.package)

    def install(self):
        self.package.get_meta('install')(self.package)

    def link(self):
        self.package.get_meta('link')(self.package)

