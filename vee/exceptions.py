from vee.cli import style


class CliException(Exception):

    def __init__(self, *args, **kwargs):
        super(CliException, self).__init__(*args)
        self.errno = kwargs.pop('errno', 1)

    @property
    def clistr(self):
        return style('Error: ', 'red', bold=True) + style(str(self), bold=True)


class AlreadyInstalled(CliException, RuntimeError):

    @property
    def clistr(self):
        return style('Error: ', 'red', bold=True) + style(self.args[0] + ' is already installed', bold=True)


class AlreadyLinked(CliException, RuntimeError):

    @property
    def clistr(self):
        return style('Error: ', 'red', bold=True) + style(self.args[0] + ' is already linked into the environment', bold=True)

