from vee.builds.generic import GenericBuild
from vee.utils import find_in_tree


class SelfBuild(GenericBuild):

    type = 'self'

    factory_priority = 9999

    @classmethod
    def factory(cls, pkg):
        
        script_path = find_in_tree(pkg.build_path, 'vee-build.sh')
        if script_path:
            return cls(pkg, script_path)

    def __init__(self, pkg, script_path):
        super(SelfBuild, self).__init__(pkg)
        self.script_path = script_path

    def build(self):

        print style('Running vee-build.sh...', 'blue', bold=True)

        pkg = self.package

        env = pkg.fresh_environ()
        env.update(
            VEE=pkg.home.root,
            VEE_BUILD_PATH=pkg.build_path,
            VEE_INSTALL_NAME=pkg.install_name,
            VEE_INSTALL_PATH=pkg.install_path,
        )

        cwd = os.path.dirname(self.script_path)
        envfile = os.path.join(cwd, 'vee-env-' + os.urandom(8).encode('hex'))

        call_log(['bash', '-c', '. %s; env | grep VEE > %s' % (os.path.basename(self.script_path), envfile)], env=env, cwd=cwd)

        env = list(open(envfile))
        env = dict(line.strip().split('=', 1) for line in env)
        os.unlink(envfile)

        pkg.build_subdir = env.get('VEE_BUILD_SUBDIR') or ''
        pkg.install_prefix = env.get('VEE_INSTALL_PREFIX') or ''
