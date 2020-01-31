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


from libqtile import configurable, hook, images, pangocffi, window
from libqtile.lazy import lazy
from libqtile.notify import notifier
from libqtile.drawer import Drawer
from libqtile.log_utils import logger

from qtools import Popup


class Server(configurable.Configurable):
    """
    This class provides a full graphical notification manager for the
    org.freedesktop.Notifications service implemented in libqtile.notify.

    Hints can be provided by notification clients to modify behaviour:
        hint    behaviour

    The format option determines what text is shown on the popup windows, and supports
    markup and new line characters e.g. '<b>{summary}</b>\n{body}'. Available
    placeholders are summary, body and app_name.

    Foreground and background colours can be specified either as tuples/lists of 3
    strings, corresponding to low, normal and critical urgencies, or just a single
    string which will then be used for all urgencies. The timeout and border options can
    be set in the same way.

    The max_windows option limits how many popup windows can be drawn at a time. When
    more notifications are recieved while the maximum number are already drawn,
    notifications are queued and displayed when existing notifications are closed.

    TODO:
        - overflow
        - select screen / follow mouse/keyboard focus
        - critical notifications to replace any visible non-critical notifs immediately?
        - icons position (left/right/None)
        - hints: image-path, desktop-entry (for icon)
        - hints: Server parameters set for single notification?
        - hints: progress value e.g. int:value:42 with drawing

    """
    defaults = [
        ('format', '{summary}\n{body}', 'Text format.'),
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
        ('opacity', 1.0, 'Opacity of notifications.'),
        ('border_width', 4, 'Line width of drawn borders.'),
        ('corner_radius', None, 'Corner radius for round corners, or None.'),
        ('font', 'sans', 'Font used in notifications.'),
        ('fontsize', 14, 'Size of font.'),
        ('fontshadow', None, 'Color for text shadows, or None for no shadows.'),
        ('text_alignment', 'left', 'Text alignment: left, center or right.'),
        ('horizonal_padding', None, 'Padding at sides of text.'),
        ('vertical_padding', None, 'Padding at top and bottom of text.'),
        ('line_spacing', 4, 'Space between lines.'),
        (
            'overflow',
            'truncate',
            'How to deal with too much text: more_width, more_height, or truncate.',
        ),
        ('max_windows', 2, 'Maximum number of windows to show at once.'),
        ('gap', 12, 'Vertical gap between popup windows.'),
        ('sticky_history', True, 'Disable timeout when browsing history.'),
        ('icon_size', 36, 'Pixel size of any icons.'),
        ('fullscreen', 'show', 'What to do when in fullscreen: show, hide, or queue.'),
    ]
    capabilities = {'body', 'body-markup'}
    # specification: https://developer.gnome.org/notification-spec/

    def __init__(self, **config):
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(Server.defaults)
        self.qtile = None
        self._hidden = []
        self._shown = []
        self._queue = []
        self._positions = []
        self._scroll_popup = None
        self._current_id = 0
        self._notif_id = None
        self._paused = False
        self._icons = {}

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

        if self.horizontal_padding is None:
            self.horizontal_padding = self.fontsize / 2
        if self.vertical_padding is None:
            self.vertical_padding = self.fontsize / 2
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
            popup.win.handle_ButtonPress = self._buttonpress(popup)
            popup.replaces_id = None
            self._hidden.append(popup)
            self._positions.append(
                (self.x, self.y + win * (self.height + 2 * self.border_width +
                 self.gap))
            )

        notifier.register(self._notify, Server.capabilities)

    def _buttonpress(self, popup):
        def _(event):
            if event.detail == 1:
                self._close(popup)
        return _

    def _notify(self, notif):
        """
        This method is registered with the NotificationManager to handle notifications
        received via dbus. They will either be drawn now or queued to be drawn soon.
        """
        if self._paused:
            self._queue.append(notif)
            return

        if self.qtile.current_window.fullscreen and self.fullscreen != 'show':
            if self.fullscreen == 'queue':
                if self._unfullscreen not in hook.subscriptions:
                    hook.subscribe.float_change(self._unfullscreen)
                self._queue.append(notif)
            return

        if notif.replaces_id:
            for popup in self._shown:
                if notif.replaces_id == popup.replaces_id:
                    self._shown.remove(popup)
                    self._send(notif, popup)
                    self._reposition()
                    return

        if self._hidden:
            self._send(notif, self._hidden.pop())
        else:
            self._queue.append(notif)

    def _unfullscreen(self):
        """
        Begin displaying of queue notifications after leaving fullscreen.
        """
        if not self.qtile.current_window.fullscreen:
            hook.unsubscribe.float_change(self._unfullscreen)
            self._renotify()

    def _renotify(self):
        """
        If we hold off temporarily on sending notifications and accumulate a queue, we
        should use this to the queue through self._notify again.
        """
        queue = self._queue.copy()
        self._queue.clear()
        while queue:
            self._notify(queue.pop(0))

    def _send(self, notif, popup, timeout=None):
        """
        Draw the desired notification using the specified Popup instance.
        """
        text = self._get_text(notif)
        urgency = notif.hints.get('urgency', 1)
        self._current_id += 1
        popup.id = self._current_id
        if popup not in self._shown:
            self._shown.append(popup)
        popup.x, popup.y = self._positions[len(self._shown) - 1]
        icon = self._load_icon(notif)

        popup.background = self.background[urgency]
        popup.foreground = self.foreground[urgency]
        popup.clear()

        if icon:
            popup.draw_image(
                icon[0],
                self.horizontal_padding,
                1 + (self.height - icon[1]) / 2,
            )
            popup.horizontal_padding += self.icon_size + self.horizontal_padding / 2

        for num, line in enumerate(text.split('\n')):
            popup.text = line
            y = self.vertical_padding + num * (popup.layout.height + self.line_spacing)
            popup.draw_text(y=y)
        if self.border_width:
            popup.set_border(self.border[urgency])
        popup.place()
        popup.unhide()
        popup.draw_window()
        popup.replaces_id = notif.replaces_id
        if icon:
            popup.horizontal_padding = self.horizontal_padding

        if timeout is None:
            if notif.timeout is None or notif.timeout < 0:
                timeout = self.timeout[urgency]
            else:
                timeout = notif.timeout
        elif timeout < 0:
            timeout = self.timeout[urgency]
        if timeout > 0:
            self.qtile.call_later(
                timeout / 1000, self._close, popup, self._current_id
            )

    def _get_text(self, notif):
        summary = ''
        body = ''
        app_name = ''
        if notif.summary:
            summary = pangocffi.markup_escape_text(notif.summary)
        if notif.body:
            body = pangocffi.markup_escape_text(notif.body)
        if notif.app_name:
            app_name = pangocffi.markup_escape_text(notif.app_name)
        return self.format.format(summary=summary, body=body, app_name=app_name)

    def _close(self, popup, nid=None):
        """
        Close the specified Popup instance.
        """
        if popup in self._shown:
            if nid is not None and popup.id != nid:
                return
            self._shown.remove(popup)
            if self._scroll_popup is popup:
                self._scroll_popup = None
                self._notif_id = None
            popup.hide()
            if self._queue and not self._paused:
                self._send(self._queue.pop(0), popup)
            else:
                self._hidden.append(popup)
        self._reposition()

    def _reposition(self):
        for index, shown in enumerate(self._shown):
            shown.x, shown.y = self._positions[index]
            shown.place()

    def _load_icon(self, notif):
        if notif.app_icon:
            if notif.app_icon in self._icons:
                return self._icons.get(notif.app_icon)
            else:
                img = images.Img.from_path(notif.app_icon)
                if img.width > img.height:
                    img.resize(width=self.icon_size)
                else:
                    img.resize(height=self.icon_size)
                self._icons[notif.app_icon] = _decode_image(
                    img.bytes_img, img.width, img.height
                )
                return self._icons[notif.app_icon]
        else:
            return None

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
        while self._shown:
            self._close(self._shown[0])

    def prev(self, qtile=None):
        """
        Display the previous notification in the history.
        """
        if notifier.notifications:
            if self._scroll_popup is None:
                if self._hidden:
                    self._scroll_popup = self._hidden.pop(0)
                else:
                    self._scroll_popup = self._shown[0]
                self._notif_id = len(notifier.notifications)
            if self._notif_id > 0:
                self._notif_id -= 1
            self._send(
                notifier.notifications[self._notif_id],
                self._scroll_popup,
                0 if self.sticky_history else None,
            )

    def next(self, qtile=None):
        """
        Display the next notification in the history.
        """
        if self._scroll_popup:
            if self._notif_id < len(notifier.notifications) - 1:
                self._notif_id += 1
            if self._scroll_popup in self._shown:
                self._shown.remove(self._scroll_popup)
            self._send(
                notifier.notifications[self._notif_id],
                self._scroll_popup,
                0 if self.sticky_history else None,
            )

    def pause(self, qtile=None):
        """
        Pause display of notifications on screen. Notifications will be queued and
        presented as usual when this is called again.
        """
        if self._paused:
            self._paused = False
            self._renotify()
        else:
            self._paused = True
            while self._shown:
                self._close(self._shown[0])

def _decode_image(bytes_img, width, height):
    try:
        surface, _ = images._decode_to_image_surface(bytes_img, width, height)
        return surface, surface.get_height()
    except Exception as e:
        logger.exception(f'Could not load notification icon')
        return None
