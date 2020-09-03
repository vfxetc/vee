import os


def load_builtin(type_, name):

    path = os.path.join(os.path.dirname(__file__), type_ + '.py')

    if not os.path.exists(path):
        return

    with open(path, 'rb') as fh:
        source = fh.read()

    namespace = {'__file__': path}
    exec(compile(source, path, 'exec'), namespace, namespace)

    return namespace[name]

