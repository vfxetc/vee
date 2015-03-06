from vee.cli import style


class CliException(Exception):

    def __init__(self, *args, **kwargs):
        super(CliException, self).__init__(*args)
        self.errno = kwargs.pop('errno', 1)
        self.detail = kwargs.pop('detail', '')

    @property
    def clistr(self):
        return (
            style('Error: ', 'red', bold=True) +
            style(str(self), bold=True) + 
            (style('\n%s' % self.detail, faint=True) if self.detail is not None else '')
        )

class AlreadyInstalled(CliException, RuntimeError):

    @property
    def clistr(self):
        return style('Error: ', 'red', bold=True) + style(self.args[0] + ' is already installed', bold=True)


class AlreadyLinked(CliException, RuntimeError):

    @property
    def clistr(self):
        return style('Error: ', 'red', bold=True) + style(self.args[0] + ' is already linked into the environment', bold=True)

