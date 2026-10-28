# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import os
try:
    from shlex import quote
except ImportError:
    from pipes import quote

# Feed packages are resolved by the receiver, never copied from another image.
# (id, PL description, EN description, tab, package alternatives)
ROWS = [
 ('autotimer','AutoTimer — automatyczne nagrywanie','AutoTimer — automatic recordings','plugins',['enigma2-plugin-extensions-autotimer']),
 ('epgrefresh','EPGRefresh — odświeżanie EPG','EPGRefresh — refresh EPG','epg',['enigma2-plugin-extensions-epgrefresh']),
 ('epgsearch','EPGSearch — wyszukiwanie audycji','EPGSearch — search events','epg',['enigma2-plugin-extensions-epgsearch']),
 ('emc','Enhanced Movie Center — nagrania','Enhanced Movie Center — recordings','plugins',['enigma2-plugin-extensions-enhancedmoviecenter']),
 ('moviecut','MovieCut — cięcie nagrań','MovieCut — recording cuts','plugins',['enigma2-plugin-extensions-moviecut']),
 ('movieretitle','MovieRetitle — nazwy nagrań','MovieRetitle — recording names','plugins',['enigma2-plugin-extensions-movieretitle']),
 ('dreamexplorer','DreamExplorer — menedżer plików','DreamExplorer — file manager','plugins',['enigma2-plugin-extensions-dreamexplorer']),
 ('filecommander','File Commander — pliki','File Commander — files','plugins',['enigma2-plugin-extensions-filecommander']),
 ('openwebif','OpenWebif — obsługa przez przeglądarkę','OpenWebif — browser control','plugins',['enigma2-plugin-extensions-openwebif']),
 ('transcoding','Transcoding Setup — ustawienia streamingu','Transcoding Setup — streaming settings','plugins',['enigma2-plugin-systemplugins-transcodingsetup']),
 ('permanentclock','PermanentClock — zegar na ekranie','PermanentClock — on-screen clock','plugins',['enigma2-plugin-extensions-permanentclock']),
 ('virtualzap','VirtualZap — podgląd kanałów','VirtualZap — channel preview','plugins',['enigma2-plugin-extensions-virtualzap']),
 ('subssupport','SubsSupport — napisy','SubsSupport — subtitles','iptv',['enigma2-plugin-extensions-subssupport']),
 ('weather','Weather Plugin — pogoda','Weather Plugin — weather','plugins',['enigma2-plugin-extensions-weatherplugin']),
 ('skin-metrix','MetrixHD — skórka z feedu','MetrixHD — image feed skin','skins',['enigma2-plugin-skins-metrix-atv','enigma2-plugin-skins-metrix-spa']),
 ('skin-pli','PLi HD — skórka z feedu','PLi HD — image feed skin','skins',['enigma2-plugin-skins-pli-hd']),
 ('skin-pli-full','PLi HD FullNight — skórka z feedu','PLi HD FullNight — image feed skin','skins',['enigma2-plugin-skins-pli-hd-fullnight-4atv','enigma2-plugin-skins-pli-hd-fullnight']),
 ('skin-simple','Umbra — skórka z feedu','Umbra — image feed skin','skins',['enigma2-plugin-skins-umbra']),
 ('skin-hdglass','HD Glass — jeśli dostępny w feedzie','HD Glass — if available in feed','skins',['enigma2-skin-fullhdglass17']),
 ('jediepg','Jedi EPG Xtream — przypisanie EPG','Jedi EPG Xtream — EPG assignment','epg',['enigma2-plugin-extensions-jediepgxtream']),
 ('ciefp','CIEFP OSCam Editor','CIEFP OSCam Editor','softcam',['enigma2-plugin-extensions-ciefposcameditor']),
 ('footonsat','FootOnSat — wydarzenia sportowe','FootOnSat — sports events','plugins',['enigma2-plugin-extensions-footonsat']),
]
CATALOG = dict((key, dict(pl=pl,en=en,group=group,packages=packages)) for key,pl,en,group,packages in ROWS)

def menu_items(lang, python_major, only_skins=False, exclude_skins=False, available_skins=None):
    result = []
    used = set()
    for key,pl,en,group,packages in ROWS:
        if only_skins and group != 'skins': continue
        if exclude_skins and group == 'skins': continue
        if group == 'skins':
            compatible = [p for p in packages if p in (available_skins or [])]
            if not compatible: continue
            used.update(compatible)
        label = pl if lang == 'PL' else en
        result.append((label + (' [feed obrazu]' if lang == 'PL' else ' [image feed]'), 'feed:' + key))
    if only_skins:
        for package in (available_skins or []):
            if package in used: continue
            key = 'native-' + package
            CATALOG[key] = dict(group='skins', packages=[package])
            label = package.replace('enigma2-plugin-skins-', '').replace('enigma2-skin-', '')
            result.append((label + (' [feed obrazu]' if lang == 'PL' else ' [image feed]'), 'feed:' + key))
    return result

def command_for(key, plugin_path):
    if key not in CATALOG: raise ValueError('Unknown catalog item')
    return '/bin/sh %s %s' % (quote(os.path.join(plugin_path,'install_feed_package.sh')), ' '.join(quote(p) for p in CATALOG[key]['packages']))
