from . import *


class TestExternal(TestCase):

    def test_dependencies(self):

        a = MockPackage('external_dependee', 'external')
        a.render_commit()

        b = MockPackage('external_depender', 'external', defaults={"REQUIRES":
            '%s --install-name %s/1.0.0 --build-sh build.sh --install-sh install.sh' % (a.path, a.name)})
        b.render_commit()

        vee(['install', b.path, '--install-name', '%s/1.0.0' % b.name,
            '--build-sh', 'build.sh',
            '--install-sh', 'install.sh',
            '--requirements-txt', 'requirements.txt',
        ])

        self.assertExists(sandbox('vee/installs/%s/1.0.0/bin/%s' % (a.name, a.name)))
        self.assertExists(sandbox('vee/installs/%s/1.0.0/bin/%s' % (b.name, b.name)))

