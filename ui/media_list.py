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
try:
    from enigma import BT_SCALE
except ImportError:
    BT_SCALE = 0


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
                small_path = os.path.join(ASSETS, icon + '.png')
                if icon not in self.pixmaps:
                    large_path = os.path.join(ASSETS, 'large', icon + '.png')
                    path = large_path if BT_SCALE else small_path
                    self.pixmaps[icon] = LoadPixmap(path) if os.path.isfile(path) else None
                pixmap = self.pixmaps[icon]
                if pixmap is not None:
                    side = min(self.row_height - 6, 36) if BT_SCALE else 24
                    params = {'flags': BT_SCALE} if BT_SCALE else {}
                    try:
                        image = MultiContentEntryPixmapAlphaBlend(pos=(inset, (self.row_height-side)//2),
                            size=(side, side), png=pixmap, **params)
                    except TypeError:
                        if small_path not in self.pixmaps:
                            self.pixmaps[small_path] = LoadPixmap(small_path)
                        image = MultiContentEntryPixmapAlphaBlend(pos=(inset, (self.row_height-24)//2),
                            size=(24, 24), png=self.pixmaps[small_path])
                        side = 24
                    row.append(image)
                    inset += side + 7
            row.append(MultiContentEntryText(pos=(inset, 0), size=(self.row_width-inset-12, self.row_height),
                font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=label))
            rows.append(row)
        self.setList(rows)
