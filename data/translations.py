# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

try:
    from Components.config import config
except Exception:
    config = None

from Plugins.SystemPlugins.PanelAIO import legacy_plugin

TRANSLATIONS = legacy_plugin.TRANSLATIONS
COL_TITLES = getattr(legacy_plugin, 'COL_TITLES', {})
FUNCTION_DESCRIPTIONS = getattr(legacy_plugin, 'FUNCTION_DESCRIPTIONS', {})


def detect_language():
    try:
        value = getattr(getattr(config.osd, 'language', None), 'value', '')
        if str(value).lower().startswith('pl'):
            return 'PL'
    except Exception:
        pass
    return 'EN'


def t(lang, key, default=''):
    lang = 'PL' if lang == 'PL' else 'EN'
    return TRANSLATIONS.get(lang, {}).get(key, default or key)
