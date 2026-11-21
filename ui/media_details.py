# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import os
from threading import Thread
from twisted.internet import reactor
import xml.etree.ElementTree as ET

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from skin import parseColor

from Plugins.SystemPlugins.PanelAIO.core.compatibility import ensure_str
from Plugins.SystemPlugins.PanelAIO.core.media_catalog import PICON_FILES, ROOT
from Plugins.SystemPlugins.PanelAIO.ui.appearance import (
    PreviewScreen, desktop_size, fit_skin, place_preview, preferences, themed_skin)

PACK_SKIN = '''<screen position="center,center" size="940,360" backgroundColor="#07111D">
<widget name="rows" position="22,42" size="396,222" font="Regular;24" itemHeight="52" scrollbarMode="showNever" foregroundColor="#D8E3ED" backgroundColor="#0D1A29" backgroundColorSelected="#195374" />
<widget name="backdrop" position="438,26" size="480,228" zPosition="1" backgroundColor="#182633" />
<widget name="sample" position="448,36" size="460,208" zPosition="2" scale="1" alphatest="blend" transparent="1" />
<widget name="caption" position="434,264" size="484,34" font="Regular;20" halign="center" transparent="1" foregroundColor="#D8E3ED" />
<widget name="keys" position="18,313" size="904,32" font="Regular;20" halign="center" transparent="1" foregroundColor="#AFC0D1" />
</screen>'''
CARD_SKIN = '''<screen position="center,center" size="830,360" backgroundColor="#07111D">
<widget name="icon" position="28,30" size="106,106" scale="1" alphatest="blend" />
<widget name="title" position="158,27" size="644,72" font="Regular;29" foregroundColor="#F2F7FC" transparent="1" />
<widget name="source" position="158,108" size="644,60" font="Regular;19" foregroundColor="#00C2FF" transparent="1" />
<widget name="body" position="28,178" size="774,129" font="Regular;22" foregroundColor="#D8E3ED" transparent="1" />
<widget name="keys" position="28,315" size="774,28" font="Regular;18" foregroundColor="#8FA7BE" transparent="1" />
</screen>'''


class FeatureCardScreen(Screen):
    def __init__(self, session, title, kind, body, source, icon, lang, package=None):
        Screen.__init__(self, session)
        self.skin = fit_skin(themed_skin(CARD_SKIN, preferences()[0]), desktop_size())
        self.setTitle(ensure_str(kind))
        self.package = package
        self.busy = False
        self._card_open = True
        self.lang = lang
        self.card_title = title
        self.onClose.append(self._finish)
        self['title'] = Label(ensure_str(title))
        self['body'] = Label(ensure_str(body))
        self['source'] = Label(ensure_str(source))
        self['keys'] = Label(ensure_str('OK / EXIT  ·  Wróć' if lang == 'PL' else 'OK / EXIT  ·  Back'))
        if package:
            self['keys'].setText(ensure_str('Zielony  ·  Szukaj zdjęcia w pakiecie     EXIT  ·  Wróć' if lang == 'PL'
                                            else 'Green  ·  Find picture in package     EXIT  ·  Back'))
        self['icon'] = Pixmap()
        self['actions'] = ActionMap(['ColorActions', 'OkCancelActions', 'InfobarEPGActions', 'InfoActions'], {
            'green': self.search, 'ok': self.close, 'cancel': self.close, 'showEventInfo': self.close, 'info': self.close}, -1)
        self._icon_path = icon
        self.onLayoutFinish.append(self.show_icon)

    def show_icon(self):
        widget = self['icon']
        if widget.instance is not None:
            widget.instance.setPixmapFromFile(ensure_str(self._icon_path))

    def _finish(self):
        self._card_open = False

    def search(self):
        if not self.package or self.busy:
            return
        from Plugins.SystemPlugins.PanelAIO.core import skin_feed, skin_previews
        package = self.package
        key = skin_previews.skin_id('feed:native-' + package)
        self.busy = True
        self['keys'].setText(ensure_str('Szukam zdjęcia w pakiecie…' if self.lang == 'PL' else 'Looking for a package preview…'))

        def find():
            try:
                path = skin_feed.fetch(package, key)
            except Exception:
                path = None
            reactor.callFromThread(self._result, path)
        worker = Thread(target=find)
        worker.daemon = True
        worker.start()

    def _result(self, path):
        if not getattr(self, '_card_open', False):
            return
        self.busy = False
        if path:
            self['keys'].setText(ensure_str('EXIT  ·  Wróć' if self.lang == 'PL' else 'EXIT  ·  Back'))
            self.session.open(PreviewScreen, self.card_title, path, lang=self.lang)
        else:
            self['keys'].setText(ensure_str('Brak dostępnego zdjęcia w pakiecie.   EXIT  ·  Wróć' if self.lang == 'PL'
                                            else 'No package preview available.   EXIT  ·  Back'))


class PiconPackScreen(Screen):
    def __init__(self, session, title, choices, lang):
        Screen.__init__(self, session)
        self.skin = fit_skin(themed_skin(PACK_SKIN, preferences()[0]), desktop_size())
        self.setTitle(ensure_str(title))
        self.lang = lang
        self.choices = choices
        self.light_background = False
        self['rows'] = MenuList([ensure_str(choice[0]) for choice in choices])
        self['sample'] = Pixmap()
        self['backdrop'] = Label('')
        self['caption'] = Label(ensure_str('Picony na przezroczystym tle' if lang == 'PL' else 'Picons with a transparent background'))
        self['keys'] = Label(ensure_str('OK  ·  Wybierz     INFO  ·  Powiększ     Żółty  ·  Zmień tło     EXIT  ·  Wróć' if lang == 'PL'
                                       else 'OK  ·  Select     INFO  ·  Enlarge     Yellow  ·  Change background     EXIT  ·  Back'))
        self['actions'] = ActionMap(['DirectionActions', 'OkCancelActions', 'ColorActions', 'InfobarEPGActions', 'InfoActions'], {
            'up': self['rows'].up, 'down': self['rows'].down, 'ok': self.select, 'cancel': lambda: self.close(None),
            'yellow': self.toggle_background, 'info': self.enlarge, 'showEventInfo': self.enlarge}, -1)
        rect = ET.fromstring(self.skin).find("widget[@name='sample']")
        self.rect = tuple(int(n) for n in (rect.get('position') + ',' + rect.get('size')).split(','))
        self['rows'].onSelectionChanged.append(self.refresh)
        self.onLayoutFinish.append(self.refresh)

    def current_index(self):
        return max(0, min(len(self.choices) - 1, self['rows'].getSelectionIndex() or 0))

    def sample_path(self):
        return os.path.join(ROOT, 'picons', PICON_FILES[self.current_index()] + '.png')

    def refresh(self):
        if self['sample'].instance is not None:
            place_preview(self['sample'], self.sample_path(), self.rect)

    def toggle_background(self):
        self.light_background = not self.light_background
        self['backdrop'].instance.setBackgroundColor(parseColor('#E7EBEE' if self.light_background else '#182633'))

    def enlarge(self):
        title = self.choices[self.current_index()][0]
        background = '#E7EBEE' if self.light_background else '#182633'
        self.session.open(PreviewScreen, title, self.sample_path(), background=background, lang=self.lang)

    def select(self):
        self.close(self.choices[self.current_index()])
