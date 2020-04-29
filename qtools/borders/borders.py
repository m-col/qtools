"""
This plugin can make Qtile draw different patterns on window borders.

Example usage:

    from qtools import borders

    borders.enable('frame')

"""


import functools
import xcffib

from libqtile.log_utils import logger
from libqtile.backend.x11 import xcbq


def _frame(self, inner_w, inner_h, borderwidths, bordercolors):
    """
    The "frame" style accepts one border width and two colours.

    The first colour is the sides and the second is top and bottom.
      _________
     |\_______/|
     ||       ||
     ||       ||
     ||       ||
     ||_______||
     |/_______\|

    """
    if len(bordercolors) == 1:
        self.set_attribute(borderpixel=bordercolors[0])
        return

    core = self.conn.conn.core
    self.borderwidth = sum(borderwidths)
    outer_w = inner_w + self.borderwidth * 2
    outer_h = inner_h + self.borderwidth * 2

    pixmap = self.conn.conn.generate_id()
    core.CreatePixmap(
        self.conn.default_screen.root_depth, pixmap, self.wid, outer_w, outer_h
    )
    gc = self.conn.conn.generate_id()
    core.CreateGC(gc, pixmap, xcffib.xproto.GC.Foreground, [bordercolors[0]])
    rect = xcffib.xproto.RECTANGLE.synthetic(0, 0, outer_w, outer_h)
    core.PolyFillRectangle(pixmap, gc, 1, [rect])

    core.ChangeGC(gc, xcffib.xproto.GC.Foreground, [bordercolors[1]])
    core.FillPoly(
        pixmap, gc, 2, 0, 4, _frame_trapezium_top(self.borderwidth, outer_w)
    )
    core.FillPoly(
        pixmap, gc, 2, 0, 4, _frame_trapezium_bottom(self.borderwidth, outer_w, outer_h)
    )

    self.set_borderpixmap(pixmap, gc, outer_w, outer_h)
    core.FreePixmap(pixmap)
    core.FreeGC(gc)
    return

@functools.lru_cache()
def _frame_trapezium_top(borderwidth, width):
    points = [
        xcffib.xproto.POINT.synthetic(0, 0),
        xcffib.xproto.POINT.synthetic(borderwidth, borderwidth),
        xcffib.xproto.POINT.synthetic(width - borderwidth, borderwidth),
        xcffib.xproto.POINT.synthetic(width, 0),
    ]
    return points

@functools.lru_cache()
def _frame_trapezium_bottom(borderwidth, width, bottom):
    points = [
        xcffib.xproto.POINT.synthetic(0, bottom),
        xcffib.xproto.POINT.synthetic(borderwidth, bottom - borderwidth),
        xcffib.xproto.POINT.synthetic(width - borderwidth, bottom - borderwidth),
        xcffib.xproto.POINT.synthetic(width, bottom),
    ]
    return points



_style_map = {
    'frame': _frame,
}


def enable(style):
    """
    Enable a particular style of window borders.

    Available styles:

        - frame

    Parameters
    ----------
    style : str
        A string specifying which style to use.

    """
    if style not in _style_map:
        logger.exception("qtools.borders: style {0} not found.".format(style))
        return

    xcbq.Window.paint_borders = _style_map[style]
    return
