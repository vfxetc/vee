import os
import shutil
import sys

from vee import libs
from vee import log
from vee.cli import style_note
from vee.envvars import join_env_path
from vee.pipeline.base import PipelineStep
from vee.subproc import call, bash_source
from vee.utils import find_in_tree, linktree, makedirs, chmod
from vee.homebrew import Homebrew


class GenericBuilder(PipelineStep):
    
    factory_priority = 0

    @classmethod
    def factory(cls, step, pkg):
        return cls()

    def init(self, pkg):
        pass
    
    def inspect(self, pkg):
        pass

    def build(self, pkg):
        log.info(style_note('Generic package; nothing to build.'), verbosity=1)

    def install(self, pkg):

        if pkg.pseudo_homebrew:
            homebrew = Homebrew(home=pkg.home)
            version = pkg.version.split('+')[0]
            untapped_name = pkg.name.split('/')[-1] # Deal with taps.
            pkg.install_path = os.path.join(homebrew.cellar, untapped_name, version)
            log.info(style_note('Re-installing into Homebrew', 'as %s/%s' % (untapped_name, version)))

        pkg._assert_paths(install=True)

        if pkg.make_install:
            log.warning('--make-install specified, but no Makefile found.')

        if os.path.exists(pkg.install_path):
            log.warning('Removing existing install', pkg.install_path)
            shutil.rmtree(pkg.install_path)

        if pkg.hard_link:
            log.info(style_note('Installing via hard-link', 'to ' + pkg.install_path))
            linktree(pkg.build_path_to_install, pkg.install_path_from_build, symlinks=True)
        else:
            log.info(style_note('Installing via copy', 'to ' + pkg.install_path))
            shutil.copytree(pkg.build_path_to_install, pkg.install_path_from_build, symlinks=True)

    def post_install(self, pkg):
        # TODO: Pull this from repository config (when that exists).
        chmod(pkg.install_path, 'o-w', recurse=True)

    def relocate(self, pkg):
        relocate_package(pkg)

    def optlink(self, pkg):
        if pkg.name:
            opt_link = pkg.home._abs_path('opt', pkg.name)
            log.info(style_note('Linking to opt/%s' % pkg.name))
            if os.path.lexists(opt_link):
                os.unlink(opt_link)
            makedirs(os.path.dirname(opt_link))
            os.symlink(pkg.install_path, opt_link)

    def develop(self, pkg):
        for name in ('bin', 'scripts'):
            path = os.path.join(pkg.build_path, name)
            if os.path.exists(path):
                log.info(style_note("Adding ./%s to $PATH" % name))
                pkg.environ['PATH'] = join_env_path('./' + name, pkg.environ.get('PATH', '@'))


def relocate_package(pkg):

    if pkg.relocate:
        log.info(style_note('Relocating'))
        with log.indent():
            libs.relocate(pkg.install_path,
                con=pkg.home.db.connect(),
                spec=pkg.render_template(pkg.relocate),
            )

    if pkg.set_rpath and sys.platform.startswith('linux'):
        rpath = pkg.render_template(pkg.set_rpath)
        log.info(style_note('Setting RPATH to', rpath))
        with log.indent():
            libs.relocate(pkg.install_path,
                con=pkg.home.db.connect(),
                spec=rpath,
            )
