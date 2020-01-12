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
import time

from libqtile.log_utils import logger
from qtools import Notifier


_transition = 80


class Backlight(Notifier):
    """
    This class controls screen backlight by directly reading and writing to the
    backlight device file in /sys.
    """
    defaults = [
        ('summary', 'Backlight', 'Notification summary.'),
        ('interval', 10, 'Percentage interval by which to change backlight'),
        ('smooth', True, 'Whether to smoothly change brightness level.'),
        (
            'path',
            '/sys/class/backlight/nv_backlight/brightness',
            'Full path to backlight device.'
        ),
    ]

    def __init__(self, **config):
        Notifier.__init__(self, **config)
        self.add_defaults(Backlight.defaults)
        self.transition = _transition / self.interval / 1000

        if not os.path.isfile(self.path):
            logger.error('Path passed to Backlight plugin is invalid')
            self.path = '/dev/null'

    def inc_brightness(self, qtile=None):
        self.change(1)

    def dec_brightness(self, qtile=None):
        self.change(-1)

    def change(self, direction):
        start = self.get_brightness()
        end = self.check_value(start + self.interval * direction)
        self.show(end)

        if self.smooth:
            for i in range(
                start + direction,
                end + direction,
                direction
            ):
                with open(self.path, 'w') as f:
                    f.write(str(i))
                time.sleep(self.transition)
        else:
            with open(self.path, 'w') as f:
                f.write(str(end))

    def get_brightness(self):
        with open(self.path, 'r') as f:
            return int(f.read())

    def check_value(self, value):
        if value > 100:
            value = 100
        elif value < 0:
            value = 0
        elif value % self.interval:
            value = self.interval * round(value / self.interval)
        return value
