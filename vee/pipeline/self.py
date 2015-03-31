import os

from vee.pipeline.generic import GenericBuilder
from vee.cli import style_note
from vee.utils import find_in_tree
from vee.subproc import call
from vee import log


class SelfBuilder(GenericBuilder):

    factory_priority = 9999

    @classmethod
    def factory(cls, step, pkg):
        if step not in ('build', 'develop'):
            return
        build_sh = find_in_tree(pkg.build_path, 'vee-build.sh')
        develop_sh = find_in_tree(pkg.build_path, 'vee-develop.sh')
        if (step == 'build' and build_sh) or (step == 'develop' and develop_sh):
            return cls(pkg, build_sh, develop_sh)

    def __init__(self, pkg, build_sh, develop_sh):
        super(SelfBuilder, self).__init__(pkg)
        self.build_sh = build_sh
        self.develop_sh = develop_sh

    def build(self):

        log.info(style_note('source vee-build.sh'))

        pkg = self.package

        env = pkg.fresh_environ()
        env.update(
            VEE=pkg.home.root,
            VEE_BUILD_PATH=pkg.build_path,
            VEE_INSTALL_NAME=pkg.install_name,
            VEE_INSTALL_PATH=pkg.install_path,
        )

        cwd = os.path.dirname(self.build_sh)
        envfile = os.path.join(cwd, 'vee-env-' + os.urandom(8).encode('hex'))

        call(['bash', '-c', '. %s; env | grep VEE > %s' % (os.path.basename(self.build_sh), envfile)], env=env, cwd=cwd)

        env = list(open(envfile))
        env = dict(line.strip().split('=', 1) for line in env)
        os.unlink(envfile)

        pkg.build_subdir = env.get('VEE_BUILD_SUBDIR') or ''
        pkg.install_prefix = env.get('VEE_INSTALL_PREFIX') or ''

    def develop(self):

        log.info(style_note('source vee-develop.sh'))

        def setenv(name, value):
            log.info('vee develop setenv %s "%s"' % (name, value))
            pkg.environ[name] = value

        with log.indent():
            bash_source(os.path.basename(self.develop_sh), callbacks=dict(vee_develop_setenv=setenv), cwd=os.path.dirname(self.develop_sh))
