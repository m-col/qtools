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
        - CDE

    Parameters
    ----------
    style : str
        A string specifying which style to use.

    """
    style = style.lower()
    if style in _style_map:
        xcbq.Window.paint_borders = _style_map[style]
    else:
        logger.exception("qtools.borders: style {} not found.".format(style))
