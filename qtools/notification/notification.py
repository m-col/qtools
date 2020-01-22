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


from xcffib.xproto import StackMode

from libqtile import configurable, pangocffi, window
from libqtile.command import lazy
from libqtile.notify import notifier
from libqtile.log_utils import logger
from libqtile.drawer import Drawer


ALIGNMENTS = {
    'left': pangocffi.pango.PANGO_ALIGN_LEFT,
    'center': pangocffi.pango.PANGO_ALIGN_CENTER,
    'right': pangocffi.pango.PANGO_ALIGN_RIGHT,
}


class Popup:
    """
    These represent a single pop-up window. These are (re)cycled, so if we have a
    maximum of two windows visible at once, we keep two of these and re-draw and present
    them.
    """
    def __init__(self, win, drawer, layout):
        self.win = win
        self.drawer = drawer
        self.layout = layout


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
        ('x', 96, 'X position of notifications.'),
        ('y', 96, 'Y position of notifications.'),
        ('width', 256, 'Width of notifications.'),
        ('height', 64, 'Height of notifications.'),
        ('opacity', 1.0, 'Opacity of notifications.'),
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
        ('border_width', 4, 'Line width of drawn borders.'),
        ('corner_radius', None, 'Corner radius for round corners, or None.'),
        ('font', 'sans', 'Font used in notifications.'),
        ('fontsize', 14, 'Size of font.'),
        ('fontshadow', None, 'Color for text shadows, or None for no shadows.'),
        ('padding', None, 'Padding at sides of text.'),
        ('format', '{summary}\n{body}', 'Text format.'),
        ('text_alignment', 'left', 'Text alignment: left, center or right.'),
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
        self._hidden = []
        self._shown = []
        self._queue = []

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
        reorganise some configuration options.
        """
        self.qtile = qtile

        if self.padding is None:
            self.padding = self.fontsize / 2
        if self.border_width:
            self.border = [self.qtile.color_pixel(c) for c in self.border]
        for win in range(self.max_windows):
            self._hidden.append(self._create_window(win))

        notifier.register(self._notify)

    def _create_window(self, win):
        """
        """
        win = window.Internal.create(
            self.qtile,
            self.x,
            self.y + (self.height + self.gap) * win,
            self.width, self.height,
            self.opacity,
        )
        drawer = Drawer(
            self.qtile, win.window.wid, self.width, self.height,
        )
        layout = drawer.textlayout(
            text='',
            colour=self.foreground[1],
            font_family=self.font,
            font_size=self.fontsize,
            font_shadow=self.fontshadow,
            wrap=True if self.overflow == 'extend_y' else False,
            markup=True,
        )
        layout.layout.set_alignment(ALIGNMENTS[self.text_alignment])
        #drawer.clear(self.background[1])  # is this necessary?

        if self.border_width:
            win.window.configure(borderwidth=self.border_width)
        if self.corner_radius:
            win.window.round_corners(
                self.width, self.height, self.corner_radius, self.border_width,
            )

        popup = Popup(win, drawer, layout)
        win.handle_Expose = self._handle_Expose
        win.handle_KeyPress = self._handle_KeyPress
        win.handle_ButtonPress = self._get_popup_ButtonPress(popup)
        self.qtile.windows_map[win.window.wid] = win
        return popup

    def _handle_Expose(self, e):
        pass

    def _handle_KeyPress(self, event):
        pass

    def _get_popup_ButtonPress(self, popup):
        def _inner(event):
            if event.detail == 1:
                self._close(popup)
        return _inner

    def _notify(self, notif):
        """
        This method is registered with the NotificationManager to handle notifications
        received via dbus. They will either be drawn now or queued to be drawn soon.
        """
        if self._hidden:
            self._send(notif, self._hidden.pop(0))
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
        text = self.format.format(summary=summary, body=body)
        urgency = notif.hints.get('urgency', 1)

        popup.drawer.clear(self.background[urgency])
        popup.layout.colour = self.foreground[urgency]
        popup.layout.text = text
        popup.layout.draw(
            self.padding, (popup.win.height - popup.layout.height) / 2,
        )
        if self.border_width:
            popup.win.window.set_attribute(borderpixel=self.border[urgency])
        popup.win.unhide()
        popup.drawer.draw()
        popup.win.window.configure(stackmode=StackMode.Above)

        if notif.timeout is None or notif.timeout < 0:
            timeout = self.timeout[urgency]
        else:
            timeout = notif.timeout
        if timeout > 0:
            self.qtile.call_later(timeout / 1000, self._close, popup)
        self._shown.append(popup)

    def _close(self, popup):
        """
        Close the specified Popup instance.
        """
        if popup in self._shown:
            self._shown.remove(popup)
            if self._queue:
                self._send(self._queue.pop(0), popup)
            else:
                popup.win.hide()
                self._hidden.append(popup)

    def close(self, qtile=None):
        """
        This method can be bound to keys to close the oldest of any visible notification
        windows.
        """
        if self._shown:
            self._close(self._shown[0])

    #def prev(self, qtile=None):
    #    self._notify(notifier.notifications[self._current_id])

    #def next(self, qtile=None):
    #    self._notify(notifier.notifications[self._current_id])
