import pkg_resources

_build_types = []

def make_builder(pkg):

    if not _build_types:
        _build_types[:] = [ep.load() for ep in pkg_resources.iter_entry_points('vee_build_types')]
        _build_types.sort(key=lambda cls: cls.factory_priority, reverse=True)

    for cls in _build_types:
        builder = cls.factory(pkg)
        if builder:
            return builder

    raise ValueError('no builder for %s' % pkg)
