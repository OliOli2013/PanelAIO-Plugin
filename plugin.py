# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

"""AIO Panel entry point.

v13.0.2 keeps the heavy runtime layer lazy-loaded and disables startup-side tasks.  Enigma2 imports plugin.py
while building the plugin list and during GUI startup; loading the whole PanelAIO
runtime at that moment is risky on some OpenATV 8 / beta images.  The dashboard
runtime is imported only when the user opens AIO Panel, while the menu entry and
safe session-start tasks stay lightweight.
"""

import os

from Plugins.Plugin import PluginDescriptor

try:
    from Components.config import config, ConfigSubsection, ConfigSelection, ConfigYesNo, configfile
except Exception:
    config = None
    ConfigSubsection = None
    ConfigSelection = None
    ConfigYesNo = None
    configfile = None

try:
    from enigma import eTimer
except Exception:
    eTimer = None

PLUGIN_NAME = 'AIO Panel'
DEFAULT_VERSION = '13.0.2'
MENU_VISIBILITY_FALLBACK_FILE = '/etc/enigma2/.panelaio_show_in_menu'

_auto_ram_timer = None
_auto_ram_connected = False
_auto_ram_active = False


def _plugin_path():
    try:
        return os.path.dirname(os.path.realpath(__file__))
    except Exception:
        return '/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO'


def _read_version(default=DEFAULT_VERSION):
    try:
        path = os.path.join(_plugin_path(), 'version.txt')
        with open(path, 'r') as f:
            value = f.read().strip()
        return value or default
    except Exception:
        return default


def _init_config():
    if config is None or ConfigSubsection is None:
        return
    try:
        if not hasattr(config.plugins, 'panelaio'):
            config.plugins.panelaio = ConfigSubsection()
        if ConfigSelection is not None and not hasattr(config.plugins.panelaio, 'auto_ram_interval'):
            config.plugins.panelaio.auto_ram_interval = ConfigSelection(
                default='off',
                choices=[('off', 'off'), ('10', '10'), ('30', '30'), ('60', '60')]
            )
        if ConfigYesNo is not None and not hasattr(config.plugins.panelaio, 'show_in_menu'):
            config.plugins.panelaio.show_in_menu = ConfigYesNo(default=True)
    except Exception as e:
        print('[AIO Panel] lightweight config init error:', e)


def _bool_from_text(value, default=True):
    try:
        txt = str(value).strip().lower()
    except Exception:
        return default
    if txt in ('1', 'true', 'yes', 'on', 'enabled', 'wlaczone', 'włączone'):
        return True
    if txt in ('0', 'false', 'no', 'off', 'disabled', 'wylaczone', 'wyłączone'):
        return False
    return default


def _read_menu_visibility_fallback():
    try:
        if os.path.exists(MENU_VISIBILITY_FALLBACK_FILE):
            with open(MENU_VISIBILITY_FALLBACK_FILE, 'r') as f:
                return _bool_from_text(f.read(), True)
    except Exception as e:
        print('[AIO Panel] menu visibility fallback read error:', e)
    return None


def _get_show_in_menu_setting(default=True):
    fallback = _read_menu_visibility_fallback()
    if fallback is not None:
        return bool(fallback)
    try:
        if config is not None and hasattr(config.plugins, 'panelaio') and hasattr(config.plugins.panelaio, 'show_in_menu'):
            return bool(config.plugins.panelaio.show_in_menu.value)
    except Exception as e:
        print('[AIO Panel] menu visibility config read error:', e)
    return default


def _show_start_error(session, err):
    text = 'AIO Panel nie uruchomił się poprawnie.\n\nBłąd:\n%s' % err
    try:
        from Screens.MessageBox import MessageBox
        session.open(MessageBox, text, MessageBox.TYPE_ERROR, timeout=15)
    except Exception:
        print('[AIO Panel] startup error:', err)


def _open_runtime(session, **kwargs):
    try:
        from Plugins.SystemPlugins.PanelAIO.ui.main import open_main
        return open_main(session, **kwargs)
    except Exception as e:
        _show_start_error(session, e)
        return None


def main(session, **kwargs):
    return _open_runtime(session, **kwargs)


def _get_auto_ram_timer():
    global _auto_ram_timer, _auto_ram_connected
    if eTimer is None:
        return None
    if _auto_ram_timer is None:
        _auto_ram_timer = eTimer()
        _auto_ram_connected = False
    if not _auto_ram_connected:
        try:
            _auto_ram_timer.callback.append(_run_auto_ram_clean_task)
            _auto_ram_connected = True
        except Exception:
            try:
                _auto_ram_timer.timeout.connect(_run_auto_ram_clean_task)
                _auto_ram_connected = True
            except Exception as e:
                print('[AIO Panel] Auto RAM timer connect error:', e)
    return _auto_ram_timer


def _run_auto_ram_clean_task():
    try:
        os.system('sync; echo 3 > /proc/sys/vm/drop_caches')
        print('[AIO Panel] Auto RAM Cleaner: memory cleaned automatically.')
    except Exception as e:
        print('[AIO Panel] Auto RAM Cleaner error:', e)


def _apply_auto_ram_from_config():
    global _auto_ram_active
    try:
        timer = _get_auto_ram_timer()
        if timer is None:
            return
        if config is None or not hasattr(config.plugins, 'panelaio') or not hasattr(config.plugins.panelaio, 'auto_ram_interval'):
            return
        value = getattr(config.plugins.panelaio.auto_ram_interval, 'value', 'off')
        if value and value != 'off':
            minutes = int(value)
            if minutes > 0:
                timer.start(minutes * 60000, False)
                _auto_ram_active = True
                print('[AIO Panel] Auto RAM Cleaner restored: %s min' % minutes)
                return
        timer.stop()
        _auto_ram_active = False
    except Exception as e:
        print('[AIO Panel] Auto RAM apply error:', e)


def sessionstart(reason, session=None, **kwargs):
    # v13.0.1: absolute safe startup. Do not run timers, shell commands or runtime imports during boot.
    return None


def menu(menuid, **kwargs):
    if menuid in ('system', 'mainmenu'):
        try:
            if not _get_show_in_menu_setting(True):
                return []
        except Exception:
            pass
        if menuid == 'mainmenu':
            return [(PLUGIN_NAME, main, 'aio_panel_main', 45)]
        return [(PLUGIN_NAME, main, 'aio_panel', 45)]
    return []


_init_config()


def Plugins(**kwargs):
    version = _read_version()
    return [
        PluginDescriptor(
            name=PLUGIN_NAME,
            description='Panel All-In-One v%s' % version,
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon='logo.png',
            fnc=main
        ),
        PluginDescriptor(where=PluginDescriptor.WHERE_MENU, fnc=menu),
    ]
