# -*- coding: utf-8 -*-
"""Satellite picon pack picker with a truly transparent explanatory sample."""
from __future__ import absolute_import
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from Plugins.SystemPlugins.PanelAIO.core.picon_previews import sample_path, backdrop_path
from Plugins.SystemPlugins.PanelAIO.ui.appearance import desktop_size, fit_skin
from Plugins.SystemPlugins.PanelAIO.core.compatibility import ensure_str
import xml.etree.ElementTree as ET

SKIN = """<screen name="AIOPiconPreviewPicker" position="center,center" size="1000,540" title="AIO Panel - Picony" backgroundColor="#101B2A">
<widget name="title" position="26,22" size="945,39" font="Regular;30" foregroundColor="#77DAF0" transparent="1" />
<widget name="items" position="26,92" size="390,245" itemHeight="62" font="Regular;24" scrollbarMode="showOnDemand" backgroundColor="#1A293A" foregroundColor="#EAF3FB" foregroundColorSelected="#FFFFFF" backgroundColorSelected="#315A7A" />
<widget name="checker" position="482,91" size="480,245" alphatest="blend" scale="1" />
<widget name="logo" position="482,91" size="480,245" alphatest="blend" scale="1" />
<widget name="caption" position="484,340" size="471,68" font="Regular;17" foregroundColor="#A9BACE" transparent="1" />
<widget name="keys" position="27,455" size="940,57" font="Regular;21" foregroundColor="#D7E8F7" transparent="1" />
</screen>"""


class PiconPreviewPicker(Screen):
    def __init__(self, session, choices, lang='PL'):
        Screen.__init__(self, session)
        self.lang = lang
        self.choices = list(choices)[:3]
        self._dark = True
        self.skin = fit_skin(ET.fromstring(SKIN), desktop_size())
        self['title'] = Label('Podgląd piconów Transparent' if lang == 'PL' else 'Transparent picon preview')
        self['items'] = MenuList([ensure_str(item[0]) for item in self.choices])
        self['checker'] = Pixmap()
        self['logo'] = Pixmap()
        self['caption'] = Label('Próbka przezroczystości AIO (ilustracja). Nie pochodzi z paczki ZIP.' if lang == 'PL' else
                                'AIO transparency illustration, not a PNG extracted from the ZIP archive.')
        self['keys'] = Label(ensure_str('OK  Wybierz     •     ŻÓŁTY  Jasne/ciemne tło     •     EXIT  Wróć' if lang == 'PL' else
                                        'OK  Choose     •     YELLOW  Light/dark backdrop     •     EXIT  Back'))
        self['actions'] = ActionMap(['OkCancelActions', 'DirectionActions', 'ColorActions'],
                                    {'ok': self.accept, 'cancel': self.cancel, 'red': self.cancel,
                                     'yellow': self.toggle_backdrop,
                                     'up': self['items'].up, 'down': self['items'].down}, -1)
        self['items'].onSelectionChanged.append(self.render)
        self.onLayoutFinish.append(self.render)

    def render(self):
        try:
            index = self['items'].getSelectionIndex() or 0
            key = ('13e', '19e', 'combo')[min(max(index, 0), 2)]
            if self['checker'].instance is not None:
                self['checker'].instance.setPixmapFromFile(backdrop_path(self._dark))
            if self['logo'].instance is not None:
                self['logo'].instance.setPixmapFromFile(sample_path(key))
        except Exception as error:
            print('[AIO Panel] picon preview error:', error)

    def toggle_backdrop(self):
        self._dark = not self._dark
        self.render()

    def accept(self):
        index = self['items'].getSelectionIndex()
        if index is not None and 0 <= index < len(self.choices):
            self.close(self.choices[index])
        else:
            self.close(None)

    def cancel(self):
        self.close(None)
