from vee.utils import style


class CliException(Exception):

    def __init__(self, message, errno=1):
        super(CliException, self).__init__(message)
        self.errno = errno

    @property
    def clistr(self):
        return style('Error: ', 'red', bold=True) + style(str(self), bold=True)


class AlreadyInstalled(CliException, RuntimeError):

    @property
    def clistr(self):
        return style('Error: ', 'red', bold=True) + style(self.args[0] + ' is already installed', bold=True)

