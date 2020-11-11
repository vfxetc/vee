from . import *

from vee.manifest import Manifest


class TestRequirements(TestCase):

    def test_global_envvars(self):
        manifest = Manifest(home=self.home())
        manifest.parse_file('''
            first
            KEY=VALUE1
            second
            KEY=VALUE2
            third
        '''.strip().splitlines())
        pkgs = list(manifest.iter_packages())
        self.assertEqual(pkgs[0].base_environ, {})
        self.assertEqual(pkgs[1].base_environ, {'KEY': 'VALUE1'})
        self.assertEqual(pkgs[2].base_environ, {'KEY': 'VALUE2'})

    def test_local_envvars(self):
        manifest = Manifest(home=self.home())
        manifest.parse_file('''
            url -e KEY=VALUE
        '''.strip().splitlines())

        flat = ''.join(manifest.iter_dump()).strip()
        self.assertEqual(flat, 'file:url --environ=KEY=VALUE')

    def test_elif(self):
        manifest = Manifest(home=self.home())
        manifest.parse_file('''
            % if 0:
                zero
            % elif 1:
                one
            % else:
                two
            % endif
        '''.strip().splitlines())
        pkgs = list(manifest.iter_packages())
        self.assertEqual(len(pkgs), 1)
        self.assertEqual(pkgs[0].name, 'one')

    def test_else(self):
        reqs = Manifest(home=self.home())
        reqs.parse_file('''
            % if 0:
                zero
            % elif 0:
                one
            % else:
                two
            % endif
        '''.strip().splitlines())
        pkgs = list(reqs.iter_packages())
        self.assertEqual(len(pkgs), 1)
        self.assertEqual(pkgs[0].name, 'two')

    def test_platforms(self):
        manifest = Manifest(home=self.home())
        manifest.parse_file('''

            before
            % if MACOS:
                macos
            % elif LINUX:
                linux
            % endif
            after

        '''.strip().splitlines())

        print(manifest)

        pkgs = list(manifest.iter_packages())
        self.assertEqual(pkgs[0].name, 'before')
        if sys.platform == 'darwin':
            self.assertEqual(pkgs[1].name, 'macos')
        elif sys.platform == 'linux2':
            self.assertEqual(pkgs[1].name, 'linux')
        self.assertEqual(pkgs[2].name, 'after')

    def test_includes_read(self):
        manifest = Manifest(
            file=os.path.abspath(os.path.join(__file__, '..', 'requirements', 'includes', 'main.txt')),
            home=self.home(),
        )
        names = [pkg.name for pkg in manifest.iter_packages()]
        self.assertEqual(names, ['main', 'always', 'true'])

    def test_includes_write(self):

        os.makedirs(self.sandbox())
        home = self.home()

        main_path = self.sandbox('main.txt')
        with open(main_path, 'w') as fh:
            fh.write(dedent('''
                main.tgz
                %include include.txt
            '''.lstrip()))

        incl_path = self.sandbox('include.txt')
        with open(incl_path, 'w') as fh:
            fh.write(dedent('''
                include.tgz
            '''.lstrip()))

        manifest = Manifest(file=main_path, home=home)
        main, incl = manifest.iter_packages()

        self.assertEqual(main.name, 'main')

        main.version = '1'
        incl.version = '2'

        manifest.dump(main_path)

        manifest = Manifest(file=main_path, home=home)
        main, incl = manifest.iter_packages()
        self.assertEqual(main.name, 'main')
        self.assertEqual(main.version, '1')
        self.assertEqual(incl.version, '2')




