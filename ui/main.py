# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

"""Public entry point for the modern AIO Panel interface."""

from Plugins.SystemPlugins.PanelAIO.ui.modern import ModernLoadingScreen


def open_main(session, lang=None, **kwargs):
    return session.open(ModernLoadingScreen)


def menu_entries(menuid, **kwargs):
    from Plugins.SystemPlugins.PanelAIO import legacy_plugin
    return legacy_plugin.menu(menuid, **kwargs)


def sessionstart_hook(reason, session=None, **kwargs):
    return None
