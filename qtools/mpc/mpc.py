"""
Qtile plugin to control Music Player Daemon using musicpd or mpd2 library

Example usage:

    import qtools.mpc
    mpc = qtools.mpc.Client()
    keys.extend([EzKey(k, v) for k, v in {
        '<XF86AudioPlay>':  mpc.lazy_toggle,
        '<XF86AudioNext>':  mpc.lazy_next,
        '<XF86AudioPrev>':  mpc.lazy_previous,
        '<XF86AudioPlay>':  mpc.lazy_stop,
    }.items()])

"""

from functools import wraps

try:
    from musicpd import ConnectionError, MPDClient
except ImportError:
    from mpd import ConnectionError, MPDClient
from qtools import Notifier


def _client_func(func):
    @wraps(func)
    def _inner(self, qtile):
        try:
            self.client.connect()
        except ConnectionError:
            pass
        self.show(func(self))
        self.client.disconnect()
    return _inner


class Client(Notifier):
    """
    The host and port are 127.0.0.1 and 6600 by default but can be set by passing these
    when initiating the client.

    The notification timeout can be changed by setting Client.timeout to milliseconds
    (int) or -1, which then uses the notification server's default timeout.
    """
    defaults = [
        ('summary', 'Music', 'Notification summary.'),
        ('host', '127.0.0.1', 'IP address of MPD server.'),
        ('port', '6600', 'Port of MPD server.'),
    ]
    def __init__(self, **config):
        Notifier.__init__(self, **config)
        self.add_defaults(Client.defaults)

        self.client = MPDClient()
        self.client.host = self.host
        self.client.port = self.port

    @_client_func
    def toggle(self):
        if self.client.status()['state'] == 'play':
            self.client.pause()
            return 'Paused'
        else:
            self.client.play()
            return 'Playing'

    @_client_func
    def next(self):
        self.client.next()
        current = self.client.currentsong()
        return f"{current['artist']} - {current['title']}"

    @_client_func
    def previous(self):
        self.client.previous()
        current = self.client.currentsong()
        return f"{current['artist']} - {current['title']}"

    @_client_func
    def stop(self):
        self.client.stop()
        return 'Stopped'
