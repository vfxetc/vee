import contextlib
import copy

class Proxy(object):

    def __init__(self, func):
        self.__dict__['get_proxied'] = func
    def __repr__(self):
        return '<Proxy via %r of %r>' % (self.get_proxied, self.get_proxied())

    def __str__(self):
        return self.get_proxied().__str__()

    def __getattr__(self, name):
        return getattr(self.get_proxied(), name)
    def __setattr__(self, name, value):
        setattr(self.get_proxied(), name, value)
    def __delattr__(self, name):
        delattr(self.get_proxied(), name)

    def __getitem__(self, name):
        return self.get_proxied()[name]
    def __setitem__(self, name, value):
        self.get_proxied()[name] = value
    def __delitem__(self, name):
        del self.get_proxied()[name]

    def __iter__(self):
        return iter(self.get_proxied())
    def __len__(self):
        return len(self.get_proxied())
    def __nonzero__(self):
        return bool(self.get_proxied())

    def __call__(self, *args, **kwargs):
        return self.get_proxied()(*args, **kwargs)


class Namespace(object):
    pass


class Stack(list):

    def __init__(self, init=None):
        self.append(Namespace() if init is None else init)

    @property
    def top(self):
        return self[-1]

    def push(self, obj=None):
        obj = copy.deepcopy(self[-1]) if obj is None else obj
        self.append(obj)
        return obj

    @contextlib.contextmanager
    def context(self, obj=None):
        self.push(obj)
        try:
            yield
        finally:
            self.pop()

    def proxy(self, name=None):
        if name is None:
            return Proxy(lambda: self[-1])
        else:
            return Proxy(lambda: getattr(self[-1], name))

