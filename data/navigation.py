# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Classification uses stable action IDs/URLs. Labels and installation commands
# are carried through unchanged, after receiver-specific compatibility filters.
TITLES = [
    ('channels', 'Listy kanałów', 'Channel lists'),
    ('start', 'AIO / Aktualizacje', 'AIO / Updates'),
    ('iptv', 'IPTV / Odtwarzacze', 'IPTV / Players'),
    ('epg', 'EPG / Picony', 'EPG / Picons'),
    ('skins', 'Skórki', 'Skins'),
    ('softcam', 'Softcam / OSCam', 'Softcam / OSCam'),
    ('plugins', 'Wtyczki / Feedy', 'Plugins / Feeds'),
    ('backup', 'Kopie / Przywracanie', 'Backup / Restore'),
    ('system', 'System / Konserwacja', 'System / Maintenance'),
    ('diagnostics', 'Diagnostyka / Naprawa', 'Diagnostics / Repair'),
    ('connect', 'Kontakt / Społeczność', 'Contact / Community'),
    ('adult', 'Dla dorosłych 18+', 'Adults 18+'),
]
ACTIONS = {
    'start': 'SHOW_AIO_INFO CHECK_FOR_UPDATES SHOW_PENDING_AIO_UPDATE AIO_QUICKSTART AIO_SEARCH AIO_FAVORITES AIO_RECENT AIO_UPDATE_CHANNEL SHOW_AIO_TIP LOCAL_CHANGELOG PLUGIN_UPDATE_MANAGER',
    'epg': 'INSTALL_PICON_UPDATER',
    'softcam': 'RESTART_OSCAM CLEAR_OSCAM_PASS MANAGE_DVBAPI UPDATE_DVBAPI_POLAND UPDATE_SRVID INSTALL_SOFTCAMKEY_ONLINE INSTALL_SOFTCAM_SCRIPT INSTALL_BEST_OSCAM INSTALL_LEVI45_OSCAM INSTALL_NCAM_FEED',
    'backup': 'BACKUP_LIST BACKUP_OSCAM RESTORE_LIST RESTORE_OSCAM',
    'system': 'SUPER_SETUP_WIZARD TOGGLE_MENU_VISIBILITY CRON_MANAGER SERVICE_MANAGER SETUP_AUTO_RAM CLEAR_TMP_CACHE SMART_CLEANUP CLEAR_RAM_CACHE CLEAR_FTP_PASS SET_SYSTEM_PASSWORD',
    'diagnostics': 'SYSTEM_MONITOR LOG_VIEWER SYSTEM_INFO POSTINSTALL_REPAIR AIO_SOURCE_HEALTH COMPATIBILITY_CHECK NETWORK_DIAGNOSTICS FREE_SPACE_DISPLAY AIO_CONNECT_DIAGNOSTICS AIO_CONNECT_REPORT',
    'connect': 'AIO_CONNECT_REPORT_QR AIO_CONNECT_SITE_QR AIO_CONNECT_JOIN_COMMUNITY AIO_CONNECT_PRIVACY AIO_CONNECT_COMMUNITY_QR',
    'channels': 'UPDATE_SATELLITES_XML',
    'plugins': 'UNINSTALL_MANAGER FEED_MANAGER INSTALL_S4AUPDATER INSTALL_MYUPDATER INSTALL_J00ZEK_REPO',
    'iptv': 'INSTALL_IPTV_DREAM INSTALL_SERVICEAPP IPTV_DEPS INSTALL_E2IPLAYER INSTALL_BMX_SAFE INSTALL_E2KODI INSTALL_ESTALKER_SAFE',
    'adult': 'INSTALL_ADULT_XXX',
}
LOOKUP = dict(('CMD:' + action, group) for group, actions in ACTIONS.items() for action in actions.split())


def classify(action):
    if action in LOOKUP:
        return LOOKUP[action]
    low = action.lower()
    if action.startswith('picons:') or any(x in low for x in ('epgimport', 'simpleiptv_epg', 'ppchannelsync', 'chocholousek')):
        return 'epg'
    if 'ciefposcameditor' in low:
        return 'softcam'
    if 'e2-doctor' in low:
        return 'diagnostics'
    if any(x in low for x in ('ajpanel', 'simplezooompanel')):
        return 'plugins'
    return 'iptv'


def build_tabs(lang, channel_lists, softcam, tools, skins, diagnostics):
    groups = dict((key, []) for key, pl, en in TITLES)
    groups['channels'] = list(channel_lists)
    groups['skins'] = [item for item in skins if item[1] != 'SEPARATOR']
    for items in (softcam, tools, diagnostics):
        for item in items:
            if item[1] != 'SEPARATOR':
                groups[classify(item[1])].append(item)
    return [(pl if lang == 'PL' else en, groups[key]) for key, pl, en in TITLES if groups[key]]
