"""
Qtile helper to get X resources from the root window.
"""


import xcffib
import xcffib.xproto


def get(DISPLAY, defaults={}):
    """
    Get the X resources in an X servers resource manager.

    Parameters
    ==========
    DISPLAY : str
        DISPLAY name to query.
    
    defaults : dict (optional)
        Default values to act as a fallback for missing values or in the event of a
        failed connection.

    Returns
    =======
    resources: dict
        Dictionary containing all (available) X resources. Resources that are specified
        in an Xresources/Xdefaults file as wildcards e.g. '*.color1' have the leading
        '*.' stripped.

    """
    try:
        conn = xcffib.connect(display=DISPLAY)
    except xcffib.ConnectionException:
        return defaults

    root = conn.get_setup().roots[0].root
    atom = conn.core.InternAtom(False, 16, 'RESOURCE_MANAGER').reply().atom

    reply = conn.core.GetProperty(
        False, root, atom,
        xcffib.xproto.Atom.STRING,
        0, (2 ** 32) - 1
    ).reply()
    conn.disconnect()

    resource_string = reply.value.buf().decode("utf-8")
    resource_list = filter(None, resource_string.split('\n'))
    resources = {}

    for resource in resource_list:
        key, value = resource.split(':\t')
        resources[key.strip('*.')] = value

    return resources
