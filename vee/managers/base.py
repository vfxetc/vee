import pkg_resources



class BaseManager(object):

    name = 'base'

    def __init__(self, requirement=None, home=None):
        self.requirement = requirement
        self.home = home or requirement.home

    def __repr__(self):
        return '%s(%r)' % (
            self.__class__.__name__,
            str(self.requirement),
        )

    def fetch(self):
        pass

    def install(self):
        pass

