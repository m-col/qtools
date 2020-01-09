"""
Qtile plugin to control Music Player Daemon using musicpd or mpd2 library

Example usage:

    import qtools.mpc as mpc
    mpc_client = mpc.Client()
    keys.extend([EzKey(k, v) for k, v in {
        '<XF86AudioPlay>':  lazy.function(mpc_local.toggle),
        '<XF86AudioNext>':  lazy.function(mpc_local.next),
        '<XF86AudioPrev>':  lazy.function(mpc_local.previous),
        '<XF86AudioPlay>':  lazy.function(mpc_local.stop),
    }.items()])

"""


try:
    from musicpd import ConnectionError, MPDClient
except ImportError:
    from mpd import ConnectionError, MPDClient

import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify


Notify.init('Music')


def _wrap(func):
    def _inner(self, qtile):
        try:
            self.client.connect()
        except ConnectionError:
            pass
        self.notifier.update('Music', func(self))
        self.notifier.show()
        self.client.disconnect()
    return _inner


class Client:
    """
    The host and port are 127.0.0.1 and 6600 by default but can be set by passing these
    when initiating the client.

    The notification timeout can be changed by setting Client.timeout to milliseconds
    (int) or -1, which then uses the notification server's default timeout.
    """
    def __init__(self, host='127.0.0.1', port='6600'):
        self.client = MPDClient()
        self.client.host = host
        self.client.port = port
        self.notifier = Notify.Notification.new('Music', 'body')
        self._timeout = -1
        self.notifier.set_timeout(self._timeout)

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        self.notifier.set_timeout(timeout)
        self._timeout = timeout

    @_wrap
    def toggle(self):
        if self.client.status()['state'] == 'play':
            self.client.pause()
            return 'Paused'
        else:
            self.client.play()
            return 'Playing'

    @_wrap
    def next(self):
        self.client.next()
        current = self.client.currentsong()
        return f"{current['artist']} - {current['title']}"

    @_wrap
    def previous(self):
        self.client.previous()
        current = self.client.currentsong()
        return f"{current['artist']} - {current['title']}"

    @_wrap
    def stop(self):
        self.client.stop()
        return 'Stopped'
