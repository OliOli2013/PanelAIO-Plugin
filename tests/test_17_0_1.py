#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
def read(name):
    with open(os.path.join(ROOT, name), 'rb') as stream:
        return stream.read().decode('utf-8')

r = read('runtime.py')
m = read('data/menus.py')
b = read('build_ipk.sh')
safe = read('safe_ipk_install.sh')
for needle in ('PICON_SET_13E', 'PICON_SET_19E', 'PICON_SET_COMBINED',
               'def _prompt_picon_pack(self, title)',
               'def _prompt_picon_target(self, title, url)',
               'def _wizard_step_picons(self)'):
    assert needle in r, needle
for name in ('Picony.zip', 'Picony1.zip', 'Picony2.zip'):
    assert name in r, name
    assert "--exclude='./%s'" % name in b, name
assert 'super_setup_wizard' in r.lower()
assert 'Obsidian FHD' in r and 'Obsidian FHD' in m
assert 'safe_ipk:' in r and 'safe_ipk:' in m
assert 'enigma2-plugin-skins-obsidian-fhd' in r
assert 'enigma2-plugin-skins-obsidian-fhd' in m
assert 'opkg' in safe
assert 'https://olioli2013.github.io/aio-iptv-projekt' not in r
assert 'https://olioli2013.github.io/aio-iptv-projekt' not in read('ui/screens/connect.py')
assert 'https://aio-iptv-projekt.pages.dev/' in read('ui/screens/connect.py')
assert 'name="facebook"' not in r
assert 'self["facebook"]' not in r
assert 'self._update_channel_urls()[\'changelog\']' not in r[r.index('class AIOInfoScreen'):r.index('class AIOTextViewerScreen')]
assert 'STRONA AIO TEAM' in read('ui/modern.py')
assert '17.0.1' in read('control/postinst')
assert '17.0.1' in read('control/control')
assert '17.0.1' in read('version.txt')
for name in ('qr_site.png', 'qr_community.png', 'qr_report.png'):
    with open(os.path.join(ROOT, 'assets', 'modern', name), 'rb') as stream:
        assert stream.read(8) == b'\x89PNG\r\n\x1a\n', name
print('AIO Panel 17.0.1 static checks: OK (Python %s)' % sys.version.split()[0])
