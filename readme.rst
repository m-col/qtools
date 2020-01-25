qtools
======

This is a small collection of plugins I wrote for Qtile_.

Aims:
    - Simplifying Qtile configuration.
    - Only loading those that are used.
    - Ability to easily create responsive key-bindings with notifications.
    - Avoiding extra dependencies.


Bases
-----

Notifiers
`````````

:code:`Notifier`-based plugins expose methods that trigger notifications, with
the purpose of being bound to keys.

An example usage:

.. code-block:: python

    import qtools.mpc
    mpc = qtools.mpc.Client()
    keys.extend([EzKey(k, v) for k, v in {
        '<XF86AudioPlay>':  mpc.lazy_toggle,
        '<XF86AudioNext>':  mpc.lazy_next,
        '<XF86AudioPrev>':  mpc.lazy_previous,
    }.items()])

:code:`Notifier`'s methods are exposed with the 'lazy\_' prefix for binding to
keys.

:code:`qtools.mpc.Client` is a subclass of :code:`Notifier`, which is found at
:code:`qtools.Notifier` in :code:`qtools/__init__.py`.


Popups
``````

The :code:`Popup` class can be used to create and control popup windows, such
as tooltips or notifications. For an example see the :code:`notification`
plugin.


Plugin list
-----------

==============  ===============================================================
Module          Description
==============  ===============================================================
amixer          Notifier that controls an ALSA device's volume

backlight       Notifier that controls backlight level

notification    A fully functional notification server

mpc             Notifier that controls MPD

xresources      Load X resources into Qtile config
==============  ===============================================================

.. _Qtile: https://github.com/qtile/qtile
