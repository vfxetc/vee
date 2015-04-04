import os

from vee import log
from vee.cli import style_note
from vee.package import Package
from vee.pipeline.generic import GenericBuilder
from vee.subproc import call, bash_source
from vee.utils import find_in_tree


class SelfBuilder(GenericBuilder):

    factory_priority = 9999

    @classmethod
    def factory(cls, step, pkg):

        for file_step, file_name, attr_name in [
            ('inspect', 'vee-requirements.txt', 'requirements_txt'),
            ('build'  , 'vee-build.sh'        , 'build_sh'),
            ('install', 'vee-install.sh'      , 'install_sh'),
            ('develop', 'vee-develop.sh'      , 'develop_sh'),
        ]:
            if step == file_step:
                path = find_in_tree(pkg.build_path, file_name)
                if path:
                    self = cls(pkg)
                    setattr(self, attr_name, path)
                    return self

    def __init__(self, pkg):
        super(SelfBuilder, self).__init__(pkg)
        self.requirements_txt = self.build_sh = self.develop_sh = None

    def inspect(self):
        pkg = self.package
        for line in open(self.requirements_txt):
            line = line.strip()
            if not line or line[0] == '#':
                continue
            pkg.dependencies.append(Package(line, home=pkg.home))

    def build(self):

        log.info(style_note('source vee-build.sh'))

        pkg = self.package
        pkg._assert_paths(build=True, install=True)
        
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

    def install(self):

        log.info(style_note('source vee-install.sh'))

        pkg = self.package
        pkg._assert_paths(build=True, install=True)

        env = pkg.fresh_environ()
        env.update(
            VEE=pkg.home.root,
            VEE_BUILD_PATH=pkg.build_path,
            VEE_INSTALL_NAME=pkg.install_name,
            VEE_INSTALL_PATH=pkg.install_path,
        )
        cwd = os.path.dirname(self.install_sh)

        with log.indent():
            call(['bash', '-c', 'source "%s" "%s"' % (self.install_sh, pkg.install_path)], env=env, cwd=cwd)

    def develop(self):
        
        log.info(style_note('source vee-develop.sh'))

        pkg = self.package

        def setenv(name, value):
            log.info('vee develop setenv %s "%s"' % (name, value))
            pkg.environ[name] = value

        with log.indent():
            bash_source(os.path.basename(self.develop_sh), callbacks=dict(vee_develop_setenv=setenv), cwd=os.path.dirname(self.develop_sh))
