import base64
import os
import re

from vee import log
from vee.cli import style_note
from vee.package import Package
from vee.pipeline.generic import GenericBuilder
from vee.subproc import call, bash_source
from vee.utils import find_in_tree


class SelfBuilder(GenericBuilder):

    factory_priority = 9000

    @classmethod
    def factory(cls, step, pkg):

        for file_step, file_name, attr_name in [
            ('inspect', 'vee-manifest.txt' , 'manifest_txt'),
            ('build'  , 'vee-build.sh'     , 'build_sh'),
            ('install', 'vee-install.sh'   , 'install_sh'),
            ('develop', 'vee-develop.sh'   , 'develop_sh'),
        ]:
            if step == file_step:

                # Look for the attribute on the package:
                url = getattr(pkg, attr_name, None)
                if url:
                    
                    # Allow these scripts to be relative to the repository
                    if url.startswith('repo:'):
                        rel_path = url[5:].lstrip('/')
                        try:
                            root = pkg.set.env.repo.work_tree
                        except AttributeError:
                            raise RuntimeError('relative %s outside of environment' % attr_name)
                        path = os.path.join(root, rel_path)

                    # ... or be searched for
                    elif '/' not in url:
                        path = find_in_tree(pkg.build_path, url)

                    # ... or just be relative (which can be forced via './something')
                    else:
                        path = os.path.abspath(pkg.build_path, url)

                    if not path:
                        raise ValueError('%s cannot be found for %s' % (attr_name, url))
                    if not os.path.exists(path):
                        raise ValueError('%s does not exist at %s' % (attr_name, path or url))

                # Search the package tree for the generic name.
                else:
                    path = find_in_tree(pkg.build_path, file_name)

                # Build the step.
                if path:
                    self = cls(pkg)
                    setattr(self, attr_name, path)
                    return self

    def __init__(self, pkg):
        super(SelfBuilder, self).__init__(pkg)
        self.manifest_txt = self.build_sh = self.develop_sh = None

    def inspect(self):
        log.info(style_note('Inspecting %s' % os.path.basename(self.manifest_txt)))
        pkg = self.package
        for line in open(self.manifest_txt):
            line = line.strip()
            if not line or line[0] == '#':
                continue
            pkg.dependencies.append(Package(line, home=pkg.home))

    def build(self):

        log.info(style_note('source %s' % os.path.basename(self.build_sh)))

        pkg = self.package
        pkg._assert_paths(build=True, install=True)
        
        env = pkg.fresh_environ()
        env.update(
            VEE=pkg.home.root,
            VEE_BUILD_PATH=pkg.build_path,
            VEE_INSTALL_NAME=pkg.install_name,
            VEE_INSTALL_PATH=pkg.install_path,
        )

        # TODO: somehow derive this from --build-sh provided script.
        cwd = os.path.dirname(self.build_sh)
        envfile = os.path.join(cwd, 'vee-env-' + base64.b16encode(os.urandom(8)).decode())

        call(['bash', '-c', '. %s; env | grep VEE > %s' % (os.path.basename(self.build_sh), envfile)], env=env, cwd=cwd)

        env = list(open(envfile))
        env = dict(line.strip().split('=', 1) for line in env)
        os.unlink(envfile)

        pkg.build_subdir = env.get('VEE_BUILD_SUBDIR') or ''
        pkg.install_prefix = env.get('VEE_INSTALL_PREFIX') or ''

    def install(self):

        log.info(style_note('source %s' % os.path.basename(self.install_sh)))

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
        
        log.info(style_note('source %s' % os.path.basename(self.develop_sh)))

        pkg = self.package

        def setenv(name, value):
            log.info('vee develop setenv %s "%s"' % (name, value))
            pkg.environ[name] = value

        with log.indent():
            bash_source(os.path.basename(self.develop_sh), callbacks=dict(vee_develop_setenv=setenv), cwd=os.path.dirname(self.develop_sh))
