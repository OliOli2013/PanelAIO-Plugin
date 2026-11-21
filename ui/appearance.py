# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import xml.etree.ElementTree as ET

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Tools.LoadPixmap import LoadPixmap
from Components.config import config, ConfigSelection, ConfigYesNo, configfile
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from enigma import getDesktop, eSize, ePoint
from skin import parseColor
from Plugins.SystemPlugins.PanelAIO.core.compatibility import ensure_str

# The first column is persisted in /etc/enigma2/settings.
THEME_CHOICES = (
    ('ocean', 'Ocean', 'Ocean'),
    ('amber', 'Bursztyn', 'Amber'),
    ('contrast', 'Wysoki kontrast', 'High contrast'),
    ('emerald', 'Szmaragd', 'Emerald'),
    ('amethyst', 'Ametyst', 'Amethyst'),
    ('ruby', 'Rubin', 'Ruby'),
    ('turquoise', 'Turkus', 'Turquoise'),
    ('graphite', 'Grafit', 'Graphite'),
    ('pearl', 'Perła (jasny)', 'Pearl (light)'),
)
THEMES = tuple(entry[0] for entry in THEME_CHOICES)
NAMES = {'PL': dict((key, pl) for key, pl, en in THEME_CHOICES),
         'EN': dict((key, en) for key, pl, en in THEME_CHOICES)}
# Screen, panel, header, accent, border, metadata, counter, footer,
# description, sidebar text, menu text, title, selected row.
BASE = ('#07111D', '#0D1A29', '#0E1C2C', '#00C2FF', '#1E789E', '#8FA7BE',
        '#8298AE', '#70879D', '#AFC0D1', '#B9C8D8', '#D8E3ED', '#F2F7FC', '#195374')
PALETTES = {
    'ocean': BASE,
    'amber': ('#201912', '#2C221A', '#392C21', '#FFCD81', '#92632D', '#D7BD9D',
              '#DEC6AE', '#CDB59D', '#EDDECC', '#F2E4D4', '#FFF2E2', '#FFF8EE', '#785025'),
    'contrast': ('#000000', '#080808', '#141414', '#FFED70', '#FAE252', '#FFFFFF',
                 '#FFFFFF', '#F2F2F2', '#FFFFFF', '#FFFFFF', '#FFFFFF', '#FFFFFF', '#3F469D'),
    'emerald': ('#081A13', '#10251A', '#183024', '#88EEA9', '#4C9164', '#A6C5AD',
                '#B2CDB8', '#9CB7A2', '#C5DACC', '#D0E4D5', '#E3F2E6', '#F2FFF4', '#287A4C'),
    'amethyst': ('#1A1225', '#261B35', '#302240', '#D5ACFF', '#9675B7', '#C3B4D2',
                 '#CCBDDA', '#B8A6C9', '#DED1EB', '#E4DAEF', '#F0E8F8', '#FBF6FF', '#815CB0'),
    'ruby': ('#210F16', '#301720', '#3D1B27', '#FF9AAE', '#A75671', '#CFB1BB',
             '#D6BCC6', '#C7A0AE', '#E5CCD5', '#EED6DD', '#F5E5E9', '#FFF4F6', '#B04964'),
    'turquoise': ('#082027', '#102A31', '#123740', '#70ECE4', '#4B9698', '#ACCCCE',
                  '#BDD6D8', '#A1BFC3', '#CBE5E5', '#D4ECEC', '#E5F6F6', '#F4FFFF', '#287D82'),
    'graphite': ('#17181B', '#24262A', '#2C2E33', '#E2E5EB', '#818795', '#BEC1CA',
                 '#C9CCD3', '#AEB2BE', '#D6D8DF', '#E2E3E8', '#EDEEF2', '#FAFAFC', '#6D727C'),
    'pearl': ('#F3F1EC', '#FFFDFA', '#E8E5DF', '#214C70', '#748392', '#435460',
              '#4E5B68', '#4D5762', '#34434D', '#263944', '#20313C', '#182730', '#365A78'),
}

# Keep the remote key hues recognisable against the light header.
PEARL_STATUS_COLORS = {
    '#FF7381': '#A02D40', '#4CDB91': '#17643C', '#FFD24A': '#755000',
    '#4CA3FF': '#205D94', '#57D99B': '#20613F',
}

APPEARANCE_SKIN = '''
    <screen position="center,center" size="850,340" title="AIO Panel" backgroundColor="#07111D">
        <widget name="items" position="24,24" size="802,174" itemHeight="50" font="Regular;27" backgroundColor="#0D1A29" foregroundColor="#F2F7FC" backgroundColorSelected="#195374" foregroundColorSelected="#FFFFFF" />
        <widget name="sample" position="24,202" size="802,62" font="Regular;28" halign="center" valign="center" backgroundColor="#0D1A29" foregroundColor="#00C2FF" />
        <widget name="keys" position="24,279" size="802,44" font="Regular;21" foregroundColor="#D8E3ED" transparent="1" />
    </screen>'''


def settings():
    section = config.plugins.panelaio
    if not hasattr(section, 'panel_theme'):
        section.panel_theme = ConfigSelection(default='ocean', choices=[(k, k) for k in THEMES])
    if not hasattr(section, 'menu_icons'):
        section.menu_icons = ConfigYesNo(default=True)
    if not hasattr(section, 'skin_previews'):
        section.skin_previews = ConfigYesNo(default=True)
    return section.panel_theme, section.menu_icons, section.skin_previews


def preferences():
    theme, icons, previews = (setting.value for setting in settings())
    return (theme if theme in THEMES else 'ocean', bool(icons), bool(previews))


def fit_skin(root, desktop):
    width, height = (int(n) for n in root.get('size').split(','))
    factor = min(1.0, (desktop[0] - 16.0) / width, (desktop[1] - 20.0) / height)
    if factor < 1.0:
        for node in root.iter():
            for key in ('size', 'position', 'itemHeight'):
                value = node.get(key)
                if value and all(n.isdigit() for n in value.split(',')):
                    node.set(key, ','.join(str(int(int(n) * factor)) for n in value.split(',')))
            if node.get('font'):
                name, size = node.get('font').rsplit(';', 1)
                node.set('font', '%s;%d' % (name, max(1, int(int(size) * factor))))
    return ET.tostring(root, encoding='utf-8').decode('utf-8')


def desktop_size():
    size = getDesktop(0).size()
    return size.width(), size.height()


def themed_skin(xml, theme):
    palette = dict(zip(BASE, PALETTES[theme]))
    if theme == 'pearl':
        palette.update(PEARL_STATUS_COLORS)
    root = ET.fromstring(xml)
    for node in root.iter():
        for key, value in list(node.attrib.items()):
            if value in palette:
                node.set(key, palette[value])
    return root


def apply_colors(screen, root):
    methods = (('foregroundColor', 'setForegroundColor'), ('backgroundColor', 'setBackgroundColor'),
               ('backgroundColorSelected', 'setBackgroundColorSelected'),
               ('foregroundColorSelected', 'setForegroundColorSelected'), ('borderColor', 'setBorderColor'))
    for node in root.iter():
        widget = screen if node is root else screen.get(node.get('name'))
        instance = getattr(widget, 'instance', None)
        for attr, method in methods:
            setter = getattr(instance, method, None)
            if setter and node.get(attr):
                setter(parseColor(node.get(attr)))


class AppearanceScreen(Screen):
    def __init__(self, session, lang):
        Screen.__init__(self, session)
        self.lang = lang
        self._pending_settings = list(preferences())
        self.skin = fit_skin(themed_skin(APPEARANCE_SKIN, self._pending_settings[0]), desktop_size())
        self.setTitle('Wygląd panelu' if lang == 'PL' else 'Panel appearance')
        self['items'] = MenuList([])
        self['sample'] = Label('')
        self['keys'] = Label(ensure_str('◀ ▶  Zmień     •     Zielony  Zapisz     •     EXIT  Anuluj' if lang == 'PL'
                                        else '◀ ▶  Change     •     Green  Save     •     EXIT  Cancel'))
        self['actions'] = ActionMap(['DirectionActions', 'OkCancelActions', 'ColorActions'], {
            'up': self['items'].up, 'down': self['items'].down, 'left': lambda: self.change(-1),
            'right': lambda: self.change(1), 'ok': lambda: self.change(1), 'green': self.save_changes,
            'red': self.close, 'cancel': self.close}, -1)
        self.onLayoutFinish.append(self.refresh)

    def refresh(self):
        theme, icons, previews = self._pending_settings
        title = NAMES[self.lang][theme]
        labels = ('Motyw', 'Ikony w menu', 'Podglądy multimediów', 'Tak', 'Nie') if self.lang == 'PL' else (
            'Theme', 'Menu icons', 'Media previews', 'On', 'Off')
        index = max(0, self['items'].getSelectionIndex() or 0)
        self['items'].setList([ensure_str('%s    %s' % (k, v)) for k, v in zip(labels[:3],
            (title, labels[3 if icons else 4], labels[3 if previews else 4]))])
        self['items'].moveToIndex(index)
        self['sample'].setText(ensure_str(title))
        apply_colors(self, themed_skin(APPEARANCE_SKIN, theme))

    def change(self, direction):
        idx = self['items'].getSelectionIndex()
        if idx == 0:
            self._pending_settings[0] = THEMES[(THEMES.index(self._pending_settings[0]) + direction) % len(THEMES)]
        elif idx in (1, 2):
            self._pending_settings[idx] = not self._pending_settings[idx]
        self.refresh()

    def save_changes(self):
        fields = settings()
        previous = preferences()
        try:
            for field, value in zip(fields, self._pending_settings):
                field.value = value
                field.save()
            configfile.save()
        except Exception as error:
            for field, value in zip(fields, previous):
                field.value = value
                field.save()
            self.session.open(MessageBox, ensure_str(str(error)), MessageBox.TYPE_ERROR)
            return
        self.close(True)


def _picture_rect(dimensions, rect):
    x, y, width, height = rect
    iw, ih = dimensions
    ratio = min(float(width) / iw, float(height) / ih)
    w, h = max(1, int(iw * ratio)), max(1, int(ih * ratio))
    return x + (width - w) // 2, y + (height - h) // 2, w, h


def _load_picture(widget, path):
    instance = getattr(widget, 'instance', None)
    if instance is None or not path:
        return False
    try:
        pixmap = LoadPixmap(ensure_str(path))
        if pixmap is None:
            return False
        instance.setPixmap(pixmap)
        return True
    except (TypeError, ValueError, RuntimeError, IOError, OSError):
        return False


def place_preview(widget, path, rect):
    from Plugins.SystemPlugins.PanelAIO.core.skin_previews import png_size
    dimensions = png_size(path) if path else None
    instance = getattr(widget, 'instance', None)
    if not dimensions or instance is None:
        return False
    x, y, width, height = _picture_rect(dimensions, rect)
    instance.move(ePoint(x, y))
    instance.resize(eSize(width, height))
    return _load_picture(widget, path)


class AIOPanelMediaPreview(Screen):
    def __init__(self, session, title, path, background=None, lang=None):
        from Plugins.SystemPlugins.PanelAIO.core.skin_previews import png_size
        Screen.__init__(self, session)
        self.skinName = 'AIOPanelMediaPreview'
        self._picture_path = path
        self._sample_background = background if background in ('#E7EBEE', '#182633') else None
        self.setTitle(ensure_str(title))
        dw, dh = desktop_size()
        width, height = max(80, int(dw) - 48), max(64, int(dh) - 90)
        dims = png_size(path) if path else None
        x, y, w, h = _picture_rect(dims or (16, 9), (0, 0, width, height))
        self.skin = (
            '<screen name="AIOPanelMediaPreview" position="center,center" size="%d,%d" backgroundColor="%s">'
            '<widget name="shot" position="%d,%d" size="%d,%d" scale="1" alphatest="blend" zPosition="1" />'
            '<widget name="message" position="0,0" size="%d,%d" font="Regular;%d" foregroundColor="#E7EDF3" '
            'backgroundColor="#101B28" halign="center" valign="center" zPosition="2" /></screen>'
            % (width, height, self._sample_background or '#080D13', x, y, w, h,
               width, height, min(30, max(16, width // 42))))
        self['shot'] = Pixmap()
        self['message'] = Label(ensure_str(
            'Nie można wyświetlić zdjęcia.  EXIT  ·  Wróć' if lang != 'EN' else
            'This picture could not be displayed.  EXIT  ·  Back'))
        self['actions'] = ActionMap(['OkCancelActions', 'InfoActions', 'InfobarEPGActions', 'HelpActions'], {
            'ok': self.close, 'cancel': self.close, 'info': self.close, 'displayHelp': self.close,
            'showEventInfo': self.close}, -1)
        if self._sample_background:
            self['background_actions'] = ActionMap(['ColorActions'], {'yellow': self.toggle_background}, -1)
        # Screen.applySkin on OpenATV and OpenPLi calls bound methods directly.
        # It passes other entries to exec(), which does not accept a lambda.
        self.onLayoutFinish.append(self.show_picture)

    def show_picture(self):
        if _load_picture(self['shot'], self._picture_path):
            self['message'].hide()
            self['shot'].show()
        else:
            self['shot'].hide()
            self['message'].show()

    def toggle_background(self):
        self._sample_background = '#182633' if self._sample_background == '#E7EBEE' else '#E7EBEE'
        if self.instance is not None:
            self.instance.setBackgroundColor(parseColor(self._sample_background))


# Keep the import used by other AIO screens and older callers.
PreviewScreen = AIOPanelMediaPreview
