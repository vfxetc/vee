import pkg_resources



class BaseManager(object):

    name = 'base'

    def __init__(self, package=None, home=None):
        self.package = package
        self.home = home or package.home

    def __repr__(self):
        return '%s(%r)' % (
            self.__class__.__name__,
            str(self.package),
        )

    def fetch(self):
        pass

    def install(self):
        pass

