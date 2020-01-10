"""
Qtile plugin to control the screen backlight.

Example usage:

    import qtools.backlight
    backlight = qtools.backlight.Backlight()
    keys.extend([EzKey(k, v) for k, v in {
        '<XF86MonBrightnessUp>':    backlight.lazy_inc_brightness,
        '<XF86MonBrightnessDown>':  backlight.lazy_dec_brightness,
    }.items()])

"""

import os

from libqtile.log_utils import logger
from qtools import Notifier


class Backlight(Notifier):

    defaults = [
        ('summary', 'Backlight', 'Notification summary.'),
        ('interval', 10, 'Percentage interval by which to change backlight'),
        (
            'path',
            '/sys/class/backlight/nv_backlight/brightness',
            'Full path to backlight device.'
        ),
    ]

    def __init__(self, **config):
        Notifier.__init__(self, **config)
        self.add_defaults(Backlight.defaults)

        if os.path.isfile(self.path):
            self.brightness = self.read()
        else:
            logger.error('Path passed to Backlight plugin is invalid')
            self.path = '/dev/null'
            self.brightness = 0

    def read(self):
        with open(self.path, 'r') as f:
            return int(f.read())

    def write(self, string):
        with open(self.path, 'w') as f:
            f.write(string)
        self.update(string)
        self.show()

    def inc_brightness(self, qtile=None):
        self.brightness = min(self.brightness + self.interval, 100)
        self.write(str(self.brightness))

    def dec_brightness(self, qtile=None):
        self.brightness = max(self.brightness - self.interval, 0)
        self.write(str(self.brightness))
