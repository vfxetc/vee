from vee._vendor import pkg_resources
from vee import log


_step_classes = []


class Pipeline(object):
    
    def __init__(self, package, step_names=None):
        self._package = package
        self._step_names = list(step_names) if step_names else ['fetch', 'extract', 'inspect', 'build', 'install']
        self._step_index = dict((name, i) for i, name in enumerate(self._step_names))
        self.steps = {}

    def run(self, step_name, *args, **kwargs):
        self.load(step_name)
        self.steps[step_name].run(step_name, *args, **kwargs)

    def load(self, step_name):

        try:
            return self.steps[step_name]
        except KeyError:
            pass

        # See if any previous steps provide it.
        step_i = self._step_index[step_name]
        for i in xrange(step_i - 1, -1, -1):
            prev_name = self._step_names[i]
            prev_step = self.steps[prev_name]
            step = prev_step.get_successor(step_name)
            if step:
                log.debug('%s (%s) provided sucessor %s (%s)' % (
                    prev_step.type, prev_name, step.type, step_name
                ))
                self.steps[step_name] = step
                return step

        # Find something that self-identifies it provides this step.
        if not _step_classes:
            _step_classes[:] = [ep.load() for ep in pkg_resources.iter_entry_points('vee_pipeline_steps')]
            _step_classes.sort(key=lambda cls: cls.factory_priority, reverse=True)
        for cls in _step_classes:
            step = cls.factory(step_name, self._package)
            if step:
                log.debug('%s factory built %s' % (step.type, step_name))
                self.steps[step_name] = step
                return step

        raise ValueError('Cannot load %s step for %s' % (step_name, self._package.freeze()))


class PipelineStep(object):

    @classmethod
    def factory(cls, pkg):
        raise NotImplementedError()

    def __init__(self, pkg):
        self.package = pkg

    def get_successor(self, next_step):
        return None

    def run(self, name, *args, **kwargs):
        func = getattr(self, name)
        if not func:
            raise ValueError('%s does not provide %s step' % (self.__class__.__name__, name))
        return func(*args, **kwargs)




