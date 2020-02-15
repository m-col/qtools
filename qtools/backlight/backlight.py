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


class Backlight(Notifier):
    """
    This class controls screen backlight by directly reading and writing to the
    backlight device file in /sys.
    """
    defaults = [
        ('summary', 'Backlight', 'Notification summary.'),
        ('interval', 10, 'Percentage interval by which to change backlight'),
        ('name', '/sys/class/backlight/nv_backlight', 'Full path to backlight device.'),
        ('smooth', True, 'Whether to smoothly change brightness level.'),
        ('transition', 0.04, 'Step size in seconds when smoothly transitioning'),
    ]

    def __init__(self, **config):
        Notifier.__init__(self, **config)
        self.add_defaults(Backlight.defaults)

        if os.path.isdir(self.name):
            self.file = os.path.join(self.name, 'brightness')
            with open(os.path.join(self.name, 'max_brightness'), 'r') as f:
                self.max = int(f.read())

        else:
            logger.error('Path passed to Backlight plugin is invalid')
            self.name = '/dev/null'
            self.max = 100

        self.interval = self.max * self.interval /100
        self.smooth_step = int(self.max / 100)

    def inc_brightness(self, qtile=None):
        self.change(1)

    def dec_brightness(self, qtile=None):
        self.change(-1)

    def change(self, direction):
        start = self.get_brightness()
        end = self.check_value(start + self.interval * direction)
        self.show(int(100 * end / self.max))

        if self.smooth:
            for i in range(
                start + direction,
                end + direction,
                direction * self.smooth_step,
            ):
                with open(self.file, 'w') as f:
                    f.write(str(i))
                time.sleep(self.transition)
                logger.warning('brightness')
        else:
            with open(self.file, 'w') as f:
                f.write(str(end))

    def get_brightness(self):
        with open(self.file, 'r') as f:
            return int(f.read())

    def check_value(self, value):
        if value > self.max:
            value = self.max
        elif value < 0:
            value = 0
        elif value % self.interval:
            value = self.interval * round(value / self.interval)
        return int(value)
