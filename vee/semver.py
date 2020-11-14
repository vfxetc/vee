import copy
import functools
import re


class _Return(Exception):
    pass

def _gt(a, b, presence_is_greater=None):
    if a is not None and b is not None:

        # If coresponding pairs aren't the same type, then compare them
        # as strings.
        if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
            a = list(a)
            b = list(b)
            for i, (x, y) in enumerate(zip(a, b)):
                if type(x) != type(y):
                    a[i] = str(x)
                    b[i] = str(y)

        if a > b:
            raise _Return(True)
        if a < b:
            raise _Return(False)

    elif presence_is_greater is not None:
        if a is not None:
            raise _Return(presence_is_greater)
        elif b is not None:
            raise _Return(not presence_is_greater)


@functools.total_ordering
class Version(object):
    """A blend bettween `SemVer 2.0`_ and `PEP 440`_.

    .. _"SemVer 2.0": http://semver.org/
    .. _"PEP 440": https://www.python.org/dev/peps/pep-0440

    """

    @classmethod
    def coerce(cls, input_):
        return input_ if isinstance(input_, cls) else cls(input_)

    def __init__(self, raw):

        # Git revisions.
        if re.match(r'^[0-9a-fA-F]{6,}$', raw):
            self.build_metadata = (raw.lower(), )
            raw = ''
        else:
            self.build_metadata = None

        # Epoch (PEP)
        m = re.match(r'^(\d+)!(.+)$', raw)
        if m:
            self.epoch = int(m.group(1))
            raw = m.group(2)
        else:
            self.epoch = 0

        # Release (PEP and SemVER)
        m = re.match(r'^(\d+(?:\.\d+)*)', raw)
        if m:
            self.release = tuple(int(x) for x in m.group(1).split('.'))
            raw = raw[m.end(1):] # Leave the separator.
        else:
            self.release = None

        # Pre-Release (PEP)
        m = re.match(r'^(a(?:lpha)?|b(?:eta)?|rc)(\d*)(\.|\+|-|$)', raw)
        if m:
            self.pep_pre_release = (m.group(1), int(m.group(2) or 0))
            raw = raw[m.end(2):]
        else:
            self.pep_pre_release = None

        # Post-Release (PEP)
        m = re.match(r'^\.(p(?:ost)?)(\d+)(\.|\+|-|$)', raw)
        if m:
            self.post_release = (m.group(1), int(m.group(2) or 0))
            raw = raw[m.end(2):]
        else:
            self.post_release = None

        # Dev-Release (PEP)
        m = re.match(r'^\.(d(?:ev)?)(\d+)(\.|\+|-|$)', raw)
        if m:
            self.dev_release = (m.group(1), int(m.group(2) or 0))
            raw = raw[m.end(2):]
        else:
            self.dev_release = None

        # Pre-Release (SemVer)
        m = re.match(r'-([\w-]+(\.[\w-]+)*)(\+|$)', raw) # SemVer forbids underscore, but meh.
        if m:
            self.sem_pre_release = tuple(int(x) if x.isdigit() else x for x in m.group(1).split('.'))
            raw = raw[m.end(1):]
        else:
            self.sem_pre_release = None

        # Build metadata (PEP and SemVer, but PEP calls it "local version")
        m = re.match(r'^\+([\w-]+(\.[\w-]+)*)$', raw)
        if m:
            self.build_metadata = tuple(int(x) if x.isdigit() else x for x in m.group(1).split('.'))
            raw = raw[m.end(1):]
        else:
            pass
            # build_metadata is already set to None at the top.

        self.unknown = tuple(int(x) if x.isdigit() else x for x in raw.split('.')) if raw else None

    @property
    def local_version(self):
        return self.build_metadata

    @property
    def pre_release(self):
        return self.pep_pre_release or self.sem_pre_release

    @property
    def git_rev(self):
        if not self.build_metadata or len(self.build_metadata) != 1:
            return
        rev = self.build_metadata[0]
        if re.match(r'^[0-9a-fA-F]{6,}$', rev):
            return rev

    def __str__(self):
        chunks = []
        if self.epoch:
            chunks.append('%d!' % self.epoch)
        if self.release:
            chunks.append('.'.join(str(x) for x in self.release))
        if self.pep_pre_release:
            chunks.append('%s%s' % self.pep_pre_release)
        if self.post_release:
            chunks.append('.%s%s' % self.post_release)
        if self.dev_release:
            chunks.append('.%s%s' % self.dev_release)
        if self.sem_pre_release:
            chunks.append('-' + '.'.join(str(x) for x in self.sem_pre_release))
        if self.build_metadata:
            if chunks:
                chunks.append('+')
            chunks.append('.'.join(str(x) for x in self.build_metadata))
        if self.unknown:
            chunks.append('.'.join(str(x) for x in self.unknown))
        return ''.join(chunks)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def __eq__(a, b):

        if a is None or b is None:
            return False
        
        if not isinstance(a, Version):
            a = Version(a)
        if not isinstance(b, Version):
            b = Version(b)

        if a.__dict__ == b.__dict__:
            return True

        rev_a = a.git_rev
        rev_b = b.git_rev

        if rev_a and rev_b:
            min_len = min(len(rev_a), len(rev_b))
            return rev_a[:min_len] == rev_b[:min_len]

        return False

    def __ne__(a, b):
        return not (a == b)

    def __gt__(a, b):

        # Where A is greater than B if A comes after B in the development
        # cycle.
        
        if not isinstance(a, Version):
            a = Version(a)
        if not isinstance(b, Version):
            b = Version(b)

        try:
            _gt(a.epoch, b.epoch)
            _gt(a.release, b.release)
            _gt(a.pep_pre_release, b.pep_pre_release, presence_is_greater=False)
            _gt(a.post_release, b.post_release, presence_is_greater=True)
            _gt(a.dev_release, b.dev_release, presence_is_greater=False)
            _gt(a.sem_pre_release, b.sem_pre_release, presence_is_greater=False)
            _gt(a.unknown, b.unknown, presence_is_greater=False)
        except _Return as r:
            return r.args[0]

        return False


_expr_ops = {}

def _op(name):
    def decorator(func):
        _expr_ops[name] = func
        return func
    return decorator


@_op('')
@_op('=')
@_op('==')
def _op_eq(a, b):
    return a == b

@_op('!=')
def _op_ne(a, b):
    return a != b

@_op('<=')
def _op_gte(a, b):
    return a <= b
@_op('>=')
def _op_lte(a, b):
    return a >= b
@_op('<')
def _op_gt(a, b):
    return a < b
@_op('>')
def _op_lt(a, b):
    return a > b

@_op('===')
def _op_arbitrary_equality(a, b):
    # This is supposed to be a string comparison, but we don't have that.
    return a == b

@_op('~=')
def _op_compatible_release(a, b):

    # This is supposed to match symantic compatibility.

    # If it is too early, then it isn't compatible.
    if a < b:
        return False

    # Make sure it isn't very far in the future.
    c = Version('1')
    release = list(b.release)
    release[-1] = 0
    release[-2] += 1
    c.release = tuple(release)

    if a > c:
        return False

    return True



class VersionExpr(object):

    @classmethod
    def coerce(cls, input_):
        return input_ if isinstance(input_, cls) else cls(input_)
        
    def __init__(self, raw):

        self.clauses = []
        
        if isinstance(raw, Version):
            self.clauses.append(('==', raw))
            return

        for chunk in re.split(r'\s*,\s*', raw.strip()):
            m = re.match(r'^(%s)\s*([\w\.!@+-]+)$' % '|'.join(re.escape(x) for x in _expr_ops), chunk)
            if not m:
                raise ValueError('could not parse version expr chunk: %r' % chunk)
            op, raw_version = m.groups()
            version = Version(raw_version)
            self.clauses.append((op, version))

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, str(self))

    def __str__(self):
        return ','.join('%s%s' % x for x in self.clauses)
    
    def __eq__(self, other):
        if not isinstance(other, VersionExpr):
            raise TypeError("cannot compare {} to {}".format(self.__class__, other.__class__))
        return str(self) == str(other)

    def eval(self, v):
        if not isinstance(v, Version):
            v = Version(v)
        for op, op_v in self.clauses:
            op_func = _expr_ops[op]
            if not op_func(v, op_v):
                return False
        return True



