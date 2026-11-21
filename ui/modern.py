# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

"""Modern AIO Panel dashboard.

The visual layer is independent from the legacy action engine.  This keeps every
existing installer and maintenance workflow available while replacing the main
navigation, status presentation and graphics with an adaptive HD/FHD interface.
The module intentionally uses Python 2.7 compatible syntax.
"""

import datetime
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from threading import Thread

from Components.Label import Label
from Components.Pixmap import Pixmap
try:
    from Components.config import config
except Exception:
    config = None

from Plugins.SystemPlugins.PanelAIO import runtime as legacy
from Plugins.SystemPlugins.PanelAIO.core import media_catalog, skin_previews
from Plugins.SystemPlugins.PanelAIO.ui.appearance import (
    AppearanceScreen, PreviewScreen, PALETTES, apply_colors, fit_skin, preferences, themed_skin, place_preview)
from Plugins.SystemPlugins.PanelAIO.ui.media_details import FeatureCardScreen
from Plugins.SystemPlugins.PanelAIO.ui.media_list import CATEGORY_ICONS, MediaMenu
from Plugins.SystemPlugins.PanelAIO.core.plugin_state import status_text as _plugin_status_text

PLUGIN_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
ASSET_PATH = os.path.join(PLUGIN_PATH, 'assets', 'modern')


def _asset(name):
    return os.path.join(ASSET_PATH, name)


def _screen_mode():
    try:
        width, height = legacy._desktop_size()
    except Exception:
        width, height = (1280, 720)
    if width <= 1024 or height <= 576:
        return 'small'
    if width <= 1280 or height <= 720:
        return 'hd'
    return 'fhd'


def _dashboard_template():
    """Dashboard skin without static eLabel overlays.

    Several Enigma2 images render static eLabel elements above dynamic widgets
    regardless of zPosition.  Large background eLabels therefore hid MenuList
    and Label content.  This skin uses the Screen background and each widget's
    own background only, so the content remains visible across images.
    """
    mode = _screen_mode()
    logo = os.path.join(PLUGIN_PATH, 'logo_original_14.png')
    if mode == 'small':
        return """
<screen name="PanelAIOModern150" position="center,center" size="900,560" title="AIO Panel" backgroundColor="#07111D" zPosition="99" borderWidth="2" borderColor="#1E789E">
    <widget name="brand_logo" position="18,10" size="56,56" pixmap="%s" alphatest="blend" scale="1" />
    <widget name="title_label" position="88,10" size="340,30" font="Regular;26" foregroundColor="#F2F7FC" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="support_label" position="88,41" size="360,22" font="Regular;16" foregroundColor="#8FA7BE" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="health" position="442,14" size="385,20" font="Regular;15" halign="right" foregroundColor="#8FA7BE" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="clock" position="442,39" size="385,24" font="Regular;19" halign="right" foregroundColor="#00C2FF" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="qr_code_small" position="842,18" size="38,38" pixmap="%s" alphatest="blend" scale="1" />
    <widget name="qr_support_label" position="798,58" size="82,16" font="Regular;11" halign="center" foregroundColor="#FFD24A" backgroundColor="#07111D" transparent="0" />
    <widget name="pp_logo" position="0,0" size="0,0" transparent="1" />

    <widget name="sidebar" position="13,88" size="214,374" itemHeight="42" font="Regular;18" scrollbarMode="showOnDemand" selectionPixmap="%s" foregroundColor="#B9C8D8" foregroundColorSelected="#FFFFFF" backgroundColor="#0D1A29" transparent="0" />
    <widget name="category_title" position="246,88" size="364,36" font="Regular;21" valign="center" foregroundColor="#00C2FF" backgroundColor="#0D1A29" transparent="0" />
    <widget name="item_counter" position="610,88" size="56,36" font="Regular;16" halign="right" valign="center" foregroundColor="#8298AE" backgroundColor="#0D1A29" transparent="0" />
    <widget name="menu" position="246,132" size="420,330" itemHeight="40" font="Regular;18" scrollbarMode="showOnDemand" selectionPixmap="%s" foregroundColor="#D8E3ED" foregroundColorSelected="#FFFFFF" backgroundColor="#0D1A29" transparent="0" />

    <widget name="item_icon" position="697,98" size="42,42" alphatest="blend" scale="1" />
    <widget name="category_icon" position="750,94" size="80,80" alphatest="blend" scale="1" />
    <widget name="detail_title" position="692,184" size="186,52" font="Regular;19" halign="center" valign="center" foregroundColor="#F2F7FC" backgroundColor="#0D1A29" transparent="0" />
    <widget name="detail_body" position="692,238" size="186,104" font="Regular;15" halign="left" valign="top" foregroundColor="#AFC0D1" backgroundColor="#0D1A29" transparent="0" />
    <widget name="image_value" position="692,350" size="186,20" font="Regular;14" foregroundColor="#8FA7BE" backgroundColor="#0D1A29" transparent="0" />
    <widget name="python_value" position="692,374" size="186,20" font="Regular;14" foregroundColor="#8FA7BE" backgroundColor="#0D1A29" transparent="0" />
    <widget name="flash_value" position="692,398" size="186,20" font="Regular;14" foregroundColor="#8FA7BE" backgroundColor="#0D1A29" transparent="0" />
    <widget name="cpu_value" position="692,422" size="88,20" font="Regular;14" foregroundColor="#57D99B" backgroundColor="#0D1A29" transparent="0" />
    <widget name="ram_value" position="790,422" size="88,20" font="Regular;14" halign="right" foregroundColor="#57D99B" backgroundColor="#0D1A29" transparent="0" />
    <widget name="net_value" position="692,446" size="186,16" font="Regular;13" foregroundColor="#00C2FF" backgroundColor="#0D1A29" transparent="0" />

    <widget name="update_status" position="18,476" size="320,20" font="Regular;15" foregroundColor="#FFD24A" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="key_red" position="18,505" size="196,25" font="Regular;16" foregroundColor="#FF7381" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="key_green" position="226,505" size="196,25" font="Regular;16" foregroundColor="#4CDB91" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="key_yellow" position="434,505" size="210,25" font="Regular;16" foregroundColor="#FFD24A" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="key_blue" position="656,505" size="160,25" font="Regular;16" foregroundColor="#4CA3FF" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="footer" position="18,536" size="798,18" font="Regular;13" halign="center" foregroundColor="#70879D" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="site_qr_label" position="704,480" size="174,18" font="Regular;12" halign="right" foregroundColor="#00C2FF" backgroundColor="#07111D" transparent="0" />
    <widget name="site_qr" position="833,505" size="48,48" alphatest="blend" scale="1" />
    <widget name="function_description" position="0,0" size="0,0" font="Regular;1" transparent="1" />
    <widget name="legend" position="0,0" size="0,0" font="Regular;1" transparent="1" />
    <widget name="tabs_display" position="0,0" size="0,0" font="Regular;1" transparent="1" />
</screen>""" % (logo, legacy.PLUGIN_QR_CODE_SMALL_PATH, _asset('sel_sidebar_small.png'), _asset('sel_menu_small.png'))
    if mode == 'hd':
        return """
<screen name="PanelAIOModern150" position="center,center" size="1180,680" title="AIO Panel" backgroundColor="#07111D" zPosition="99" borderWidth="2" borderColor="#1E789E">
    <widget name="brand_logo" position="22,12" size="68,68" pixmap="%s" alphatest="blend" scale="1" />
    <widget name="title_label" position="108,15" size="420,34" font="Regular;30" foregroundColor="#F2F7FC" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="support_label" position="108,52" size="430,24" font="Regular;18" foregroundColor="#8FA7BE" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="health" position="560,17" size="530,22" font="Regular;17" halign="right" foregroundColor="#8FA7BE" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="clock" position="560,48" size="530,28" font="Regular;22" halign="right" foregroundColor="#00C2FF" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="qr_code_small" position="1110,19" size="50,50" pixmap="%s" alphatest="blend" scale="1" />
    <widget name="qr_support_label" position="1048,72" size="112,18" font="Regular;13" halign="center" foregroundColor="#FFD24A" backgroundColor="#07111D" transparent="0" />
    <widget name="pp_logo" position="0,0" size="0,0" transparent="1" />

    <widget name="sidebar" position="22,108" size="260,476" itemHeight="50" font="Regular;21" scrollbarMode="showOnDemand" selectionPixmap="%s" foregroundColor="#B9C8D8" foregroundColorSelected="#FFFFFF" backgroundColor="#0D1A29" transparent="0" />
    <widget name="category_title" position="306,108" size="470,42" font="Regular;25" valign="center" foregroundColor="#00C2FF" backgroundColor="#0D1A29" transparent="0" />
    <widget name="item_counter" position="780,108" size="86,42" font="Regular;18" halign="right" valign="center" foregroundColor="#8298AE" backgroundColor="#0D1A29" transparent="0" />
    <widget name="menu" position="306,158" size="560,426" itemHeight="46" font="Regular;21" scrollbarMode="showOnDemand" selectionPixmap="%s" foregroundColor="#D8E3ED" foregroundColorSelected="#FFFFFF" backgroundColor="#0D1A29" transparent="0" />

    <widget name="item_icon" position="900,120" size="54,54" alphatest="blend" scale="1" />
    <widget name="category_icon" position="976,116" size="92,92" alphatest="blend" scale="1" />
    <widget name="detail_title" position="896,218" size="252,64" font="Regular;23" halign="center" valign="center" foregroundColor="#F2F7FC" backgroundColor="#0D1A29" transparent="0" />
    <widget name="detail_body" position="896,290" size="252,132" font="Regular;17" halign="left" valign="top" foregroundColor="#AFC0D1" backgroundColor="#0D1A29" transparent="0" />
    <widget name="image_value" position="896,438" size="252,22" font="Regular;16" foregroundColor="#8FA7BE" backgroundColor="#0D1A29" transparent="0" />
    <widget name="python_value" position="896,466" size="252,22" font="Regular;16" foregroundColor="#8FA7BE" backgroundColor="#0D1A29" transparent="0" />
    <widget name="flash_value" position="896,494" size="252,22" font="Regular;16" foregroundColor="#8FA7BE" backgroundColor="#0D1A29" transparent="0" />
    <widget name="cpu_value" position="896,522" size="118,22" font="Regular;16" foregroundColor="#57D99B" backgroundColor="#0D1A29" transparent="0" />
    <widget name="ram_value" position="1030,522" size="118,22" font="Regular;16" halign="right" foregroundColor="#57D99B" backgroundColor="#0D1A29" transparent="0" />
    <widget name="net_value" position="896,550" size="252,22" font="Regular;16" foregroundColor="#00C2FF" backgroundColor="#0D1A29" transparent="0" />

    <widget name="update_status" position="22,604" size="380,22" font="Regular;17" foregroundColor="#FFD24A" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="footer" position="430,604" size="650,22" font="Regular;15" halign="right" foregroundColor="#70879D" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="site_qr_label" position="956,576" size="192,20" font="Regular;14" halign="right" foregroundColor="#00C2FF" backgroundColor="#07111D" transparent="0" />
    <widget name="site_qr" position="1094,599" size="64,64" alphatest="blend" scale="1" />
    <widget name="key_red" position="22,640" size="250,26" font="Regular;18" foregroundColor="#FF7381" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="key_green" position="284,640" size="250,26" font="Regular;18" foregroundColor="#4CDB91" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="key_yellow" position="546,640" size="276,26" font="Regular;18" foregroundColor="#FFD24A" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="key_blue" position="834,640" size="246,26" font="Regular;18" foregroundColor="#4CA3FF" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="function_description" position="0,0" size="0,0" font="Regular;1" transparent="1" />
    <widget name="legend" position="0,0" size="0,0" font="Regular;1" transparent="1" />
    <widget name="tabs_display" position="0,0" size="0,0" font="Regular;1" transparent="1" />
</screen>""" % (logo, legacy.PLUGIN_QR_CODE_SMALL_PATH, _asset('sel_sidebar_hd.png'), _asset('sel_menu_hd.png'))
    return """
<screen name="PanelAIOModern150" position="center,center" size="1560,900" title="AIO Panel" backgroundColor="#07111D" zPosition="99" borderWidth="2" borderColor="#1E789E">
    <widget name="brand_logo" position="30,16" size="86,86" pixmap="%s" alphatest="blend" scale="1" />
    <widget name="title_label" position="138,20" size="570,44" font="Regular;40" foregroundColor="#F2F7FC" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="support_label" position="138,70" size="590,28" font="Regular;23" foregroundColor="#8FA7BE" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="health" position="740,22" size="690,28" font="Regular;22" halign="right" foregroundColor="#8FA7BE" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="clock" position="740,62" size="690,34" font="Regular;28" halign="right" foregroundColor="#00C2FF" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="qr_code_small" position="1450,24" size="70,70" pixmap="%s" alphatest="blend" scale="1" />
    <widget name="qr_support_label" position="1388,98" size="132,24" font="Regular;17" halign="center" foregroundColor="#FFD24A" backgroundColor="#07111D" transparent="0" />
    <widget name="pp_logo" position="0,0" size="0,0" transparent="1" />

    <widget name="sidebar" position="32,140" size="330,632" itemHeight="64" font="Regular;28" scrollbarMode="showOnDemand" selectionPixmap="%s" foregroundColor="#B9C8D8" foregroundColorSelected="#FFFFFF" backgroundColor="#0D1A29" transparent="0" />
    <widget name="category_title" position="394,140" size="610,56" font="Regular;33" valign="center" foregroundColor="#00C2FF" backgroundColor="#0D1A29" transparent="0" />
    <widget name="item_counter" position="1005,140" size="109,56" font="Regular;23" halign="right" valign="center" foregroundColor="#8298AE" backgroundColor="#0D1A29" transparent="0" />
    <widget name="menu" position="394,210" size="720,562" itemHeight="58" font="Regular;28" scrollbarMode="showOnDemand" selectionPixmap="%s" foregroundColor="#D8E3ED" foregroundColorSelected="#FFFFFF" backgroundColor="#0D1A29" transparent="0" />

    <widget name="item_icon" position="1160,158" size="82,82" alphatest="blend" scale="1" />
    <widget name="category_icon" position="1282,152" size="128,128" alphatest="blend" scale="1" />
    <widget name="detail_title" position="1154,300" size="360,84" font="Regular;31" halign="center" valign="center" foregroundColor="#F2F7FC" backgroundColor="#0D1A29" transparent="0" />
    <widget name="detail_body" position="1154,398" size="360,186" font="Regular;24" halign="left" valign="top" foregroundColor="#AFC0D1" backgroundColor="#0D1A29" transparent="0" />
    <widget name="image_value" position="1154,606" size="360,30" font="Regular;22" foregroundColor="#8FA7BE" backgroundColor="#0D1A29" transparent="0" />
    <widget name="python_value" position="1154,644" size="360,30" font="Regular;22" foregroundColor="#8FA7BE" backgroundColor="#0D1A29" transparent="0" />
    <widget name="flash_value" position="1154,682" size="360,30" font="Regular;22" foregroundColor="#8FA7BE" backgroundColor="#0D1A29" transparent="0" />
    <widget name="cpu_value" position="1154,720" size="170,30" font="Regular;22" foregroundColor="#57D99B" backgroundColor="#0D1A29" transparent="0" />
    <widget name="ram_value" position="1344,720" size="170,30" font="Regular;22" halign="right" foregroundColor="#57D99B" backgroundColor="#0D1A29" transparent="0" />
    <widget name="net_value" position="1154,758" size="360,30" font="Regular;22" foregroundColor="#00C2FF" backgroundColor="#0D1A29" transparent="0" />

    <widget name="update_status" position="30,808" size="500,28" font="Regular;22" foregroundColor="#FFD24A" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="footer" position="560,808" size="840,28" font="Regular;20" halign="right" foregroundColor="#70879D" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="site_qr_label" position="1230,772" size="284,24" font="Regular;18" halign="right" foregroundColor="#00C2FF" backgroundColor="#07111D" transparent="0" />
    <widget name="site_qr" position="1422,798" size="96,96" alphatest="blend" scale="1" />
    <widget name="key_red" position="30,852" size="330,32" font="Regular;24" foregroundColor="#FF7381" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="key_green" position="378,852" size="330,32" font="Regular;24" foregroundColor="#4CDB91" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="key_yellow" position="726,852" size="370,32" font="Regular;24" foregroundColor="#FFD24A" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="key_blue" position="1114,852" size="286,32" font="Regular;24" foregroundColor="#4CA3FF" backgroundColor="#0E1C2C" transparent="0" />
    <widget name="function_description" position="0,0" size="0,0" font="Regular;1" transparent="1" />
    <widget name="legend" position="0,0" size="0,0" font="Regular;1" transparent="1" />
    <widget name="tabs_display" position="0,0" size="0,0" font="Regular;1" transparent="1" />
</screen>""" % (logo, legacy.PLUGIN_QR_CODE_SMALL_PATH, _asset('sel_sidebar_fhd.png'), _asset('sel_menu_fhd.png'))

def _modern_skin(theme='ocean'):
    root = themed_skin(_dashboard_template(), theme)
    mode = _screen_mode()
    geometry = {'small': ('692,350', '186,104'), 'hd': ('896,430', '252,142'),
                'fhd': ('1154,586', '352,198')}
    pos, size = geometry[mode]
    ET.SubElement(root, 'widget', name='skin_preview', position=pos, size=size, scale='1', alphatest='blend')
    root.set('name', 'PanelAIODashboard181')
    for name in ('sidebar', 'menu'):
        node = root.find("widget[@name='%s']" % name)
        node.attrib.pop('selectionPixmap', None)
        node.set('backgroundColorSelected', PALETTES[theme][-1])
    return fit_skin(root, legacy._desktop_size())


def _loading_skin():
    mode = _screen_mode()
    logo = os.path.join(PLUGIN_PATH, 'logo_original_14.png')
    if mode == 'small':
        return """
<screen name="AIOModernLoading150" position="center,center" size="720,340" title="AIO Panel" backgroundColor="#07111D">
    <eLabel position="0,0" size="720,340" backgroundColor="#07111D"  zPosition="-10" />
    <eLabel position="0,0" size="720,78" backgroundColor="#0E1C2C"  zPosition="-10" />
    <widget name="logo" position="22,13" size="52,52" pixmap="%s" alphatest="blend" scale="1" />
    <widget name="title" position="92,15" size="470,32" font="Regular;27" foregroundColor="#F2F7FC" transparent="1" />
    <widget name="version" position="562,20" size="136,24" font="Regular;18" halign="right" foregroundColor="#00C2FF" transparent="1" />
    <widget name="stage" position="92,49" size="600,20" font="Regular;16" foregroundColor="#8FA7BE" transparent="1" />
    <widget name="message" position="34,104" size="652,130" font="Regular;22" halign="center" valign="center" foregroundColor="#D8E3ED" transparent="1" />
    <eLabel position="34,252" size="652,1" backgroundColor="#1E789E"  zPosition="-10" />
    <widget name="tip" position="42,270" size="636,52" font="Regular;16" halign="center" valign="center" foregroundColor="#8FA7BE" transparent="1" />
</screen>""" % logo
    return """
<screen name="AIOModernLoading150" position="center,center" size="900,430" title="AIO Panel" backgroundColor="#07111D">
    <eLabel position="0,0" size="900,430" backgroundColor="#07111D"  zPosition="-10" />
    <eLabel position="0,0" size="900,98" backgroundColor="#0E1C2C"  zPosition="-10" />
    <widget name="logo" position="28,16" size="66,66" pixmap="%s" alphatest="blend" scale="1" />
    <widget name="title" position="118,20" size="560,38" font="Regular;33" foregroundColor="#F2F7FC" transparent="1" />
    <widget name="version" position="690,25" size="180,28" font="Regular;22" halign="right" foregroundColor="#00C2FF" transparent="1" />
    <widget name="stage" position="118,62" size="750,24" font="Regular;20" foregroundColor="#8FA7BE" transparent="1" />
    <widget name="message" position="46,132" size="808,160" font="Regular;28" halign="center" valign="center" foregroundColor="#D8E3ED" transparent="1" />
    <eLabel position="46,322" size="808,1" backgroundColor="#1E789E"  zPosition="-10" />
    <widget name="tip" position="58,344" size="784,62" font="Regular;20" halign="center" valign="center" foregroundColor="#8FA7BE" transparent="1" />
</screen>""" % logo


def _system_language():
    try:
        value = getattr(getattr(config.osd, 'language', None), 'value', '')
        if str(value).lower().startswith('pl'):
            return 'PL'
    except Exception:
        pass
    return 'EN'


def _strip_leading_symbol(value):
    text = legacy.ensure_unicode(value).strip()
    try:
        text = re.sub(u'^[^\\w]+', u'', text, flags=re.UNICODE)
    except Exception:
        pass
    return text.strip()


def _truncate(text, limit):
    value = legacy.ensure_unicode(text).replace('\r', ' ').strip()
    if len(value) <= limit:
        return value
    return value[:max(0, limit - 1)].rstrip() + u'…'


class ModernPanelAIO(legacy.PanelAIO):
    modern_skin_name = ['PanelAIODashboard181']

    def __init__(self, session, fetched_data):
        self.theme, self.show_icons, self.show_previews = preferences()
        self.skin = _modern_skin(self.theme)
        self._dashboard_xml = ET.fromstring(self.skin)
        self._media_ready = False
        self._preview_key = None
        self._preview_path = None
        self._media = None
        self._detail_text = u''
        self._preview_timer = None
        self._fetching_key = None
        self._miss_until = {}
        self._pixel_paths = {}
        self._setting_tabs = False
        legacy.PanelAIO.__init__(self, session, fetched_data)
        self['skin_preview'] = Pixmap()
        self.onClose.append(self._cancel_preview_timer)
        self['brand_logo'] = Pixmap()
        self['category_icon'] = Pixmap()
        self['item_icon'] = Pixmap()
        self['site_qr'] = Pixmap()
        self['appearance_actions'] = legacy.ActionMap(['MenuActions'], {'menu': self.open_appearance}, -1)
        self['qr_support_label'] = Label('')
        self['site_qr_label'] = Label('')
        self['category_title'] = Label('')
        self['item_counter'] = Label('')
        self['clock'] = Label('')
        self['detail_title'] = Label('')
        self['detail_body'] = Label('')
        self['image_value'] = Label('')
        self['python_value'] = Label('')
        self['flash_value'] = Label('')
        self['cpu_value'] = Label('')
        self['ram_value'] = Label('')
        self['net_value'] = Label('')
        self['key_red'] = Label('')
        self['key_green'] = Label('')
        self['key_yellow'] = Label('')
        self['key_blue'] = Label('')
        self._modern_image_name = self._detect_image_name()
        self['menu'].onSelectionChanged.append(self._modern_selection_changed)
        self.onLayoutFinish.append(self._modern_layout_ready)

    def _make_menu(self, role):
        node = self._dashboard_xml.find("widget[@name='%s']" % role)
        return MediaMenu(int(node.get('size').split(',')[0]), int(node.get('itemHeight')),
                        int(node.get('font').split(';')[-1]))

    def _on_sidebar_changed(self):
        if not self._setting_tabs:
            legacy.PanelAIO._on_sidebar_changed(self)

    def open_appearance(self):
        self.sess.openWithCallback(self._appearance_saved, AppearanceScreen, self.lang)

    def _appearance_saved(self, saved=False):
        if not saved:
            return
        self.theme, self.show_icons, self.show_previews = preferences()
        self.skin = _modern_skin(self.theme)
        self._dashboard_xml = ET.fromstring(self.skin)
        apply_colors(self, self._dashboard_xml)
        index = self._get_list_index(self['menu'])
        self._set_sidebar_tabs(self.tabs)
        self.switch_tab(self.active_tab)
        self['menu'].moveToIndex(index)
        self._refresh_modern_ui()

    def _detect_image_name(self):
        candidates = [
            ('/etc/image-version', ('imagename=', 'distro=', 'imageversion=')),
            ('/etc/issue', ()),
            ('/etc/vtiversion.info', ()),
        ]
        for path, keys in candidates:
            try:
                if not os.path.exists(path):
                    continue
                with open(path, 'r') as handle:
                    raw = handle.read(4096).strip()
                if keys:
                    for line in raw.splitlines():
                        lower = line.lower().strip()
                        for key in keys:
                            if lower.startswith(key):
                                value = line.split('=', 1)[-1].strip().strip('"\'')
                                if value:
                                    return _truncate(value, 24)
                if raw:
                    return _truncate(raw.splitlines()[0], 24)
            except Exception:
                pass
        return 'Enigma2'

    def _modern_layout_ready(self):
        self._media_ready = True
        self['skin_preview'].hide()
        self._set_pixmap('brand_logo', os.path.join(PLUGIN_PATH, 'logo_original_14.png'))
        self._set_pixmap('site_qr', _asset('qr_site.png'))
        try:
            self.set_language(self.lang)
            self.switch_tab(self.active_tab)
        except Exception as error:
            print('[AIO Panel] content rebuild after layout error:', error)
        self._refresh_modern_labels()
        self._refresh_modern_ui()
        self._update_health()

    def _set_pixmap(self, widget_name, path):
        try:
            widget = self[widget_name]
            if widget.instance is not None and os.path.exists(path):
                if self._pixel_paths.get(widget_name) != path:
                    widget.instance.setPixmapFromFile(legacy.ensure_str(path))
                    self._pixel_paths[widget_name] = path
                widget.show()
                return True
        except Exception:
            pass
        return False

    def _refresh_modern_labels(self):
        if self.lang == 'PL':
            self['support_label'].setText('MENU  •  Wygląd panelu')
            self['qr_support_label'].setText('WSPARCIE')
            self['site_qr_label'].setText('STRONA AIO TEAM')
            self['key_red'].setText('●  Polski')
            self['key_green'].setText('●  English')
            self['key_yellow'].setText('●  Restart GUI')
            self['key_blue'].setText('●  Aktualizacja')
        else:
            self['support_label'].setText('MENU  •  Panel appearance')
            self['qr_support_label'].setText('SUPPORT')
            self['site_qr_label'].setText('AIO TEAM WEBSITE')
            self['key_red'].setText('●  Polski')
            self['key_green'].setText('●  English')
            self['key_yellow'].setText('●  Restart GUI')
            self['key_blue'].setText('●  Update')
        self['title_label'].setText('AIO Panel %s' % legacy.VER)

    def _set_sidebar_tabs(self, tabs):
        self.tabs = tabs or []
        self.active_tab = min(self.active_tab, max(0, len(self.tabs) - 1))
        self._setting_tabs = True
        try:
            rows = []
            for title, items in self.tabs:
                clean = legacy.ensure_unicode(title).replace('---', '').strip()
                rows.append((clean, CATEGORY_ICONS.get(clean, 'system')))
            self['sidebar'].set_rows(rows, self.show_icons)
            self['sidebar'].moveToIndex(self.active_tab)
        finally:
            self._setting_tabs = False

    def switch_tab(self, tab_index):
        if not self.tabs:
            self.active_tab = 0
            self['menu'].setList([])
            self._refresh_modern_ui()
            return
        if tab_index < 0:
            tab_index = 0
        if tab_index >= len(self.tabs):
            tab_index = len(self.tabs) - 1
        self.active_tab = tab_index
        try:
            self['sidebar'].moveToIndex(tab_index)
        except Exception:
            pass
        items = self.tabs[tab_index][1]
        category = CATEGORY_ICONS.get(legacy.ensure_unicode(self.tabs[tab_index][0]), 'system')
        rows = [(_strip_leading_symbol(name), self._row_icon(action, category)) for name, action in items]
        self['menu'].set_rows(rows, self.show_icons)
        self['menu'].moveToIndex(0)
        self.update_function_description()
        self._apply_focus()
        self._refresh_modern_ui()

    def set_language(self, lang, persist=False):
        legacy.PanelAIO.set_language(self, lang, persist=persist)
        try:
            self._refresh_modern_labels()
            self._refresh_modern_ui()
        except Exception:
            pass

    def _modern_selection_changed(self):
        self._refresh_modern_ui()

    def _current_item(self):
        try:
            items = self.tabs[self.active_tab][1]
            index = self._get_list_index(self['menu'])
            if index is None or index < 0 or index >= len(items):
                return (None, None, 0, len(items))
            name, action = items[index]
            return (name, action, index, len(items))
        except Exception:
            return (None, None, 0, 0)

    def _row_icon(self, action, category):
        media = media_catalog.lookup(action, category)
        return media.icon if media else category

    def _fallback_description(self, action):
        value = legacy.ensure_unicode(action or '')
        if self.lang == 'PL':
            if value.startswith('archive:'):
                return 'Pobiera i bezpiecznie instaluje wybrane archiwum. Przed wykonaniem operacji AIO Panel poprosi o potwierdzenie.'
            if value.startswith('bash_raw:'):
                return 'Uruchamia instalator online w konsoli Enigma2. Przebieg i ewentualne błędy będą widoczne na ekranie.'
            if 'BACKUP' in value:
                return 'Tworzy kopię bezpieczeństwa wskazanych danych bez zmiany bieżącej konfiguracji.'
            if 'RESTORE' in value:
                return 'Przywraca wcześniej utworzoną kopię po sprawdzeniu jej zawartości.'
            return 'Wybierz OK, aby zobaczyć potwierdzenie i uruchomić tę funkcję.'
        if value.startswith('archive:'):
            return 'Downloads and safely installs the selected archive. AIO Panel asks for confirmation before making changes.'
        if value.startswith('bash_raw:'):
            return 'Runs the online installer in the Enigma2 console, where progress and errors remain visible.'
        if 'BACKUP' in value:
            return 'Creates a safety backup without changing the current configuration.'
        if 'RESTORE' in value:
            return 'Restores a previously created and validated backup.'
        return 'Press OK to review the confirmation and run this function.'

    def _refresh_modern_ui(self):
        if not self._media_ready:
            return
        try:
            if self.tabs and self.active_tab < len(self.tabs):
                category = legacy.ensure_unicode(self.tabs[self.active_tab][0]).replace('---', '').strip()
            else:
                category = ''
            self['category_title'].setText(legacy.ensure_str(category))
            category_icon = CATEGORY_ICONS.get(category, 'system')
            self._set_pixmap('category_icon', os.path.join(PLUGIN_PATH, 'assets', 'icons', 'large', category_icon + '.png'))
            name, action, index, total = self._current_item()
            self['item_counter'].setText('%d/%d' % ((index + 1) if total else 0, total))
            media = media_catalog.lookup(action, category_icon)
            self._media = media if self.show_previews and media_catalog.has_preview(action, media) else None
            self._select_preview(action, self._media)
            if name:
                clean_name = _strip_leading_symbol(name)
                self['detail_title'].setText(legacy.ensure_str(_truncate(clean_name, 44)))
                description = ''
                try:
                    description = self['function_description'].getText()
                except Exception:
                    pass
                if not description:
                    description = self._fallback_description(action)
                try:
                    state = _plugin_status_text(action, self.lang)
                except Exception:
                    state = ''
                description = legacy.ensure_unicode(description)
                if state:
                    description = (description.rstrip() + u'\\n\\n' + legacy.ensure_unicode(state)).strip()
                if action == 'CMD:AIO_APPEARANCE':
                    description = (u'Wybierz motyw, ikony menu i podglądy multimediów.' if self.lang == 'PL'
                                   else u'Choose a theme, menu icons and media previews.')
                if action and action.startswith('archive:'):
                    groups = media_catalog.CHANNEL_SAMPLES.get(media_catalog.archive_key(legacy.ensure_unicode(action).partition(':')[2]))
                    if groups:
                        label = u'Przykładowe bukiety: ' if self.lang == 'PL' else u'Sample bouquets: '
                        description = label + u', '.join(groups) + u'\n' + description
                self._detail_text = description
                if self._media:
                    kind = self._media_label()
                    hint = u'INFO  ·  ' + kind
                    description = hint + u'\\n' + description
                self['detail_body'].setText(legacy.ensure_str(_truncate(description, 310)))
                icon = media.icon if media else category_icon
                self._set_pixmap('item_icon', media_catalog.icon_path(icon))
            else:
                self['detail_title'].setText('')
                self['detail_body'].setText('')
                self._set_pixmap('item_icon', media_catalog.icon_path(category_icon))
        except Exception as error:
            print('[AIO Panel] modern UI refresh error:', error)

    def _cancel_preview_timer(self):
        if self._preview_timer is not None and self._preview_timer.active():
            self._preview_timer.cancel()
        self._preview_timer = None

    def _display_preview(self, path):
        self._preview_path = path
        widget = self['skin_preview']
        illustration = path
        if not illustration and self._media:
            old_key = media_catalog.visual_previews.preview_id(self._current_item()[1])
            if old_key and old_key.startswith('card:'):
                illustration = media_catalog.visual_previews.local_image(old_key)
            illustration = illustration or media_catalog.icon_path(self._media.icon)
        if illustration:
            node = self._dashboard_xml.find("widget[@name='skin_preview']")
            rect = [int(n) for n in (node.get('position') + ',' + node.get('size')).split(',')]
            if place_preview(widget, illustration, rect):
                widget.show()
            else:
                widget.hide()
                illustration = None
        else:
            widget.hide()
        for name in ('image_value', 'python_value', 'flash_value', 'cpu_value', 'ram_value', 'net_value'):
            if illustration:
                self[name].hide()
            else:
                self[name].show()

    def _media_label(self):
        media = self._media
        if media.kind == 'skin':
            if not self._preview_path:
                return media_catalog.phrase('skin-card', self.lang)
            if media.key in skin_previews.GALLERY.get('skin_layout', []):
                return media_catalog.phrase('layout', self.lang)
            if media.key in skin_previews.GALLERY.get('skin_art', []):
                return media_catalog.phrase('art', self.lang)
        return media_catalog.phrase(media.kind, self.lang)

    def _select_preview(self, action, media):
        key = (media.key if media.kind == 'skin' else action) if media else None
        if key == self._preview_key:
            return
        self._preview_key = key
        self._cancel_preview_timer()
        path = media_catalog.picture(media)
        self._display_preview(path)
        if (media and media.kind == 'skin' and not path and not self._fetching_key
                and time.time() >= self._miss_until.get(key, 0)):
            self._preview_timer = legacy.reactor.callLater(0.45, self._fetch_preview, key)

    def _fetch_preview(self, key):
        self._preview_timer = None
        self._fetching_key = key
        def worker():
            try:
                path = skin_previews.fetch_image(key)
            except Exception:
                path = None
            legacy.reactor.callFromThread(self._preview_finished, key, path)
        thread = Thread(target=worker)
        thread.daemon = True
        thread.start()

    def _preview_finished(self, key, path):
        if getattr(self, '_closed', True):
            return
        self._fetching_key = None
        if not path:
            self._miss_until[key] = time.time() + 600
        current = self._preview_key
        if key == current:
            self._display_preview(path)
        elif current and self._media and self._media.kind == 'skin' and not self._preview_path:
            self._preview_key = None
        self._refresh_modern_ui()

    def open_support(self):
        if self._focus != 'menu' or not self._media:
            return legacy.PanelAIO.open_support(self)
        name, action = self._current_item()[:2]
        title = _strip_leading_symbol(name)
        if self._preview_path:
            self.sess.open(PreviewScreen, title, self._preview_path, lang=self.lang)
        else:
            package = self._media.source if self._media.kind == 'skin' else None
            self.sess.openWithCallback(self._card_closed, FeatureCardScreen, title, self._media_label(), self._detail_text,
                           media_catalog.source_label(action, self._media, self.lang),
                           media_catalog.icon_path(self._media.icon), self.lang, package)

    def _card_closed(self, *unused):
        if not getattr(self, '_closed', True) and self._media and self._media.kind == 'skin':
            self._preview_key = None
            self._refresh_modern_ui()

    def _flash_percent(self):
        try:
            stat = os.statvfs('/')
            total = float(stat.f_blocks * stat.f_frsize)
            free = float(stat.f_bavail * stat.f_frsize)
            if total <= 0:
                return None
            return max(0.0, min(100.0, (total - free) * 100.0 / total))
        except Exception:
            return None

    def _update_health(self):
        try:
            cpu = self._read_cpu_percent()
            ram = self._read_mem_pct()
            flash = self._flash_percent()
            ip = self._local_ip()
            cpu_text = 'CPU: N/A' if cpu is None else 'CPU: %d%%' % int(cpu)
            ram_text = 'RAM: N/A' if ram is None else 'RAM: %d%%' % int(ram)
            flash_text = 'Flash: N/A' if flash is None else 'Flash: %d%%' % int(flash)
            net_text = ('Sieć: %s' if self.lang == 'PL' else 'Network: %s') % (ip or 'offline')
            self['cpu_value'].setText(cpu_text)
            self['ram_value'].setText(ram_text)
            self['flash_value'].setText(flash_text)
            self['net_value'].setText(net_text)
            self['image_value'].setText(('System: %s' if self.lang == 'PL' else 'Image: %s') % self._modern_image_name)
            self['python_value'].setText('Python: %s.%s' % (sys.version_info[0], sys.version_info[1]))
            self['clock'].setText(datetime.datetime.now().strftime('%d.%m.%Y  %H:%M'))
            self['health'].setText('%s  |  %s  |  %s' % (cpu_text, ram_text, flash_text))
        except Exception as error:
            print('[AIO Panel] modern health error:', error)
        try:
            self._health_timer.start(2000, True)
        except Exception:
            pass


class ModernLoadingScreen(legacy.AIOLoadingScreen):
    skin = _loading_skin()

    def __init__(self, session):
        legacy.AIOLoadingScreen.__init__(self, session)
        self.skin = fit_skin(themed_skin(_loading_skin(), preferences()[0]), legacy._desktop_size())
        self.skinName = ['AIOModernLoading150']
        self['logo'] = Pixmap()
        self['title'] = Label('AIO Panel')
        self['version'] = Label('v%s' % legacy.VER)
        self['stage'] = Label('')
        self['tip'] = Label('')
        self.onLayoutFinish.append(self._modern_loading_ready)
        self.onClose.append(self._stop_loading)

    def _stop_loading(self):
        self._panel_opened = True
        timer = self._loading_timeout_call
        if timer is not None and timer.active():
            timer.cancel()

    def _modern_loading_ready(self):
        try:
            if self['logo'].instance is not None:
                self['logo'].instance.setPixmapFromFile(os.path.join(PLUGIN_PATH, 'logo_original_14.png'))
        except Exception:
            pass
        self['title'].setText('AIO Panel')
        self['version'].setText('v%s' % legacy.VER)
        if _system_language() == 'PL':
            self['stage'].setText('Inicjalizacja bezpiecznego środowiska')
            self['tip'].setText('AIO Panel ładuje dane w tle. Brak odpowiedzi serwera nie zablokuje otwarcia panelu.')
        else:
            self['stage'].setText('Initializing the safe runtime environment')
            self['tip'].setText('AIO Panel loads data in the background. A server timeout will not block the dashboard.')

    def start_loading_process(self):
        try:
            self['stage'].setText('Sprawdzanie zależności systemowych' if _system_language() == 'PL' else 'Checking system dependencies')
        except Exception:
            pass
        return legacy.AIOLoadingScreen.start_loading_process(self)

    def start_async_data_load(self):
        try:
            self['stage'].setText('Pobieranie list i informacji online' if _system_language() == 'PL' else 'Loading lists and online information')
            self['message'].setText('Ładowanie danych AIO Panel…' if _system_language() == 'PL' else 'Loading AIO Panel data…')
        except Exception:
            pass
        return legacy.AIOLoadingScreen.start_async_data_load(self)

    def _open_panel_safe(self, fetched_data=None):
        if getattr(self, '_panel_opened', True):
            return
        self._panel_opened = True
        try:
            if self._loading_timeout_call is not None and self._loading_timeout_call.active():
                self._loading_timeout_call.cancel()
        except Exception:
            pass
        data = fetched_data or self.fetched_data_cache or {
            'repo_lists': [],
            's4a_lists_full': [],
            'best_oscam_version': 'Auto',
            'local_oscam_version': 'Online'
        }
        self.close(data)
