"""
Simple base classes that can be used for multiple plugins.
"""


import os
from random import randint

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
gi.require_version('Notify', '0.7')
from gi.repository import Notify

from xcffib.xproto import StackMode
from libqtile.drawer import Drawer
from libqtile.lazy import lazy
from libqtile.log_utils import logger
from libqtile import configurable, pangocffi, window


class Notifier(configurable.Configurable):
    """
    This is a base class for classes with methods that are to be executed upon key
    presses and that generate pop-up notifications.
    """
    _is_initted = False

    defaults = [
        ('summary', 'Notifier', 'Notification summary.'),
        ('timeout', -1, 'Timeout for notifications.'),
        ('sound', None, 'Sound to make when sending notification'),
    ]

    def __init__(self, **config):
        if not Notifier._is_initted:
            Notifier._is_initted = True
            Notify.init('Qtile')

        configurable.Configurable.__init__(self, **config)
        self.add_defaults(Notifier.defaults)
        self.notifier = Notify.Notification.new(
            config.get('summary', 'Notifier'), ''
        )
        self.timeout = config.get('timeout', -1)
        self.id = randint(10, 1000)

        if self.sound is not None:
            self.sound = os.path.expanduser(self.sound)

    def __getattr__(self, name):
        """
        Using this, we can get e.g. Mpc.lazy_toggle which is the equivalent of
        lazy.function(Mpc.toggle), which is more convenient for setting keybindings.
        """
        if name.startswith('lazy_'):
            return lazy.function(getattr(self, name[5:]))
        return configurable.Configurable.__getattr__(self, name)

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        self.notifier.set_timeout(value)
        self._timeout = value

    def show(self, body):
        if not isinstance(body, str):
            body = str(body)
        self.notifier.update(self.summary, body)
        if hasattr(self, 'id'):
            self.notifier.set_property('id', self.id)
        self.notifier.show()
        if self.sound is not None:
            play_sound(self.sound)

    def hide(self):
        self.notifier.hide()


Gst.init(None)

def play_sound(path):
    """
    Play an audio file. This accepts a full path to an audio file. This is mostly a
    snippet from the playsound library.
    """
    playbin = Gst.ElementFactory.make('playbin', 'playbin')
    playbin.props.uri = 'file://' + path

    set_result = playbin.set_state(Gst.State.PLAYING)
    if set_result == Gst.StateChangeReturn.ASYNC:
        bus = playbin.get_bus()
        bus.poll(Gst.MessageType.EOS, Gst.CLOCK_TIME_NONE)
        playbin.set_state(Gst.State.NULL)
    else:
        logger.exception("qtools.play_sound failed with file: {0}".format(path))
