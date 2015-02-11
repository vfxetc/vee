from vee.utils import colour


class CliException(Exception):

    def __init__(self, message, errno=1):
        super(CliException, self).__init__(message)
        self.errno = errno

    @property
    def clistr(self):
        return colour('ERROR: ', 'red', bright=True) + colour(str(self), 'black', reset=True)


class AlreadyInstalled(CliException, RuntimeError):

    @property
    def clistr(self):
        return colour('ERROR: ', 'red', bright=True) + colour(self.args[0] + ' is already installed', 'black', reset=True)

