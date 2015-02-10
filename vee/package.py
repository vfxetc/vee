
class Package(object):
    
    def __init__(self, req):
        self.requirement = req

    def __repr__(self):
        return '%s(%r)' % (
            self.__class__.__name__,
            str(self.requirement),
        )
