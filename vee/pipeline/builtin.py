from vee.pipeline.base import PipelineStep

from vee.builtin import load_builtin


class BuiltinLoader(PipelineStep):
    
    factory_priority = 9999

    @classmethod
    def factory(cls, step, pkg):
        if step == 'init' and pkg.url.startswith('builtin:'):
            return cls()

    def init(self, pkg):
        
        name = pkg.url.split(':')[1]
        meta_cls = load_builtin(name, 'Package')

        if not meta_cls:
            raise ValueError("no builtin Package for {!r}".format(name))

        pkg.meta = meta_cls()

