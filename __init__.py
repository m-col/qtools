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

        Configurable.__init__(self)
        self.add_defaults(Notifier.defaults)
        self._notifier = None

    def __getattr__(self, name):
        """
        Using this, we can get e.g. Mpc.lazy_toggle which is the equivalent of
        lazy.function(Mpc.toggle), which is more convenient for setting keybindings.
        """
        if name.startswith('lazy_'):
            return lazy.function(getattr(self, name[5:]))
        return Configurable.__getattr__(self, name)

    @property
    def notifier(self):
        if self._notifier is None:
            self._notifier = Notify.Notification.new(self.summary, '')
            self._notifier.set_timeout(self.timeout)
        return self._notifier

    def set_timeout(self, timeout):
        self.notifier.set_timeout(timeout)
        self.timeout = timeout

    def show(self):
        self.notifier.show()

    def hide(self):
        self.notifier.hide()

    def update(self, body):
        self.notifier.update(self.summary, body)
