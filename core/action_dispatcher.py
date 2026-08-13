# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

"""Modular dispatcher for AIO 16.x actions.

Only actions with stable method-level contracts live here. The older runtime keeps
complex low-level workflows as a compatibility backend, while the public action
routing no longer needs to grow one giant conditional chain for every new feature.
"""

_METHODS = {
    'INSTALL_IPTV_DREAM': 'install_iptv_dream_simplified',
    'INSTALL_S4AUPDATER': 'install_s4aupdater_safe',
    'INSTALL_PICON_UPDATER': 'install_picon_updater_safe',
    'INSTALL_MYUPDATER': 'install_myupdater_safe',
    'AIO_QUICKSTART': 'open_aio_quickstart',
    'AIO_SEARCH': 'open_aio_search',
    'AIO_FAVORITES': 'open_favorites',
    'AIO_RECENT': 'open_recent',
    'AIO_SOURCE_HEALTH': 'open_source_health',
    'AIO_UPDATE_CHANNEL': 'show_update_channel_menu',
    'COMPATIBILITY_CHECK': 'open_compatibility_check',
    'SHOW_AIO_TIP': 'show_aio_tip',
    'LOCAL_CHANGELOG': 'show_local_changelog',
}

_CONNECT = {
    'AIO_CONNECT_DIAGNOSTICS': 'diagnostics',
    'AIO_CONNECT_REPORT': 'report',
    'AIO_CONNECT_REPORT_QR': 'report_qr',
    'AIO_CONNECT_SITE_QR': 'site_qr',
    'AIO_CONNECT_COMMUNITY_QR': 'community_qr',
    'AIO_CONNECT_JOIN_COMMUNITY': 'community_join',
    'AIO_CONNECT_PRIVACY': 'privacy',
}


def dispatch(panel, key):
    method_name = _METHODS.get(str(key or ''))
    if method_name:
        getattr(panel, method_name)()
        return True
    connect_action = _CONNECT.get(str(key or ''))
    if connect_action:
        panel.open_aio_connect(connect_action)
        return True
    return False


def registered_keys():
    return sorted(list(_METHODS.keys()) + list(_CONNECT.keys()))
