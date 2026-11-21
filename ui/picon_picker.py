# -*- coding: utf-8 -*-
from __future__ import absolute_import
from Plugins.SystemPlugins.PanelAIO.ui.media_details import PiconPackScreen


class PiconPreviewPicker(PiconPackScreen):
    """Keep the constructor used by callers of the 18.2.0 picker."""
    def __init__(self, session, choices, lang='PL'):
        title = 'Wybierz zestaw piconów' if lang == 'PL' else 'Choose picon package'
        PiconPackScreen.__init__(self, session, title, choices, lang)
