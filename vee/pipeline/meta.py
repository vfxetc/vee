import functools

from vee.pipeline.base import PipelineStep


class MetaStep(PipelineStep):
    
    factory_priority = 9001

    @classmethod
    def factory(cls, step, pkg):
        if pkg.get_meta(step):
            return cls()

    def fetch(self, pkg):
        pkg.get_meta('fetch')(pkg)

    def extract(self, pkg):
        pkg.get_meta('extract')(pkg)

    def inspect(self, pkg):
        pkg.get_meta('inspect')(pkg)

    def build(self, pkg):
        pkg.get_meta('build')(pkg)

    def install(self, pkg):
        pkg.get_meta('install')(pkg)

    def link(self):
        pkg.get_meta('link')(pkg)

