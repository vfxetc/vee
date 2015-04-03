from vee.pipeline.base import PipelineStep


class DeferredStep(PipelineStep):
    
    factory_priority = 9999

    @classmethod
    def factory(cls, step, pkg):
        if pkg.url.startswith('deferred:'):
            return cls(pkg)

    def init(self):
        pass
    

