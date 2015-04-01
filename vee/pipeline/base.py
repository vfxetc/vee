import pkg_resources

from vee import log


_step_classes = []
_step_classes_by_name = {}


class Pipeline(object):
    
    def __init__(self, package, step_names):
        self._package = package
        self._step_names = list(step_names)
        self._step_index = dict((name, i) for i, name in enumerate(self._step_names))
        self._have_run = set()
        self.steps = {}

    def run_to(self, name, *args, **kwargs):

        if name in self._have_run:
            raise RuntimeError('already run %s' % name)

        # Run everything up to here.
        index = self._step_index[name]
        for name in self._step_names[:index + 1]:
            if name not in self._have_run:
                step = self.load(name)
                step.run(name, *args, **kwargs)
                self._have_run.add(name)

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
            step = prev_step.get_next(step_name)
            if step:
                log.debug('%s (%s) provided sucessor %s (%s) for %s' % (
                    prev_step.name, prev_name, step.name, step_name, self._package
                ), verbosity=2)
                self.steps[step_name] = step
                return step

        # Load the step classes.
        if not _step_classes:
            for ep in pkg_resources.iter_entry_points('vee_pipeline_steps'):
                cls = ep.load()
                cls.name = ep.name
                _step_classes.append(cls)
                _step_classes_by_name[ep.name] = cls
            _step_classes.sort(key=lambda cls: getattr(cls, 'factory_priority', 1), reverse=True)
        
        # Find something that self-identifies it provides this step.
        for cls in _step_classes:
            step = cls.factory(step_name, self._package)
            if step:
                log.debug('%s factory built %s for %s' % (step.name, step_name, self._package), verbosity=2)
                self.steps[step_name] = step
                return step

        raise ValueError('Cannot load %s step for %s' % (step_name, self._package.freeze()))


class PipelineStep(object):

    @classmethod
    def factory(cls, pkg):
        raise NotImplementedError()

    def __init__(self, pkg):
        self.package = pkg

    def get_next(self, next_step):
        return None

    def run(self, name, *args, **kwargs):
        func = getattr(self, name)
        if not func:
            raise ValueError('%s does not provide %s step' % (self.__class__.__name__, name))
        return func(*args, **kwargs)




