# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import os

# Lightweight local presence checks only; no opkg update/network access is performed
# while the user moves through the menu.
_ACTION_PATHS = {
    'CMD:INSTALL_IPTV_DREAM': (
        '/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream/plugin.py',
    ),
    'CMD:INSTALL_S4AUPDATER': (
        '/usr/lib/enigma2/python/Plugins/Extensions/S4aUpdater/plugin.py',
        '/usr/lib/enigma2/python/Plugins/SystemPlugins/S4aUpdater/plugin.py',
    ),
    'CMD:INSTALL_PICON_UPDATER': (
        '/usr/lib/enigma2/python/Plugins/Extensions/PiconUpdater/plugin.py',
    ),
    'CMD:INSTALL_MYUPDATER': (
        '/usr/lib/enigma2/python/Plugins/Extensions/MyUpdater/plugin.py',
    ),
    'CMD:INSTALL_E2IPLAYER': (
        '/usr/lib/enigma2/python/Plugins/Extensions/IPTVPlayer/plugin.py',
        '/usr/lib/enigma2/python/Plugins/Extensions/E2iPlayer/plugin.py',
    ),
}


def is_installed(action):
    paths = _ACTION_PATHS.get(str(action or ''))
    if not paths:
        return None
    return any(os.path.isfile(path) for path in paths)


def status_text(action, lang='PL'):
    state = is_installed(action)
    if state is None:
        return ''
    if lang == 'PL':
        return 'Status: ✓ zainstalowana' if state else 'Status: — niezainstalowana'
    return 'Status: ✓ installed' if state else 'Status: — not installed'
