# -*- coding: utf-8 -*-
"""Find an image for a skin without running a package or touching receiver settings."""
from __future__ import absolute_import
import os
import re
import struct
import tempfile
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

BUNDLED = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'previews')
CACHE = '/tmp/PanelAIO/previews'
PROJECT = 'https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/assets/previews/'
MAX_BYTES = 1536 * 1024
IDS = {
    'CMD:INSTALL_AIOHD_NEXT': 'aiohd', 'CMD:INSTALL_JIHAD_SKIN': 'jihad',
    'CMD:INSTALL_FURY_SKIN': 'fury',
    'feed:skin-metrix': 'metrix', 'feed:skin-pli': 'pli', 'feed:skin-pli-full': 'fullnight',
    'feed:skin-simple': 'umbra', 'feed:skin-hdglass': 'glass17',
    'remote_script:https://raw.githubusercontent.com/popking159/skins/refs/heads/main/aglarepli/installer.sh': 'aglare',
    'remote_script:https://raw.githubusercontent.com/popking159/skins/refs/heads/main/lukapli/installer.sh': 'luka',
    'remote_script:https://raw.githubusercontent.com/popking159/skins/refs/heads/main/maxyatv/installer.sh': 'maxy',
}
PACKAGES = {'aiohd-next': 'aiohd', 'jihad': 'jihad', 'aglare-fhd-pli': 'aglare',
            'luka-fhd-pli': 'luka', 'maxy-fhd': 'maxy', 'obsidian-fhd': 'obsidian',
            'metrix-atv': 'metrix', 'metrix-spa': 'metrix', 'pli-hd': 'pli', 'pli-hd-fullnight': 'fullnight',
            'pli-hd-fullnight-4atv': 'fullnight', 'fullhdglass17': 'glass17',
            'umbra': 'umbra', 'hdglass': 'glass17'}
OE = 'https://raw.githubusercontent.com/oe-alliance/oe-alliance-skins/600402d73b88f911f4a24aeff279672d3a86cb8c/'
UPSTREAM = {'blue-hd': OE + 'Rossi/Blue-HD/prev.png', 'red-hd': OE + 'Rossi/Red-HD/prev.png',
            'novum-fhd-light': OE + 'Nashu/NOVUM_FHD_Light/prev.png',
            'novum-hd-slim': OE + 'Nashu/NOVUM_HD_Slim/prev.png'}


def skin_id(action):
    if not action:
        return None
    if action.startswith('safe_ipk:'):
        source = action.split('|', 1)[0]
        if source == 'safe_ipk:https://raw.githubusercontent.com/Insprion80/Skins/main/xDreamy/xDreamy.ipk':
            return 'xdreamy'
        if source == 'safe_ipk:https://raw.githubusercontent.com/dali44g/Obsidian-FHD/main/release/enigma2-plugin-skins-obsidian-fhd_all.ipk':
            return 'obsidian'
    for prefix in ('feed:native-enigma2-plugin-skins-', 'feed:native-enigma2-skin-'):
        if action.startswith(prefix):
            slug = action[len(prefix):].lower()
            if re.match(r'^[a-z0-9][a-z0-9+._-]{0,79}\Z', slug):
                return PACKAGES.get(slug, slug)
    return IDS.get(action)


def png_size(path):
    try:
        with open(path, 'rb') as handle:
            header = handle.read(24)
        if header[:16] == b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR':
            width, height = struct.unpack('>II', header[16:])
            if 0 < width <= 4096 and 0 < height <= 2160 and width * height <= 4096 * 2160:
                return width, height
    except (IOError, OSError, ValueError, struct.error):
        pass
    return None


def local_image(key, skin_root='/usr/share/enigma2'):
    if not key or not re.match(r'^[a-z0-9][a-z0-9+._-]{0,79}\Z', key):
        return None
    for base in (BUNDLED, CACHE):
        path = os.path.join(base, key + '.png')
        if png_size(path):
            return path
    normalize = lambda value: re.sub(r'[^a-z0-9]', '', value.lower())
    target = normalize(key)
    try:
        folders = os.listdir(skin_root)
    except OSError:
        folders = []
    # Only look within one folder matching the selected skin. Never substitute
    # another skin's preview, even when package names are similar.
    for folder in sorted(folders):
        if normalize(folder) != target:
            continue
        base = os.path.join(skin_root, folder)
        for name in ('prev.png', 'preview.png', 'screenshot.png', 'skin_preview.png',
                     'screenshots/prev.png', 'screenshots/preview.png',
                     'screens/preview.png'):
            path = os.path.join(base, name)
            if png_size(path):
                return path
    return None


def fetch_image(key):
    """Run on a worker. Publish complete PNGs by rename, keep at most 64 cached images."""
    if not key or not re.match(r'^[a-z0-9][a-z0-9+._-]{0,79}\Z', key):
        return None
    name = key + '.png'
    url = UPSTREAM.get(key, PROJECT + name)
    tmp = None
    try:
        source = urlopen(url, timeout=5)
        try:
            if not source.geturl().startswith('https://raw.githubusercontent.com/'):
                return None
            data = source.read(MAX_BYTES + 1)
        finally:
            source.close()
        if len(data) > MAX_BYTES or not data.endswith(b'\x00\x00\x00\x00IEND\xaeB\x60\x82'):
            return None
        if not os.path.isdir(CACHE):
            try:
                os.makedirs(CACHE, 0o700)
            except OSError:
                if not os.path.isdir(CACHE):
                    raise
        with tempfile.NamedTemporaryFile(dir=CACHE, prefix='.preview-', delete=False) as handle:
            tmp = handle.name
            handle.write(data)
        if not png_size(tmp):
            return None
        path = os.path.join(CACHE, name)
        os.rename(tmp, path)
        tmp = None
        old = [os.path.join(CACHE, n) for n in os.listdir(CACHE) if n.endswith('.png') and n != name]
        for item in sorted(old, key=os.path.getmtime, reverse=True)[63:]:
            os.unlink(item)
        return path
    except (IOError, OSError, ValueError):
        return None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
