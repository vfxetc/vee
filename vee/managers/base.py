import pkg_resources

from vee.package import Package


class BaseManager(object):

    name = 'base'
    package_class = Package

    def __init__(self, home, req):
        self.home = home
        self.requirement = req

    def __repr__(self):
        return '%s(%r)' % (
            self.__class__.__name__,
            str(self.requirement),
        )

    def load_package(self, req):
        return self.package_class(self.home, req)

    def fetch(self, package):
        package.fetch()

    def install(self, package):
        package.install()

