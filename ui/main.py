# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

"""Public entry point for the modern AIO Panel interface."""

from Plugins.SystemPlugins.PanelAIO.ui.modern import ModernLoadingScreen, ModernPanelAIO


def open_main(session, lang=None, **kwargs):
    def loaded(data=None):
        if isinstance(data, dict):
            session.open(ModernPanelAIO, data)
    return session.openWithCallback(loaded, ModernLoadingScreen)


def menu_entries(menuid, **kwargs):
    from Plugins.SystemPlugins.PanelAIO import runtime
    return runtime.menu(menuid, **kwargs)


def sessionstart_hook(reason, session=None, **kwargs):
    return None
