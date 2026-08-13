# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

try:
    from Components.config import config
except Exception:
    config = None

from Plugins.SystemPlugins.PanelAIO import runtime

TRANSLATIONS = runtime.TRANSLATIONS
COL_TITLES = getattr(runtime, 'COL_TITLES', {})
FUNCTION_DESCRIPTIONS = getattr(runtime, 'FUNCTION_DESCRIPTIONS', {})


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
