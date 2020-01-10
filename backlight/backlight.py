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

        if not os.path.isfile(self.path):
            logger.error('Path passed to Backlight plugin is invalid')
            self.path = '/dev/null'

    @property
    def brightness(self):
        with open(self.path, 'r') as f:
            return int(f.read())

    @brightness.setter
    def brightness(self, value):
        if value > 100:
            value = 100
        elif value < 0:
            value = 0
        elif value % self.interval:
            value = self.interval * round(value / self.interval)

        with open(self.path, 'w') as f:
            f.write(str(value))
        self.show(value)

    def inc_brightness(self, qtile=None):
        self.brightness += self.interval

    def dec_brightness(self, qtile=None):
        self.brightness -= self.interval
