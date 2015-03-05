from . import *


class TestDevelopCommand(TestCase):

    def test_dev_init(self):
        vee(['develop', 'init', 'tdc_init'])
        self.assertExists(os.path.join(VEE, 'dev/tdc_init/.git'))

    def test_dev_clone(self):
        pkg = MockPackage('tdc_clone', 'python_source')
        pkg.render_commit()
        vee(['develop', 'clone', pkg.path])
        self.assertExists(os.path.join(VEE, 'dev', pkg.name, pkg.name, '__init__.py'))

    def test_dev_install(self):

        pkg = MockPackage('tdc_install', 'python_source')
        pkg.render_commit()

        req_repo = MockRepo('tdc_simple')
        req_repo.add_requirements(pkg.git_url)
        
        vee(['repo', 'add', req_repo.name, req_repo.path])

        vee(['update', req_repo.name])
        vee(['upgrade', req_repo.name])

        vee(['develop', 'install', pkg.name])

        self.assertExists(os.path.join(VEE, 'dev/tdc_install/tdc_install/__init__.py'))


        cmd = ['python', '-c', 'import tdc_install; print tdc_install.__file__.replace("/lib64/", "/lib/")']
        
        default_out = subprocess.check_output(['vee', 'exec', '-r', req_repo.name] + cmd).strip()
        if default_out.endswith('.pyc'):
            default_out = default_out[:-1]
        self.assertEqual(default_out, os.path.join(VEE, 'environments/tdc_simple/master/lib/python2.7/site-packages/tdc_install/__init__.py'))
        
        # dev_out = subprocess.check_output(['vee', 'exec', '--dev', '-r', req_repo.name] + cmd).strip()
        # self.assertEqual(default_out, os.path.join(VEE, 'dev/tdc_install/tdc_install/__init__.py'))

