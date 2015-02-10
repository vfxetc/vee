
class Package(object):
    
    def __init__(self, home, req):
        self.home = home
        self.requirement = req

    def __repr__(self):
        return '%s(%r)' % (
            self.__class__.__name__,
            str(self.requirement),
        )

    def fetch(self):
        pass

    def install(self):
        pass
