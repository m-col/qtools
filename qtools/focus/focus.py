"""
This plugin exposes four functions - up, down, left and right - that when called will
move window focus to the first window in that general direction. Focussing is based
entirely on position and geometry, so is independent of screens, layouts and whether
windows are floating or tiled.

Example usage: binding a key to lazy.function(qtools.focus.right)
"""


def up(qtile):
    _focus_window(qtile, -1, 'y')


def down(qtile):
    _focus_window(qtile, 1, 'y')


def left(qtile):
    _focus_window(qtile, -1, 'x')


def right(qtile):
    _focus_window(qtile, 1, 'x')


def _focus_window(qtile, dir, axis):
    win = None
    win_wide = None
    dist = 10000
    dist_wide = 10000

    if axis == 'x':
        dim = 'width'
        band_axis = 'y'
        band_dim = 'height'
        cur_pos, band_min, _, band_max = qtile.current_window.edges
    else:
        dim = 'height'
        band_axis = 'x'
        band_dim = 'width'
        band_min, cur_pos, band_max, _ = qtile.current_window.edges

    cur_pos += getattr(qtile.current_window, dim) / 2

    windows = [w for g in qtile.groups if g.screen for w in g.windows]

    if qtile.current_window in windows:
        windows.remove(qtile.current_window)

    for w in windows:
        if not w.minimized:
            pos = getattr(w, axis) + getattr(w, dim) / 2
            gap = dir * (pos - cur_pos)
            if gap > 0:
                band_pos = getattr(w, band_axis) + getattr(w, band_dim) / 2
                if band_min < band_pos < band_max:
                    if gap < dist:
                        dist = gap
                        win = w
                else:
                    if gap < dist_wide:
                        dist_wide = gap
                        win_wide = w

    if not win:
        win = win_wide
    if win:
        qtile.focus_screen(win.group.screen.index)
        win.group.focus(win, True)
        win.focus(False)
