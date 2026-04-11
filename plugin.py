# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

from Plugins.Plugin import PluginDescriptor

try:
    from Components.config import config, ConfigSubsection, ConfigYesNo
except Exception:
    config = None
    ConfigSubsection = None
    ConfigYesNo = None

from Plugins.SystemPlugins.PanelAIO.ui.main import open_main, menu_entries, sessionstart_hook
from Plugins.SystemPlugins.PanelAIO.core.system import plugin_version


def _init_config():
    if config is None or ConfigSubsection is None:
        return
    try:
        if not hasattr(config.plugins, 'panelaio'):
            config.plugins.panelaio = ConfigSubsection()
        if ConfigYesNo is not None and not hasattr(config.plugins.panelaio, 'show_in_menu'):
            config.plugins.panelaio.show_in_menu = ConfigYesNo(default=True)
    except Exception:
        pass


_init_config()


def main(session, **kwargs):
    open_main(session, **kwargs)


def sessionstart(reason, session=None, **kwargs):
    return sessionstart_hook(reason, session=session, **kwargs)


def menu(menuid, **kwargs):
    return menu_entries(menuid, **kwargs)


def Plugins(**kwargs):
    version = plugin_version()
    return [
        PluginDescriptor(name='AIO Panel', description='AIO Panel %s modular architecture' % version, where=PluginDescriptor.WHERE_PLUGINMENU, icon='logo.png', fnc=main),
        PluginDescriptor(where=PluginDescriptor.WHERE_MENU, fnc=menu),
        PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart),
    ]
