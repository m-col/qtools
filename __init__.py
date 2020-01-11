"""
Simple base classes that can be used for multiple plugins.
"""


import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify

from libqtile.configurable import Configurable
from libqtile.command import lazy


class Notifier(Configurable):
    """
    This is a base class for classes with methods that are to be executed upon key
    presses and that generate pop-up notifications.
    """
    _is_initted = False

    defaults = [
        ('summary', 'Notifier', 'Notification summary.'),
        ('timeout', -1, 'Timeout for notifications.'),
    ]

    def __init__(self, **config):
        if not Notifier._is_initted:
            Notifier._is_initted = True
            Notify.init('Qtile')

        Configurable.__init__(self, **config)
        self.add_defaults(Notifier.defaults)
        self.notifier = Notify.Notification.new(
            config.get('summary', 'Notifier'), ''
        )
        self.timeout = config.get('timeout', -1)

    def __getattr__(self, name):
        """
        Using this, we can get e.g. Mpc.lazy_toggle which is the equivalent of
        lazy.function(Mpc.toggle), which is more convenient for setting keybindings.
        """
        if name.startswith('lazy_'):
            return lazy.function(getattr(self, name[5:]))
        return Configurable.__getattr__(self, name)

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
        self.notifier.show()

    def hide(self):
        self.notifier.hide()
