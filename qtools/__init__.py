"""
Simple base classes that can be used for multiple plugins.
"""


import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify

from xcffib.xproto import StackMode

from libqtile import configurable, pangocffi, window
from libqtile.lazy import lazy
from libqtile.drawer import Drawer


class Notifier(configurable.Configurable):
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

        configurable.Configurable.__init__(self, **config)
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
        self.notifier.show()

    def hide(self):
        self.notifier.hide()


ALIGNMENTS = {
    'left': pangocffi.pango.PANGO_ALIGN_LEFT,
    'center': pangocffi.pango.PANGO_ALIGN_CENTER,
    'right': pangocffi.pango.PANGO_ALIGN_RIGHT,
}


class Popup(configurable.Configurable):
    """
    This base class can be used to create popup windows for a variety of purposes.
    """
    defaults = [
        ('opacity', 1.0, 'Opacity of notifications.'),
        ('foreground', '#ffffff', 'Color of text.'),
        ('background', '#111111', 'Background color.'),
        ('border', '#111111', 'Border color.'),
        ('border_width', 4, 'Line width of drawn borders.'),
        ('corner_radius', None, 'Corner radius for round corners, or None.'),
        ('font', 'sans', 'Font used in notifications.'),
        ('fontsize', 14, 'Size of font.'),
        ('fontshadow', None, 'Color for text shadows, or None for no shadows.'),
        ('padding', None, 'Padding at sides of text.'),
        ('text_alignment', 'left', 'Text alignment: left, center or right.'),
    ]

    def __init__(self, qtile, x=50, y=50, width=256, height=64, **config):
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(Popup.defaults)
        self.qtile = qtile

        win = qtile.conn.create_window(x, y, width, height)
        win.set_property("QTILE_INTERNAL", 1)
        self.win = window.Internal(win, qtile)
        self.win.opacity = self.opacity
        self.drawer = Drawer(
            self.qtile, self.win.window.wid, width, height,
        )
        self.layout = self.drawer.textlayout(
            text='',
            colour=self.foreground,
            font_family=self.font,
            font_size=self.fontsize,
            font_shadow=self.fontshadow,
            wrap=True,
            markup=True,
        )
        self.layout.layout.set_alignment(ALIGNMENTS[self.text_alignment])

        if self.border_width:
            self.win.window.configure(borderwidth=self.border_width)
        if self.corner_radius:
            self.win.window.round_corners(
                width, height, self.corner_radius, self.border_width,
            )

        self.win.handle_Expose = self._handle_Expose
        self.win.handle_KeyPress = self._handle_KeyPress
        self.win.handle_ButtonPress = self._handle_ButtonPress
        self.qtile.windows_map[self.win.window.wid] = self.win

        self.x = self.win.x
        self.y = self.win.y
        self.width = self.win.width
        self.height = self.win.height

    def _handle_Expose(self, e):
        pass

    def _handle_KeyPress(self, event):
        pass

    def _handle_ButtonPress(self, event):
        if event.detail == 1:
            self.hide()

    @property
    def text(self):
        return self.layout.text

    @text.setter
    def text(self, value):
        self.layout.text = value

    @property
    def foreground(self):
        return self._foreground

    @foreground.setter
    def foreground(self, value):
        self._foreground = value
        if hasattr(self, 'layout'):
            self.layout.colour = value

    def set_border(self, color):
        self.win.window.set_attribute(borderpixel=color)

    def clear(self):
        self.drawer.clear(self.background)

    def draw_text(self):
        self.layout.draw(
            self.padding,
            (self.win.height - self.layout.height) / 2,
        )

    def draw_window(self):
        self.drawer.draw()

    def place(self):
        self.win.place(
            self.x, self.y, self.width, self.height,
            self.border_width, self.border, above=True
        )

    def unhide(self):
        self.win.unhide()
        self.win.window.configure(stackmode=StackMode.Above)

    def hide(self):
        self.win.hide()

    def kill(self):
        self.win.kill()
