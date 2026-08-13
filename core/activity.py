# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import json
import os
import time

from Plugins.SystemPlugins.PanelAIO.core.compatibility import ensure_unicode
from Plugins.SystemPlugins.PanelAIO.core.runtime_safety import atomic_write

STATE_DIR = '/etc/enigma2'
STATE_FILE = os.path.join(STATE_DIR, '.panelaio_activity.json')
MAX_FAVORITES = 50
MAX_HISTORY = 30


def _default_state():
    return {'favorites': [], 'history': []}


def _load():
    try:
        with open(STATE_FILE, 'r') as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return _default_state()
        if not isinstance(data.get('favorites'), list):
            data['favorites'] = []
        if not isinstance(data.get('history'), list):
            data['history'] = []
        return data
    except Exception:
        return _default_state()


def _save(state):
    try:
        payload = json.dumps(state, ensure_ascii=True, sort_keys=True, indent=2)
        atomic_write(STATE_FILE, payload)
        return True
    except Exception:
        return False


def get_favorites():
    return list(_load().get('favorites', []))


def is_favorite(action):
    action = ensure_unicode(action)
    for item in get_favorites():
        if ensure_unicode(item.get('action')) == action:
            return True
    return False


def toggle_favorite(name, action):
    state = _load()
    action = ensure_unicode(action)
    name = ensure_unicode(name)
    favorites = []
    removed = False
    for item in state.get('favorites', []):
        if ensure_unicode(item.get('action')) == action:
            removed = True
            continue
        favorites.append(item)
    if not removed:
        favorites.insert(0, {'name': name, 'action': action, 'added': int(time.time())})
        favorites = favorites[:MAX_FAVORITES]
    state['favorites'] = favorites
    _save(state)
    return not removed


def record_recent(name, action):
    state = _load()
    action = ensure_unicode(action)
    name = ensure_unicode(name)
    history = []
    for item in state.get('history', []):
        if ensure_unicode(item.get('action')) == action:
            continue
        history.append(item)
    history.insert(0, {'name': name, 'action': action, 'time': int(time.time())})
    state['history'] = history[:MAX_HISTORY]
    _save(state)


def get_recent():
    return list(_load().get('history', []))
