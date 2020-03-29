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
        ('horizontal_padding', 0, 'Padding at sides of text.'),
        ('vertical_padding', 0, 'Padding at top and bottom of text.'),
        ('text_alignment', 'left', 'Text alignment: left, center or right.'),
        ('wrap', True, 'Whether to wrap text.'),
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
            wrap=self.wrap,
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
        if not self.border_width:
            self.border = None

    def _handle_Expose(self, e):
        pass

    def _handle_KeyPress(self, event):
        pass

    def _handle_ButtonPress(self, event):
        if event.detail == 1:
            self.hide()

    @property
    def width(self):
        return self.win.width

    @width.setter
    def width(self, value):
        self.win.width = value
        self.drawer.width = value

    @property
    def height(self):
        return self.win.height

    @height.setter
    def height(self, value):
        self.win.height = value
        self.drawer.height = value

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

    def draw_text(self, x=None, y=None):
        self.layout.draw(
            x or self.horizontal_padding,
            y or self.vertical_padding,
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

    def draw_image(self, image, x, y):
        """
        Paint an image onto the window at point x, y. The image should be a surface e.g.
        loaded from libqtile.images.Img.load_path.
        """
        self.drawer.ctx.set_source_surface(image, x, y)
        self.drawer.ctx.paint()

    def hide(self):
        self.win.hide()

    def kill(self):
        self.win.kill()
