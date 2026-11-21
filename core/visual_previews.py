# -*- coding: utf-8 -*-
"""Truthful visual cards for installation actions; real skin images stay separate."""
from __future__ import absolute_import
import os
from . import skin_previews

ROOT = os.path.dirname(os.path.dirname(__file__))
CARDS = os.path.join(ROOT, 'assets', 'cards')


def preview_id(action):
    if not action:
        return None
    key = skin_previews.skin_id(action)
    if key:
        return 'skin:' + key
    value = action.lower()
    if 'picon' in value:
        return 'card:picons'
    if 'oscam' in value or 'softcam' in value or 'dvbapi' in value:
        return 'card:softcam'
    if 'e2iplayer' in value or 'serviceapp' in value or 'streamlink' in value:
        return 'card:video'
    if 'open_cam' in value or 'opencamview' in value or 'onvif' in value:
        return 'card:camera'
    if 'neoradio' in value or 'radio' in value:
        return 'card:radio'
    if 'channel' in value or 'bouquet' in value or 'liste' in value or 'lists' in value:
        return 'card:channels'
    if 'epg' in value:
        return 'card:epg'
    if 'iptv' in value or 'xtream' in value or 'jedi' in value:
        return 'card:iptv'
    if 'backup' in value or 'restore' in value:
        return 'card:backup'
    if 'repair' in value or 'diagnostic' in value:
        return 'card:repair'
    if 'update' in value:
        return 'card:update'
    if 'network' in value or 'connect' in value:
        return 'card:network'
    if 'weather' in value:
        return 'card:weather'
    if 'webif' in value or 'explorer' in value or 'commander' in value:
        return 'card:browser'
    if 'plugin' in value or 'extensions' in value:
        return 'card:plugins'
    if value.startswith(('safe_ipk:', 'remote_script:', 'feed:', 'archive:',
                         's4archive:', 'bash_raw:', 'opkg:', 'picons:')) or 'install' in value:
        return 'card:install'
    return None


def actual_skin_image(key):
    if not key or not key.startswith('skin:'):
        return None
    return skin_previews.local_image(key[5:])


def local_image(key):
    if not key:
        return None
    if key.startswith('skin:'):
        return actual_skin_image(key) or os.path.join(CARDS, 'skins-missing.png')
    if key.startswith('card:'):
        name = key[5:]
        # No user-supplied path fragments are permitted.
        if name not in ('picons', 'softcam', 'video', 'camera', 'radio', 'channels',
                        'epg', 'iptv', 'backup', 'repair', 'update', 'network',
                        'weather', 'browser', 'plugins', 'install', 'system'):
            return None
        return os.path.join(CARDS, name + '.png')
    return None


def actual_photo(key):
    return bool(key and key.startswith('skin:') and actual_skin_image(key))


def fetch_image(key):
    if not key or not key.startswith('skin:'):
        return None
    return skin_previews.fetch_image(key[5:])
