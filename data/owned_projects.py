# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

"""AIO Team projects, sourced from OliOli2013 GitHub repository inventory.

Repository-only resources (website and channel lists) are excluded: channel
lists already have their own tab; the website is not an Enigma2 plugin.
Projects are registered once here, never duplicated in IPTV/EPG/Skins/Tools.
"""

OWNER = 'OliOli2013'
PROJECTS = (
    ('PanelAIO-Plugin', '🔄 AIO Panel — aktualizacja', '🔄 AIO Panel — update', 'CMD:CHECK_FOR_UPDATES'),
    ('IPTV-Dream-Plugin', '📺 IPTV Dream — instaluj / aktualizuj', '📺 IPTV Dream — install / update', 'CMD:INSTALL_IPTV_DREAM'),
    ('MyUpdater-Plugin', '🔄 MyUpdater — instaluj / aktualizuj', '🔄 MyUpdater — install / update', 'CMD:INSTALL_MYUPDATER'),
    ('PiconUpdater', '🖼️ PiconUpdater — instaluj / aktualizuj', '🖼️ PiconUpdater — install / update', 'CMD:INSTALL_PICON_UPDATER'),
    ('SimpleIPTV_EPG', '📅 Simple IPTV EPG — instaluj / aktualizuj', '📅 Simple IPTV EPG — install / update', 'remote_script:https://raw.githubusercontent.com/OliOli2013/SimpleIPTV_EPG/main/installer.sh'),
    ('NeoRadio', '📻 NeoRadio — instaluj / aktualizuj', '📻 NeoRadio — install / update', 'safe_ipk:https://github.com/OliOli2013/NeoRadio/releases/latest/download/enigma2-plugin-extensions-neoradio_all.ipk|^(enigma2-plugin-extensions-neoradio(?:online|-online)?|neoradio)$'),
    ('PPChannelSync-Plugin', '📡 PP Channel Sync — instaluj / aktualizuj', '📡 PP Channel Sync — install / update', 'remote_script:https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main/installer.sh'),
    ('E2-Doctor-Plugin', '🩺 E2 Doctor (Python 3) — instaluj / aktualizuj', '🩺 E2 Doctor (Python 3) — install / update', 'remote_script:https://raw.githubusercontent.com/OliOli2013/E2-Doctor-Plugin/main/installer.sh'),
    ('AIOHD-NEXT-Skin', '🎨 AIOHD NEXT — instaluj / aktualizuj', '🎨 AIOHD NEXT — install / update', 'CMD:INSTALL_AIOHD_NEXT'),
    ('OpenCamView-Plugin', '📹 OpenCamView — instaluj / aktualizuj', '📹 OpenCamView — install / update', 'remote_script:https://raw.githubusercontent.com/OliOli2013/OpenCamView-Plugin/main/installer.sh'),
)
PROJECT_ACTIONS = frozenset(p[3] for p in PROJECTS)
PROJECT_REPOS = tuple(p[0] for p in PROJECTS)

def project_items(lang):
    return [(p[1] if lang == 'PL' else p[2], p[3]) for p in PROJECTS]

PROJECT_DESCRIPTIONS_PL = {
    'PanelAIO-Plugin': 'Sprawdza nową wersję AIO Panel. Aktualizacja list SAT zachowuje DVB-T/T2, IPTV, FAVOURITES i własną numerację.',
    'IPTV-Dream-Plugin': 'Instaluje lub aktualizuje odtwarzacz IPTV Dream z oficjalnego repozytorium AIO Team.',
    'MyUpdater-Plugin': 'Instaluje lub aktualizuje MyUpdater, narzędzie do aktualizacji wtyczek Enigma2.',
    'PiconUpdater': 'Instaluje PiconUpdater do zarządzania ikonami kanałów.',
    'SimpleIPTV_EPG': 'Instaluje Simple IPTV EPG — dopasowanie EPG i piconów dla kanałów IPTV.',
    'NeoRadio': 'Instaluje NeoRadio z najnowszej publicznej paczki GitHub Releases.',
    'PPChannelSync-Plugin': 'Instaluje narzędzie synchronizacji kanałów PP Channel Sync.',
    'E2-Doctor-Plugin': 'Instaluje E2 Doctor do diagnostyki tunera. Wymaga Python 3.',
    'AIOHD-NEXT-Skin': 'Instaluje skórkę AIOHD NEXT z oficjalnego wydania repozytorium autora.',
    'OpenCamView-Plugin': 'Instaluje OpenCamView do podglądu kamer IP/RTSP/ONVIF. Wymaga Python 3.',
}
PROJECT_DESCRIPTIONS_EN = {
    'PanelAIO-Plugin': 'Check AIO Panel updates. SAT-only channel update preserves DVB-T/T2, IPTV, FAVOURITES and custom numbering.',
    'IPTV-Dream-Plugin': 'Install or update IPTV Dream from the AIO Team repository.',
    'MyUpdater-Plugin': 'Install or update MyUpdater, a plugin update tool.',
    'PiconUpdater': 'Install PiconUpdater, the channel-logo manager.',
    'SimpleIPTV_EPG': 'Install Simple IPTV EPG to match guide data and picons with IPTV services.',
    'NeoRadio': 'Install NeoRadio from the latest public GitHub Release package.',
    'PPChannelSync-Plugin': 'Install PP Channel Sync for channel synchronization.',
    'E2-Doctor-Plugin': 'Install E2 Doctor for receiver diagnostics. Python 3 required.',
    'AIOHD-NEXT-Skin': 'Install the AIOHD NEXT skin from its official release.',
    'OpenCamView-Plugin': 'Install OpenCamView for IP/RTSP/ONVIF cameras. Python 3 required.',
}

def project_description(action, lang):
    for repo, pl, en, project_action in PROJECTS:
        if project_action == action:
            table = PROJECT_DESCRIPTIONS_PL if lang == 'PL' else PROJECT_DESCRIPTIONS_EN
            return table.get(repo, '')
    return ''
