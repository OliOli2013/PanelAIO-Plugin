# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
from Components.MenuList import MenuList
from enigma import RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, gFont
from Components.MultiContent import MultiContentEntryPixmapAlphaBlend, MultiContentEntryText
from Tools.LoadPixmap import LoadPixmap
from Plugins.SystemPlugins.PanelAIO.core.compatibility import ensure_str
from Plugins.SystemPlugins.PanelAIO.data.navigation import TITLES

ASSETS = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icons')
CATEGORY_ICONS = dict((name, key) for key, pl, en in TITLES for name in (pl, en))


class MediaMenu(MenuList):
    def __init__(self, width, height, font):
        self.row_width, self.row_height = width, height
        self.pixmaps = {}
        MenuList.__init__(self, [], content=eListboxPythonMultiContent)
        self.l.setFont(0, gFont('Regular', font))
        self.l.setItemHeight(height)

    def set_rows(self, entries, icons):
        rows = []
        for label, icon in entries:
            label = ensure_str(label)
            row = [label]
            inset = 6
            if icons:
                if self.row_height >= 40:
                    side, folder = 36, 'medium'
                elif self.row_height >= 28:
                    side, folder = 24, ''
                else:
                    side, folder = 18, 'compact'
                if icon not in self.pixmaps:
                    path = os.path.join(ASSETS, folder, icon + '.png')
                    self.pixmaps[icon] = LoadPixmap(path) if os.path.isfile(path) else None
                pixmap = self.pixmaps[icon]
                if pixmap is not None:
                    image = MultiContentEntryPixmapAlphaBlend(pos=(inset, (self.row_height-side)//2),
                        size=(side, side), png=pixmap)
                    row.append(image)
                    inset += side + 7
            row.append(MultiContentEntryText(pos=(inset, 0), size=(self.row_width-inset-12, self.row_height),
                font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=label))
            rows.append(row)
        self.setList(rows)
