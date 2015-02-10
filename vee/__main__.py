# from vee.commands.main import main
import pkg_resources

if __name__ == '__main__':

    for x in pkg_resources.iter_entry_points('vee.commands'):
        print x
