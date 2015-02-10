import pkg_resources




class BaseManager(object):

    package_class = None

    def __init__(self, req):
        self.requirement = req

    def __repr__(self):
        return '%s(%r)' % (
            self.__class__.__name__,
            str(self.requirement),
        )

    def load_package(self, req):
        if self.package_class is None:
            raise NotImplementedError()
        else:
            return self.package_class(req)


