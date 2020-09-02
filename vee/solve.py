import re

from vee.semver import Version, VersionExpr


class SolveError(ValueError):
    pass


def loads_provides(raw):
    """Parse a serialized provision."""

    out = {}

    for chunk in raw.split(','):
        chunk = chunk.strip()

        # Just a name means we only care about presence.
        m = re.match(r'^\w+$', chunk)
        if m:
            out.setdefault(chunk, None)
            continue

        m = re.match(r'^(\w+)\s*=\s*(.+)$', chunk)
        if m:
            name, value = m.groups()
            out[name] = Version(value.strip())
            continue

        raise ValueError("could not parse provision {!r}".format(chunk))

    return out


def loads_requires(raw):
    """parse a serialized requirement."""

    out = {}

    for chunk in raw.split(';'):
        chunk = chunk.strip()

        # Just a name means we only care about presence.
        m = re.match(r'^\w+$', chunk)
        if m:
            out.setdefault(chunk, {})
            continue

        # Shortcut for version.
        # TODO: Use the version expression regex.
        m = re.match(r'^(\w+)([^\w:].+)$', chunk)
        if m:
            name, raw_expr = m.groups()
            expr = VersionExpr(raw_expr.strip())
            out.setdefault(name.strip(), {})['version'] = expr
            continue

        m = re.match(r'^(\w+):(.+)$', chunk)
        if not m:
            raise ValueError("could not parse provision {!r}".format(chunk))

        name, rest = m.groups()
        data = out.setdefault(name.strip(), {})

        for hunk in rest.split(','):
            hunk = hunk.strip()

            # Just a name is for presence.
            m = re.match(r'^\w+$', hunk)
            if m:
                data.setdefault(hunk, None)
                continue

            m = re.match(r'^(\w+)(.+)$', hunk)
            if not m:
                raise ValueError("could not parse provision {!r}; bad hunk {!r}".format(chunk, hunk))
            key, raw_expr = m.groups()
            expr = VersionExpr(raw_expr.strip())
            data[key.strip()] = expr

    return out


def solve_dependencies(requires, manifest):
    """Solve abstract requirements into concrete provisions.

    :param dict requires: The abstract requirements to solve.
    :param Manifest manifest: Where to pull packages from.
    :return dict: Concrete provisions that satisfy the abstract requirements.
    :raises SolveError: if unable to satisfy the requirements.

    """

