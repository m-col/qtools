"""
Qtile plugin to control an ALSA device volume level.

Example usage:

    import qtools.amixer
    vol = qtools.amixer.Volume()
    keys.extend([EzKey(k, v) for k, v in {
        '<XF86AudioMute>':        vol.lazy_mute,
        '<XF86AudioRaiseVolume>': vol.lazy_increase,
        '<XF86AudioLowerVolume>': vol.lazy_decrease,
    }.items()])

"""


import subprocess

from libqtile.log_utils import logger
from qtools import Notifier


class Volume(Notifier):
    defaults = [
        ('summary', 'Volume', 'Notification summary.'),
        ('mixer', 'Master', 'ALSA mixer to control.'),
        ('interval', 5, 'Percentage interval to change volume by.'),
    ]
    def __init__(self, **config):
        Notifier.__init__(self, **config)
        self.add_defaults(Volume.defaults)

    def increase(self, qtile=None):
        volume = self._run(f'{self.interval}%+')
        self.show(self.interval * round(volume/self.interval))

    def decrease(self, qtile=None):
        volume = self._run(f'{self.interval}%-')
        self.show(self.interval * round(volume/self.interval))

    def toggle(self, qtile=None):
        volume = self._run('toggle')
        self.show(self.interval * round(volume/self.interval))

    def mute(self, qtile=None):
        self._run('mute')
        self.show('Muted')

    def unmute(self, qtile=None):
        volume = self._run('unmute')
        self.show(volume)

    def _run(self, setting):
        try:
            output = subprocess.run(
                ['amixer', 'set', self.mixer, setting],
                stdout=subprocess.PIPE,
            )
            stdout = output.stdout.splitlines()
        except subprocess.CalledProcessError as err:
            logger.error(err.output.decode())
            return

        if len(stdout) == 5:
            volume = int(stdout[4].decode().split()[3][1:-2])
        elif len(stdout) == 7:
            volume = int(stdout[5].decode().split()[4][1:-2])
        else:
            logger.warning('Output from amixer needs decoding')
        return volume
