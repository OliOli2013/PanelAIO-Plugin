# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

"""Main dashboard bridge for the modular architecture.

All sections are migrated at once by delegating runtime behavior to the full
compatibility layer in legacy_plugin.py. This keeps every existing menu section
available while allowing the next refactor steps to happen inside core/, ui/
and data/ without another big-bang move.
"""

from Plugins.SystemPlugins.PanelAIO import legacy_plugin
from Plugins.SystemPlugins.PanelAIO.data.menus import build_static_tabs
from Plugins.SystemPlugins.PanelAIO.data.translations import detect_language


def _safe_build_tabs(lang):
    try:
        return build_static_tabs(lang)
    except Exception:
        return []


ALL_TABS_PL = _safe_build_tabs('PL')
ALL_TABS_EN = _safe_build_tabs('EN')


def open_main(session, lang=None, **kwargs):
    lang = lang or detect_language()
    return legacy_plugin.main(session, **kwargs)


def menu_entries(menuid, **kwargs):
    return legacy_plugin.menu(menuid, **kwargs)


def sessionstart_hook(reason, session=None, **kwargs):
    return legacy_plugin.sessionstart(reason, session=session, **kwargs)
