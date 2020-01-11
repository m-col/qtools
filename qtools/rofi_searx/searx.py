"""
Qtile plugin to use rofi to execute a process using the URL for a randomised searx
instance.

Example usage:

    import qtools.rofi_searx
    searx = qtools.rofi_searx.Searx()
    keys.extend([EzKey(k, v) for k, v in {
        'M-s':   searx.lazy_search,
        'M-C-s': searx.lazy_remove_last_used,
    }.items()])

"""


import random
import shlex
import subprocess

from qtools import Notifier


class Searx(Notifier):
    """
    This plugin opens a rofi prompt to get a search query from the user, then randomly
    selects a searx instance from a provided list and opens a browser to carry out the
    web search.

    Searx instances can be provided directly as a list, or alternatively an
    instances_file path can be provided to load the list of searx instances from a file
    containing line-separated full URLs to searx instances.

    Searx.remove_last_used can be used to remove the previously used searx instance from
    the instance list. If an instance_file was provided, the last instance will simply
    be commented out in the file and ignored, but not removed. New instances can be
    added by adding to the file, and either restarting Qtile or binding
    Searx.lazy_load_instances to a key.
    """
    defaults = [
        ('summary', 'Searx', 'Notification summary.'),
        ('instances', ['https://searx.me'], 'List of searx instance base URLs.'),
        ('instances_file', None, 'File containing list of searx instances. If specified'
                                 ' instances passed directly are ignored.'),
        ('prompt', 'Search the web', 'Prompt displayed by rofi.'),
        ('theme', None, 'rofi theme to use.'),
        ('launcher', 'tor-browser --allow-remote {url}', 'Command used to open web '
                     'browser. Requires {url} to place the search url.'),
    ]

    def __init__(self, **config):
        Notifier.__init__(self, **config)
        self.add_defaults(Searx.defaults)
        self.last_used = None

        self.command = ['rofi', '-dmenu', '-l', '0']
        if self.prompt:
            self.command.extend(['-p', self.prompt])
        if self.theme:
            self.command.extend(['-theme', self.theme])

        if self.instances_file:
            self.load_instances()

    def search(self, qtile=None):
        output = subprocess.run(
            self.command,
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        if output.stdout and not output.returncode:
            if self.instances_file:
                instance = random.choice(
                    [i for i in self.instances if not i.startswith('#')]
                )
            else:
                instance = random.choice(self.instances)

            query = output.stdout.strip()
            url = f"'{instance}/?q={query}&categories=general&language=en-US'"
            command = self.launcher.format(url=url)
            subprocess.Popen(shlex.split(command))
            self.last_used = instance

    def remove_last_used(self, qtile=None):
        if self.last_used:
            self.instances.remove(self.last_used)
            if self.instances_file:
                self.instances.append(f'#{self.last_used}')
                self.save_instances()
            self.last_used = None

    def load_instances(self, qtile=None):
        with open(self.instances_file, 'r') as f:
            self.instances = f.read().split()

    def save_instances(self):
        with open(self.instances_file, 'w') as f:
            f.write('\n'.join(self.instances))
