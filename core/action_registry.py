# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

"""Metadata layer for actions. Runtime compatibility handlers remain in runtime.py while new actions use modular helpers."""

NO_CONFIRM_EXACT = set([
    'CMD:SHOW_AIO_INFO', 'CMD:NETWORK_DIAGNOSTICS', 'CMD:FREE_SPACE_DISPLAY',
    'CMD:UNINSTALL_MANAGER', 'CMD:MANAGE_DVBAPI', 'CMD:CHECK_FOR_UPDATES',
    'CMD:SUPER_SETUP_WIZARD', 'CMD:UPDATE_SATELLITES_XML', 'CMD:INSTALL_SERVICEAPP',
    'CMD:IPTV_DEPS', 'CMD:INSTALL_E2KODI', 'CMD:INSTALL_J00ZEK_REPO',
    'CMD:INSTALL_SOFTCAM_SCRIPT', 'CMD:INSTALL_IPTV_DREAM', 'CMD:INSTALL_S4AUPDATER', 'CMD:INSTALL_PICON_UPDATER', 'CMD:INSTALL_MYUPDATER', 'CMD:SETUP_AUTO_RAM',
    'CMD:FEED_MANAGER', 'CMD:POSTINSTALL_REPAIR', 'CMD:TOGGLE_MENU_VISIBILITY',
    'CMD:SHOW_PENDING_AIO_UPDATE', 'CMD:AIO_SEARCH', 'CMD:AIO_FAVORITES',
    'CMD:AIO_RECENT', 'CMD:AIO_SOURCE_HEALTH', 'CMD:AIO_UPDATE_CHANNEL',
])

NAVIGATION_ACTIONS = set([
    'CMD:AIO_SEARCH', 'CMD:AIO_FAVORITES', 'CMD:AIO_RECENT',
    'CMD:AIO_UPDATE_CHANNEL', 'CMD:SHOW_AIO_INFO', 'CMD:LOCAL_CHANGELOG',
    'CMD:SHOW_AIO_TIP',
])


def action_key(action):
    value = str(action or '')
    if value.startswith('CMD:'):
        return value.split(':', 1)[1]
    return value.split(':', 1)[0]


def requires_confirmation(action):
    value = str(action or '')
    if value in NO_CONFIRM_EXACT:
        return False
    return True


def should_record_recent(action):
    return str(action or '') not in NAVIGATION_ACTIONS and str(action or '') != 'SEPARATOR'
