"""
Qtile plugin that acts as a notification server and draws notification windows.

Example usage:

    import qtools.notification
    notifier = qtools.notification.Server()
    keys.extend([EzKey(k, v) for k, v in {
        'M-<grave>':    notifier.lazy_prev,
        'M-S-<grave>':  notifier.lazy_next,
        'C-<space>':    notifier.lazy_close,
    }.items()])

"""


from libqtile import configurable, pangocffi, window
from libqtile.lazy import lazy
from libqtile.notify import notifier
from libqtile.drawer import Drawer
from libqtile.log_utils import logger

from qtools import Popup


class Server(configurable.Configurable):
    """
    Foreground and background colours can be specified either as tuples/lists of 3
    strings, corresponding to low, normal and critical urgencies, or just a single
    string which will then be used for all urgencies. The timeout and border options can
    be set in the same way.

    TODO:
        - overflow
        - spacing between lines
        - replace_id
    """
    defaults = [
        ('format', '{summary}\n{body}', 'Text format.'),
        ('opacity', 1.0, 'Opacity of notifications.'),
        ('border_width', 4, 'Line width of drawn borders.'),
        ('corner_radius', None, 'Corner radius for round corners, or None.'),
        ('font', 'sans', 'Font used in notifications.'),
        ('fontsize', 14, 'Size of font.'),
        ('fontshadow', None, 'Color for text shadows, or None for no shadows.'),
        ('padding', None, 'Padding at sides of text.'),
        ('text_alignment', 'left', 'Text alignment: left, center or right.'),
        (
            'foreground',
            ('#ffffff', '#ffffff', '#ffffff'),
            'Foreground colour of notifications, in ascending order of urgency.',
        ),
        (
            'background',
            ('#111111', '#111111', '#111111'),
            'Background colour of notifications, in ascending order of urgency.',
        ),
        (
            'border',
            ('#111111', '#111111', '#111111'),
            'Border colours in ascending order of urgency. Or None for none.',
        ),
        (
            'timeout',
            (5000, 5000, 0),
            'Millisecond timeout duration, in ascending order of urgency.',
        ),
        (
            'overflow',
            'trim',
            'How to deal with too much text: extend_x, extend_y or trim.',
        ),
        ('max_windows', 2, 'Maximum number of windows to show at once.'),
        ('gap', 18, 'Vertical gap between popup windows.'),
    ]

    def __init__(self, **config):
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(Server.defaults)
        self.qtile = None
        self._popups = []
        self._hidden = []
        self._shown = []
        self._queue = []
        self._positions = []

        self._make_attr_list('foreground')
        self._make_attr_list('background')
        self._make_attr_list('timeout')
        self._make_attr_list('border')

    def __getattr__(self, name):
        """
        Using this, we can get e.g. Server.lazy_close which is the equivalent of
        lazy.function(Server.close) but more convenient for setting keybindings.
        """
        if name.startswith('lazy_'):
            return lazy.function(getattr(self, name[5:]))
        return configurable.Configurable.__getattr__(self, name)

    def _make_attr_list(self, attr):
        """
        Turns '#000000' into ('#000000', '#000000', '#000000')
        """
        value = getattr(self, attr)
        if not isinstance(value, (tuple, list)):
            setattr(self, attr, (value,) * 3)

    def configure(self, qtile):
        """
        This method needs to be called to set up the Server with the Qtile manager and
        create the required popup windows.
        """
        self.qtile = qtile

        if self.padding is None:
            self.padding = self.fontsize / 2
        if self.border_width:
            self.border = [self.qtile.color_pixel(c) for c in self.border]

        self._popup_config = {}
        for opt in Popup.defaults:
            key = opt[0]
            if hasattr(self, key):
                value = getattr(self, key)
                if isinstance(value, (tuple, list)):
                    self._popup_config[key] = value[1]
                else:
                    self._popup_config[key] = value

        for win in range(self.max_windows):
            popup = Popup(self.qtile, **self._popup_config)
            self._popups.append(popup)
            self._hidden.append(popup)
            self._positions.append(
                (self.x, self.y + win * (self.height + self.border_width * 3 + self.gap))
            )

        notifier.register(self._notify)

    def _notify(self, notif):
        """
        This method is registered with the NotificationManager to handle notifications
        received via dbus. They will either be drawn now or queued to be drawn soon.
        """
        if self._hidden:
            self._send(notif, self._hidden.pop())
        else:
            self._queue.append(notif)

    def _send(self, notif, popup):
        """
        Draw the desired notification using the specified Popup instance.
        """
        summary = None
        body = None
        if notif.summary:
            summary = pangocffi.markup_escape_text(notif.summary)
        if notif.body:
            body = pangocffi.markup_escape_text(notif.body)
        urgency = notif.hints.get('urgency', 1)

        popup.x, popup.y = self._positions[len(self._shown)]
        popup.background = self.background[urgency]
        popup.foreground = self.foreground[urgency]
        popup.text = self.format.format(summary=summary, body=body)
        popup.clear()
        popup.draw_text()
        if self.border_width:
            popup.set_border(self.border[urgency])
        popup.place()
        popup.unhide()
        popup.draw_window()
        popup.id = notif.id

        if notif.timeout is None or notif.timeout < 0:
            timeout = self.timeout[urgency]
        else:
            timeout = notif.timeout
        if timeout > 0:
            self.qtile.call_later(timeout / 1000, self._close, popup, notif.id)
        self._shown.append(popup)

    def _close(self, popup, nid=None):
        """
        Close the specified Popup instance.
        """
        if popup in self._shown:
            self._shown.remove(popup)
            if nid is not None and popup.id != nid:
                return
            popup.hide()
            if self._queue:
                self._send(self._queue.pop(0), popup)
            else:
                self._hidden.append(popup)

        for index, shown in enumerate(self._shown):
            shown.x, shown.y = self._positions[index]
            shown.place()

    def close(self, qtile=None):
        """
        Close the oldest of all visible popup windows.
        """
        if self._shown:
            self._close(self._shown[0])

    def close_all(self, qtile=None):
        """
        Close all popup windows.
        """
        self._queue.clear()
        for popup in self._shown:
            self._close(popup)

    #def prev(self, qtile=None):
    #    self._notify(notifier.notifications[self._current_id])

    #def next(self, qtile=None):
    #    self._notify(notifier.notifications[self._current_id])
