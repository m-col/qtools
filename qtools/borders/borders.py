"""
This plugin can make Qtile draw different patterns on window borders.

Example usage:

    from qtools import borders

    borders.enable('frame')

"""


from libqtile.log_utils import logger
from libqtile.backend.x11 import xcbq

from .cde import cde
from .frame import frame


_style_map = {
    'frame': frame,
    'cde': cde,
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
    style = style.lower()
    if style not in _style_map:
        logger.exception("qtools.borders: style {0} not found.".format(style))
        return

    xcbq.Window.paint_borders = _style_map[style]
    return
