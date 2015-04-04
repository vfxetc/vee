from . import *


class TestSelf(TestCase):

    def test_dependencies(self):

        a = MockPackage('self_dependee', 'self')
        a.render_commit()

        b = MockPackage('self_depender', 'self', defaults={"REQUIRES":
            '%s --install-name %s/1.0.0' % (a.path, a.name)})
        b.render_commit()

        vee(['install', b.path, '--install-name', '%s/1.0.0' % b.name])

        self.assertExists(sandbox('vee/installs/%s/1.0.0/bin/%s' % (a.name, a.name)))
        self.assertExists(sandbox('vee/installs/%s/1.0.0/bin/%s' % (b.name, b.name)))