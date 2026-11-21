# -*- coding: utf-8 -*-
"""Match stable dashboard actions to pictures, descriptive cards and row icons."""
from __future__ import absolute_import, unicode_literals

import json
import os
from collections import namedtuple
try:
    from urllib.parse import urlsplit, unquote
except ImportError:
    from urlparse import urlsplit
    from urllib import unquote

from Plugins.SystemPlugins.PanelAIO.core import skin_previews, visual_previews
from Plugins.SystemPlugins.PanelAIO.data.catalog import CATALOG
from Plugins.SystemPlugins.PanelAIO.core.compatibility import ensure_unicode

Media = namedtuple('Media', 'kind key icon source')
ROOT = skin_previews.BUNDLED
ICON_ROOT = os.path.join(os.path.dirname(ROOT), 'icons')
def archive_key(address):
    parsed = urlsplit(address)
    parts = parsed.path.lstrip('/').split('/')
    if parsed.hostname == 'raw.githubusercontent.com':
        return '/'.join(parts)
    if parsed.hostname == 'github.com' and len(parts) > 3 and parts[2] == 'raw':
        return '/'.join(parts[:2] + parts[3:])
    return address


try:
    with open(os.path.join(ROOT, 'channel_samples.json'), 'rb') as samples:
        CHANNEL_SAMPLES = dict((archive_key(url), names) for url, names in json.load(samples).items())
except (IOError, OSError, ValueError):
    CHANNEL_SAMPLES = {}

PICON_FILES = ('13e', '19e', 'both')
COMMANDS = {
    'CHECK_FOR_UPDATES': 'panelaio', 'INSTALL_IPTV_DREAM': 'iptvdream',
    'INSTALL_MYUPDATER': 'myupdater', 'INSTALL_PICON_UPDATER': 'piconupdater',
    'INSTALL_SERVICEAPP': 'serviceapp', 'INSTALL_E2IPLAYER': 'e2iplayer',
    'INSTALL_BMX_SAFE': 'bmx', 'INSTALL_JEDI_GITHUB': 'jedi', 'INSTALL_E2KODI': 'e2kodi',
    'INSTALL_ESTALKER_SAFE': 'estalker', 'INSTALL_CHOCHO_GITHUB': 'chocho',
    'INSTALL_S4AUPDATER': 's4aupdater', 'INSTALL_FURY_SKIN': 'furybiss',
    'INSTALL_NCAM_FEED': 'ncam', 'INSTALL_LEVI45_OSCAM': 'oscam', 'INSTALL_BEST_OSCAM': 'oscam',
}
REPOS = {'simpleiptv_epg':'simpleiptvepg', 'neoradio':'neoradio', 'ppchannelsync-plugin':'ppchannelsync',
         'e2-doctor-plugin':'e2doctor', 'opencamview-plugin':'opencamview', 'ajpanel':'ajpanel',
         'epgimport-99':'epgimport', 'vavoo':'vavoo', 'tvgarden':'tvgarden',
         'simplezooompanel':'zoompanel', 'enigma2-plugin-youtube':'youtube'}
ROW_ICONS = {'neoradio':'radio', 'opencamview':'camera','e2doctor':'repair','piconupdater':'picons',
             'chocho':'picons','epgimport':'epg','epgrefresh':'epg','epgsearch':'search','jediepg':'epg',
             'myupdater':'update','s4aupdater':'update','panelaio':'start','ppchannelsync':'channels',
             'iptvdream':'iptv','simpleiptvepg':'epg','bmx':'channels','jedi':'channels',
             'serviceapp':'media','e2iplayer':'media','youtube':'media','tvgarden':'iptv',
             'vavoo':'iptv','xstreamity':'iptv','streamlinkproxy':'network','e2kodi':'media',
             'autotimer':'clock','moviecut':'media','movieretitle':'files','emc':'record',
             'dreamexplorer':'files','filecommander':'files','openwebif':'network',
             'transcoding':'media','permanentclock':'clock','virtualzap':'channels',
             'subssupport':'captions','weather':'weather','footonsat':'sport','ciefp':'softcam',
             'ajpanel':'tools','zoompanel':'search','furybiss':'softcam','ncam':'softcam','oscam':'softcam'}
PL_EN = {'screen':('Zrzut ekranu','Screenshot'), 'logo':('Logo wtyczki','Plugin logo'),
         'art':('Grafika autora','Publisher artwork'), 'skin':('Podgląd skórki','Skin preview'),
         'picons':('Próbka piconów','Picon sample'), 'card':('Karta funkcji','Feature details'),
         'skin-card':('Karta skórki','Skin details'), 'layout':('Układ z plików skórki','Layout from skin files'), 'feed':('Feed odbiornika','Receiver feed'),
         'local':('AIO Panel','AIO Panel'), 'archive':('Archiwum','Archive'),
         'installer':('Instalator','Installer'), 'package':('Pakiet','Package')}
def phrase(key, lang):
    return PL_EN[key][0 if lang == 'PL' else 1]

def split_source(action):
    address = action.partition(':')[2].split('|', 1)[0]
    parsed = urlsplit(address)
    parts = [x for x in parsed.path.split('/') if x]
    if parsed.hostname in ('github.com','raw.githubusercontent.com') and len(parts) >= 2:
        return REPOS.get(parts[1].lower(), ''), 'GitHub · ' + '/'.join(parts[:2])
    return '', parsed.hostname or ''

def lookup(action, category):
    action = ensure_unicode(action)
    if not action or action == 'SEPARATOR':
        return None
    skin = skin_previews.skin_id(action)
    if skin:
        package = skin_previews.feed_package(action)
        if not package and action.startswith('feed:'):
            package = CATALOG.get(action[5:], {}).get('preview_package')
            if package:
                skin = skin_previews.skin_id('feed:native-' + package) or skin
        return Media('skin', skin, 'skins', package or '')
    prefix, _, value = action.partition(':')
    origin = ''
    if prefix == 'picons':
        return Media('picons','both','picons','13°E / 19.2°E')
    if prefix == 'feed':
        key = value
        origin = ', '.join(CATALOG.get(key, {}).get('packages', []))
    elif prefix == 'opkg':
        key = value.rsplit('extensions-',1)[-1]
        origin = value
    elif prefix == 'CMD':
        key = COMMANDS.get(value, '')
    elif prefix in ('remote_script','remote_script_bash','safe_ipk','archive','s4archive'):
        key, origin = split_source(action)
        if prefix in ('archive', 's4archive'):
            filename = unquote(urlsplit(value).path.rsplit('/',1)[-1])
            origin = (origin + ' · ' + ensure_unicode(filename)) if filename else origin
    else:
        key = ''
    icon = ROW_ICONS.get(key, category)
    if not key and prefix == 'CMD':
        if value == 'AIO_APPEARANCE': icon = 'appearance'
        elif 'RESTORE' in value: icon = 'restore'
        elif 'BACKUP' in value: icon = 'backup'
        elif 'UPDATE' in value: icon = 'update'
        elif 'SEARCH' in value: icon = 'search'
        elif 'RECENT' in value: icon = 'history'
        elif 'FAVORITES' in value: icon = 'star'
        elif 'NETWORK' in value or 'FEED' in value: icon = 'network'
        elif 'WIZARD' in value: icon = 'tools'
        elif 'SPACE' in value: icon = 'storage'
        elif 'CLOCK' in value or 'CRON' in value: icon = 'clock'
        elif 'INFO' in value or 'TIP' in value: icon = 'help'
    image = skin_previews.GALLERY.get('plugins',{}).get(key)
    if image:
        return Media(image[1],image[0],icon,origin)
    return Media('card',key,icon,origin)

def picture(media):
    if not media: return None
    if media.kind == 'skin': return skin_previews.local_image(media.key)
    if media.kind in ('screen','art','logo'):
        return os.path.join(ROOT, 'plugins', media.key + '.png')
    if media.kind == 'picons':
        return os.path.join(ROOT,'picons',media.key + '.png')
    return None

def source_label(action, media, lang):
    if media.source:
        return media.source
    if action.startswith(('feed:', 'opkg:')):
        return phrase('feed', lang)
    if action.startswith('CMD:INSTALL_'):
        return phrase('installer',lang) + ' · AIO Panel'
    return 'AIO Panel'


def has_preview(action, media):
    if not media:
        return False
    if media.kind != 'card':
        return True
    if visual_previews.preview_id(action):
        return True
    return action.startswith(('feed:', 'opkg:', 'archive:', 's4archive:', 'bouquet:', 'm3u:', 'bouquet_json:', 'm3u_json:', 'safe_ipk:', 'picons:', 'bash_raw:',
        'remote_script:', 'remote_script_bash:', 'CMD:INSTALL_', 'CMD:UPDATE_')) or action in (
        'CMD:SUPER_SETUP_WIZARD', 'CMD:IPTV_DEPS', 'CMD:PLUGIN_UPDATE_MANAGER')


def icon_path(icon):
    return os.path.join(ICON_ROOT, 'large', icon + '.png')
