# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

# Explicit remote-script sources approved for execution as root by AIO Panel.
# Matching owner/repository/path is intentionally stricter than trusting github.com as a whole.
TRUSTED_REMOTE_SCRIPTS = set([
    'https://raw.githubusercontent.com/OliOli2013/E2-Doctor-Plugin/main/installer.sh',
    'https://raw.githubusercontent.com/OliOli2013/SimpleIPTV_EPG/main/installer.sh',
    'https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main/installer.sh',
    'https://raw.githubusercontent.com/OliOli2013/MyUpdater-Plugin/main/installer.sh',
    'https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh',
    'https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh',
    'https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh',
    'https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh',
    'https://raw.githubusercontent.com/Belfagor2005/vavoo/main/installer.sh',
    'https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/installer.sh',
    'https://raw.githubusercontent.com/Belfagor2005/SimpleZooomPanel/main/installer.sh',
    'https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh',
    'https://raw.githubusercontent.com/ciefp/CiefpOscamEditor/main/installer.sh',
    'https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh',
    'https://raw.githubusercontent.com/levi-45/Levi45Emulator/main/installer.sh',
    'https://raw.githubusercontent.com/popking159/skins/refs/heads/main/aglarepli/installer.sh',
    'https://raw.githubusercontent.com/popking159/skins/refs/heads/main/lukapli/installer.sh',
    'https://raw.githubusercontent.com/popking159/skins/refs/heads/main/maxyatv/installer.sh',
    'https://raw.githubusercontent.com/islam-2412/FuryBiss/refs/heads/main/fury/installer.sh',
    'https://raw.githubusercontent.com/Insprion80/Skins/main/xDreamy/installer.sh',
    'https://github.com/s3n0/e2plugins/raw/master/ChocholousekPicons/online-setup',
])


# Deliberate compatibility exception. The S4aUpdater publisher currently documents
# only this legacy HTTP bootstrap URL. It is never accepted by the generic remote
# script runner; only install_s4aupdater_safe.sh may use it.
TRUSTED_LEGACY_HTTP_SCRIPTS = set([
    'http://s4aupdater.one.pl/instalujs4aupdater.sh',
])

TRUSTED_INSTALLER_PROFILES = {
    'https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh': 'iptv-dream',
    'https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh': 'picon-updater',
    'https://raw.githubusercontent.com/OliOli2013/MyUpdater-Plugin/main/installer.sh': 'myupdater',
}

ESSENTIAL_HEALTH_TARGETS = [
    ('AIO Panel - version', 'https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/version.txt'),
    ('AIO Panel - changelog', 'https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/changelog.txt'),
    ('AIO Lists - manifest', 'https://raw.githubusercontent.com/OliOli2013/PanelAIO-Lists/main/manifest.json'),
    ('E2iPlayer Python3', 'https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh'),
    ('PiconUpdater installer', 'https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh'),
    ('MyUpdater v5.1 installer', 'https://raw.githubusercontent.com/OliOli2013/MyUpdater-Plugin/main/installer.sh'),
    ('satellites.xml OpenPLi', 'https://raw.githubusercontent.com/OpenPLi/tuxbox-xml/master/xml/satellites.xml'),
    ('S4aUpdater installer (legacy HTTP)', 'http://s4aupdater.one.pl/instalujs4aupdater.sh'),
]


def normalize_script_url(url):
    value = str(url or '').strip()
    # Action payloads may carry one safe installer argument after '|'.
    if '|' in value:
        value = value.split('|', 1)[0].strip()
    return value


def is_trusted_remote_script(url):
    value = normalize_script_url(url)
    try:
        parsed = urlparse(value)
        if parsed.scheme.lower() != 'https' or not parsed.hostname:
            return False
    except Exception:
        return False
    return value in TRUSTED_REMOTE_SCRIPTS


def health_targets(include_scripts=True):
    targets = list(ESSENTIAL_HEALTH_TARGETS)
    if include_scripts:
        for url in sorted(TRUSTED_REMOTE_SCRIPTS):
            try:
                p = urlparse(url)
                parts = [x for x in p.path.split('/') if x]
                label = '/'.join(parts[:3]) if parts else p.hostname
            except Exception:
                label = url
            targets.append(('Installer: ' + label, url))
    return targets
