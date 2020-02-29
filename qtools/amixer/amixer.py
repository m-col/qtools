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
    """
    This Notifier can be used to control ALSA mixer volume and muting, sending
    notifications when operations are performed.

    The 'mixer' option should be set to the name of the ALSA mixer you use to control
    the volume. By default this will also be used for mute/unmute operations.
    Alternatively, if you use the Master mixer for muting instead of the mixer used for
    volume control, set 'mute_master' to true.
    """
    defaults = [
        ('summary', 'Volume', 'Notification summary.'),
        ('mixer', 'Master', 'ALSA mixer to control.'),
        ('interval', 5, 'Percentage interval to change volume by.'),
        ('mute_master', False, 'Use the Master mixer for mute operations'),
    ]

    def __init__(self, **config):
        Notifier.__init__(self, **config)
        self.add_defaults(Volume.defaults)
        if self.mute_master and self.mixer == 'Master':
            self.mute_master = False

    def increase(self, qtile=None):
        stdout = _run(['set', self.mixer, f'{self.interval}%+'])
        volume = _get_volume(stdout)
        self.show(self.interval * round(volume / self.interval))

    def decrease(self, qtile=None):
        stdout = _run(['set', self.mixer, f'{self.interval}%-'])
        volume = _get_volume(stdout)
        self.show(self.interval * round(volume / self.interval))

    def toggle(self, qtile=None):
        stdout = _run(
            ['set', 'Master' if self.mute_master else self.mixer, 'toggle']
        )
        if _get_mute(stdout):
            self.show('Muted')
        else:
            if self.mute_master:
                stdout = _run(['get', self.mixer])
            volume = _get_volume(stdout)
            self.show(self.interval * round(volume / self.interval))

    def mute(self, qtile=None):
        _run(['set', 'Master' if self.mute_master else self.mixer, 'mute'])
        self.show('Muted')

    def unmute(self, qtile=None):
        _run(['set', 'Master' if self.mute_master else self.mixer, 'unmute'])
        volume = _get_volume(_run(['get', self.mixer]))
        self.show(self.interval * round(volume / self.interval))


def _get_mute(stdout):
    if len(stdout) == 5:
        if stdout[4].decode().split()[5][1:-1] == 'on':
            muted = False
        else:
            muted = True
    else:
        muted = False
        logger.warning('Output from amixer needs decoding')
    return muted

def _get_volume(stdout):
    if (stdlen:=len(stdout)) == 5:
        vol = int(stdout[4].decode().split()[3][1:-2])
    elif stdlen == 7:
        vol = int(stdout[5].decode().split()[4][1:-2])
    else:
        logger.warning('Output from amixer needs decoding')
        vol = 0
    return vol

def _run(args):
    cmd = ['amixer']
    cmd.extend(args)
    try:
        output = subprocess.run(cmd, stdout=subprocess.PIPE, check=False)
    except subprocess.CalledProcessError as err:
        logger.error(err.output.decode())
        return ''
    return output.stdout.splitlines()
