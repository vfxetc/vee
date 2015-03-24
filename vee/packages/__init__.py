from vee._vendor import pkg_resources


_package_types = []


def make_package(req, home=None, set=None):

    if not _package_types:
        _package_types[:] = [ep.load() for ep in pkg_resources.iter_entry_points('vee_package_types')]
        _package_types.sort(key=lambda cls: cls.factory_priority, reverse=True)

    for cls in _package_types:
        package = cls.factory(req, home, set)
        if package:
            return package

    raise ValueError('no package for %s' % req)
