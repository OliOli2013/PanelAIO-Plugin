# -*- coding: utf-8 -*-
"""Exercise the dashboard/remote entry points without a receiver or package installation."""
from __future__ import absolute_import, print_function
import ast
import os
import sys
import types
import xml.etree.ElementTree as ET
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def module(name, **attrs):
    if name not in sys.modules:
        mod = sys.modules[name] = types.ModuleType(name)
        mod.__path__ = []
        if '.' in name:
            parent, child = name.rsplit('.', 1)
            setattr(module(parent), child, mod)
    mod = sys.modules[name]
    for key, val in attrs.items():
        setattr(mod, key, val)
    return mod


class Box(object):
    pass


class Value(object):
    def __init__(self, default=None, **unused):
        self.value = default
    def save(self):
        pass


class Timer(object):
    def __init__(self, *args):
        self.callback = []
        self.pending = True
    def start(self, *args):
        pass
    def stop(self):
        self.pending = False
    cancel = stop
    def active(self):
        return self.pending


class Geometry(object):
    dims = (1280, 720)
    def __init__(self, *coords):
        self.coords = coords
    def size(self):
        return self
    def width(self):
        return self.dims[0]
    def height(self):
        return self.dims[1]


class Component(object):
    def execBegin(self):
        self.executing = True

    def execEnd(self):
        self.executing = False


class Widget(Component):
    def __init__(self, text=''):
        self.instance = self
        self.text = text
        self.visible = True
    def setText(self, text):
        self.text = text
    def getText(self):
        return self.text
    def show(self):
        self.visible = True
    def hide(self):
        self.visible = False
    def setPixmap(self, pixmap):
        assert pixmap is not None
        self.path = pixmap

    def setPixmapFromFile(self, path):
        assert os.path.isfile(path), path
        self.path = path
    def move(self, position):
        self.position = position
    def resize(self, size):
        self.size_value = size
    def setBackgroundColor(self, color):
        self.background = color
    def setForegroundColor(self, color):
        self.foreground = color
    def setSelectionEnable(self, value):
        self.highlight = value


class Rows(Widget):
    def setForegroundColorSelected(self, color):
        self.selected_foreground = color

    def setBackgroundColorSelected(self, color):
        self.selected_background = color

    def __init__(self, rows, **unused):
        Widget.__init__(self)
        self.l = self
        self.onSelectionChanged = []
        self.index = 0
        self.setList(rows)
    def setFont(self, index, font):
        self.font = font
    def setItemHeight(self, height):
        self.height = height
    def setList(self, rows):
        self.list = rows
        self.moveToIndex(0)
    def moveToIndex(self, idx):
        idx = max(0, min(idx, len(self.list) - 1))
        if self.index != idx:
            self.index = idx
            for fn in self.onSelectionChanged:
                fn()
    def getSelectionIndex(self):
        return self.index
    def up(self):
        self.moveToIndex(self.index - 1)
    def down(self):
        self.moveToIndex(self.index + 1)


class Bindings(Component):
    def __init__(self, contexts, bindings, *args):
        self.actions = bindings


class Screen(dict):
    def __init__(self, session):
        dict.__init__(self)
        self.session = session
        self.instance = Widget()
        self.onShown, self.onClose, self.onLayoutFinish = [], [], []
        self.onExecBegin, self.onFirstExecBegin = [], []
    def setTitle(self, name):
        self.title = name
    def close(self, *values):
        self.result = values
    def execBegin(self):
        # OpenATV and OpenPLi enumerate the Screen dictionary on activation.
        for component in self.values():
            component.execBegin()
    def execEnd(self):
        for component in self.values():
            component.execEnd()


class Session(object):
    def activate_last_dialog(self):
        screen, args, kwargs = self.last
        dialog = screen(self, *args, **kwargs)
        for callback in dialog.onLayoutFinish:
            # Enigma2 treats non-method callbacks as code to exec() during applySkin.
            if isinstance(callback, type(dialog.close)):
                callback()
            else:
                eval(compile(callback, '<layout>', 'exec'), {})
        dialog.execBegin()
        return dialog

    def openWithCallback(self, callback, screen, *args, **kw):
        self.last = (screen, args, kw)
        self.callback = callback
    def open(self, screen, *args, **kw):
        self.last = (screen, args, kw)


def setup():
    pkg = module('Plugins.SystemPlugins.PanelAIO')
    pkg.__path__ = [ROOT]
    config = Box()
    config.plugins, config.osd = Box(), Box()
    config.osd.language = Value('pl_PL')
    module('Components.config', config=config, ConfigSelection=Value, ConfigYesNo=Value,
           ConfigSubsection=Box, configfile=Value())
    module('enigma', eTimer=Timer, eDVBDB=Box, eSize=Geometry, ePoint=Geometry,
           getDesktop=Geometry, eListboxPythonMultiContent=Rows, RT_VALIGN_CENTER=1,
           RT_HALIGN_LEFT=0, gFont=lambda *args: args, BT_SCALE=2)
    module('skin', parseColor=lambda value: value)
    module('Tools.LoadPixmap', LoadPixmap=lambda path: path if os.path.isfile(path) else None)
    module('Tools.Directories', fileExists=os.path.isfile)
    module('Components.MultiContent', MultiContentEntryText=lambda **kw: kw,
           MultiContentEntryPixmapAlphaBlend=lambda **kw: kw)
    for name, obj in [('ActionMap',Bindings),('Label',Widget),('MenuList',Rows),('Pixmap',Widget)]:
        module('Components.'+name, **{name:obj})
    module('Plugins.Plugin', PluginDescriptor=Box)
    for name in ('Screen','Console','ChoiceBox','MessageBox','InputBox','Standby'):
        module('Screens.'+name, **{('TryQuitMainloop' if name=='Standby' else name):Screen})
    Screen.TYPE_ERROR, Screen.TYPE_INFO, Screen.TYPE_YESNO = 1, 2, 3
    reactor = Box()
    reactor.running = False
    reactor.callLater = lambda *args: Timer()
    reactor.callFromThread = lambda fn, *args: fn(*args)
    module('twisted.internet', reactor=reactor)
    return config


def text_contrast(foreground, background):
    def luminance(color):
        channels = [int(color[i:i+2], 16) / 255.0 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
        return sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))

    low, high = sorted((luminance(foreground), luminance(background)))
    return (high + .05) / (low + .05)


def check_theme_controls(panel, session, appearance, modern):
    themes = appearance.THEMES
    assert len(themes) == len(set(themes)) == 9
    assert set(themes) == set(appearance.PALETTES)
    for lang in ('PL', 'EN'):
        panel.set_language(lang)
        saved = appearance.preferences()
        start = themes.index(saved[0])
        panel.open_appearance()
        editor = session.activate_last_dialog()
        for step in range(1, len(themes) + 1):
            editor['actions'].actions['left']()
            key = themes[(start-step) % len(themes)]
            palette = appearance.PALETTES[key]
            assert editor.instance.background == palette[0]
            assert editor['items'].selected_background == palette[-1]
            assert editor['sample'].foreground == palette[3]
            assert editor['sample'].getText() == appearance.ensure_str(appearance.NAMES[lang][key])
        editor['actions'].actions['right']()
        editor['actions'].actions['cancel']()
        editor.execEnd()
        session.callback(*editor.result)
        assert appearance.preferences() == saved and panel.theme == saved[0]

        for step in range(1, len(themes) + 1):
            key = themes[(start+step) % len(themes)]
            panel.open_appearance()
            editor = session.activate_last_dialog()
            editor['actions'].actions['right']()
            editor['actions'].actions['green']()
            editor.execEnd()
            session.callback(*editor.result)
            assert appearance.preferences() == (key, saved[1], saved[2])
            assert panel.theme == key and panel.instance.background == appearance.PALETTES[key][0]
            assert panel['menu'].selected_background == appearance.PALETTES[key][-1]
            assert panel['sidebar'].selected_foreground == '#FFFFFF'
            loading = modern.ModernLoadingScreen(session)
            assert ET.fromstring(loading.skin).get('backgroundColor') == panel.instance.background


def exercise():
    config = setup()
    from Plugins.SystemPlugins.PanelAIO import runtime
    from Plugins.SystemPlugins.PanelAIO.ui import main, modern, appearance
    from Plugins.SystemPlugins.PanelAIO.core import action_dispatcher, skin_previews, media_catalog
    from Plugins.SystemPlugins.PanelAIO.ui.media_details import PiconPackScreen, FeatureCardScreen
    from Plugins.SystemPlugins.PanelAIO.data.catalog import CATALOG, ROWS
    from Plugins.SystemPlugins.PanelAIO.ui.media_list import CATEGORY_ICONS
    from Plugins.SystemPlugins.PanelAIO.core.compatibility import ensure_unicode
    session = Session()
    runtime._get_show_in_menu_setting = lambda *args: True
    skins = [p for row in ROWS if row[3]=='skins' for p in row[4]]
    skins.extend(['enigma2-plugin-skins-blue-hd', 'enigma2-skin-aio-unknown-test'])
    # An installed feed can be many screens long. Include keys from across the catalog.
    sampled = sorted(skin_previews.GALLERY['skins'])[::6]
    skins.extend('enigma2-plugin-skins-' + n for n in sampled if 'enigma2-plugin-skins-' + n not in skins)
    skins.append('enigma2-plugin-skins-blue-hd-dbg')
    data = {'repo_lists':[('Polska 13E AIO Panel', 'archive:'+runtime.WIZARD_CHANNEL_URL)],
            's4a_lists_full':[], 'available_skins':skins}
    main.open_main(session)
    assert session.last[0] is modern.ModernLoadingScreen
    loading = session.last[0](session)
    loading._open_panel_safe(data)
    session.callback(*loading.result)
    assert session.last[:2] == (modern.ModernPanelAIO,(data,))
    panel = modern.ModernPanelAIO(session, data)
    panel._local_ip = lambda: '127.0.0.1'
    for cb in panel.onLayoutFinish:
        cb()
    assert config.plugins.panelaio.language.value == 'auto' and panel.lang == 'PL'

    for dims in ((720, 576),(1024, 576),(1280, 720),(1920, 1080),(3840, 2160)):
        Geometry.dims = dims
        for theme in appearance.THEMES:
            root = ET.fromstring(modern._modern_skin(theme))
            width, height = map(int, root.get('size').split(','))
            assert width <= dims[0] and height <= dims[1]
            for node in root.findall('widget'):
                assert node.get('name') in panel, node.get('name')
                x,y = map(int,node.get('position').split(','))
                w,h = map(int,node.get('size').split(','))
                assert 0 <= x <= x+w <= width and 0 <= y <= y+h <= height, node.attrib
                if node.get('foregroundColor'):
                    background = node.get('backgroundColor', root.get('backgroundColor'))
                    assert text_contrast(node.get('foregroundColor'), background) >= 4.5, (theme, node.attrib)
                if node.get('foregroundColorSelected') and node.get('backgroundColorSelected'):
                    assert text_contrast(node.get('foregroundColorSelected'), node.get('backgroundColorSelected')) >= 4.5
    Geometry.dims = (1280,720)

    # Intercept the effects of the live dispatcher. Every menu item must reach
    # a real method, a dialog or a command runner without installing anything.
    calls = []
    class Probe(object):
        lang = 'PL'
        sess = session
        image_type = 'openatv'
        fetched_data_cache = data
        def __getattr__(self, name):
            target = getattr(panel, name)
            assert callable(target), name
            if name == '_safe_legacy_action_command':
                return target
            def record(*args, **kwargs):
                calls.append(name)
            return record

    probe = Probe()
    dispatch = getattr(runtime.PanelAIO.execute_action, '__func__', runtime.PanelAIO.execute_action)
    saved = {}
    def record_effect(*args, **kwargs):
        calls.append('operation')
    for name in ('run_command_in_background', 'console_screen_open', 'install_archive',
                 'install_e2kodi', 'show_message_compat'):
        saved[name] = getattr(runtime, name)
        setattr(runtime, name, record_effect)
    saved['_should_record_recent'] = runtime._should_record_recent
    runtime._should_record_recent = lambda action: False
    # Every visible row must both route and match the item picked by the remote.
    tree = ast.parse(open(os.path.join(ROOT,'runtime.py'),'rb').read())
    execute = next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='execute_action')
    def literals(nodes):
        if hasattr(ast, 'Constant'):
            return set(n.value for n in nodes if isinstance(n, ast.Constant) and isinstance(n.value, str))
        return set(n.s for n in nodes if isinstance(n, ast.Str))
    commands = set(action_dispatcher.registered_keys())
    for node in ast.walk(execute):
        if isinstance(node,ast.Compare) and isinstance(node.left,ast.Name) and node.left.id=='key':
            commands.update(literals(ast.walk(node)))
    prefixes = set()
    for node in ast.walk(execute):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='startswith' and isinstance(node.func.value,ast.Name) and node.func.value.id=='action':
            prefixes.update(literals(ast.walk(node)))
    for handler in action_dispatcher._METHODS.values():
        assert callable(getattr(panel,handler)), handler
    observations = []
    for lang in ('PL','EN'):
        panel.set_language(lang)
        actions = []
        for ti,(category,entries) in enumerate(panel.tabs):
            panel.switch_tab(ti)
            assert panel['sidebar'].getSelectionIndex()==ti and len(panel['menu'].list)==len(entries)
            assert ensure_unicode(category) in CATEGORY_ICONS
            for ri,(label,action) in enumerate(entries):
                panel['menu'].moveToIndex(ri)
                assert panel._current_item()[:2]==(label,action)
                assert panel['menu'].list[ri][0] and len(panel['menu'].list[ri])==3
                if action=='SEPARATOR':
                    continue
                del calls[:]
                dispatch(probe, label, action)
                assert calls, ('No dispatch target', action)
                actions.append(action)
                prefix = action.split(':')[0]+':'
                assert prefix in prefixes,(lang,label,action)
                if prefix=='CMD:':
                    assert action[4:] in commands,(label,action)
                elif prefix=='feed:':
                    assert action[5:] in CATALOG, action
                if skin_previews.skin_id(action) and not action.startswith('feed:native-'):
                    assert panel._preview_path and panel['skin_preview'].visible,action
                else:
                    media = media_catalog.lookup(action, CATEGORY_ICONS[category])
                    if media_catalog.has_preview(action, media):
                        assert panel['skin_preview'].visible, action
                        assert panel._preview_path == media_catalog.picture(media), (action, media)
                        assert panel._preview_path or media.kind in ('skin', 'card'), action
                    else:
                        assert not panel['skin_preview'].visible, action
                    if action.endswith('-dbg'):
                        raise AssertionError(action)
        assert len(actions)==len(set(actions)),[k for k,n in Counter(actions).items() if n>1]
        observations.append(set(actions))
    for name, original in saved.items():
        setattr(runtime, name, original)
    from Plugins.SystemPlugins.PanelAIO.data.skins import FAMILIES, action_for_image
    for src, (family, suffix) in FAMILIES.items():
        action = 'remote_script:' + src
        for image, end in (('openatv','atv'),('openpli','pli')):
            selected = action_for_image(action, image)
            assert ('/%s%s/%s%s.ipk|' % (family,end,family,end)) in selected
            assert selected.endswith(suffix + ('-pli' if end=='pli' else '') + '$')
        assert action_for_image(action, 'unknown') == action
    if sys.version_info[0] == 2:
        assert not any('/OpenCamView-Plugin/' in a or '/E2-Doctor-Plugin/' in a or 'youtube_py3-' in a for a in observations[0])
    assert observations[0] == observations[1]
    panel['act'].actions['red']()
    assert config.plugins.panelaio.language.value=='PL'
    entries=[(ti,ri) for ti,(_,items) in enumerate(panel.tabs) for ri,(_,action) in enumerate(items) if action=='CMD:AIO_APPEARANCE']
    ti,ri=entries[0]
    panel.switch_tab(ti)
    panel['menu'].moveToIndex(ri)
    panel.ok_pressed()
    assert session.last[0] is appearance.AppearanceScreen
    editor = session.activate_last_dialog()
    assert all(component.executing for component in editor.values())
    editor.change(1)
    editor['items'].moveToIndex(1)
    editor.change(1)
    editor['items'].moveToIndex(2)
    editor.change(1)
    editor['actions'].actions['green']()
    editor.execEnd()
    session.callback(*editor.result)
    assert appearance.preferences()==('amber',False,False)
    assert panel._current_item()[1]=='CMD:AIO_APPEARANCE'
    assert len(panel['menu'].list[ri])==2 and panel.instance.background=='#201912'
    assert modern.ModernPanelAIO(session,data).theme=='amber'
    panel['appearance_actions'].actions['menu']()
    editor = session.activate_last_dialog()
    editor['actions'].actions['right']()
    editor['actions'].actions['cancel']()
    editor.execEnd()
    session.callback(*editor.result)
    assert appearance.preferences()==('amber',False,False)
    for field in appearance.settings()[1:]:
        field.value=True
    panel._appearance_saved(True)
    target=[(ti,ri) for ti,(_,items) in enumerate(panel.tabs) for ri,(_,a) in enumerate(items) if a=='CMD:INSTALL_AIOHD_NEXT'][0]
    panel.switch_tab(target[0])
    panel['menu'].moveToIndex(target[1])
    assert panel._preview_path and not panel['flash_value'].visible
    panel.open_support()
    assert session.last[0] is appearance.PreviewScreen
    view = session.activate_last_dialog()
    assert view['shot'].path.endswith('aiohd.png')
    assert view['shot'].visible and not view['message'].visible
    assert view.skinName == 'AIOPanelMediaPreview'
    session.open(appearance.PreviewScreen, 'Missing', '/missing-aio-picture.png', lang='EN')
    missing = session.activate_last_dialog()
    assert missing['message'].visible and not missing['shot'].visible
    missing['actions'].actions['cancel']()
    missing.execEnd()
    view.execEnd()
    # A late network reply may populate the cache but must never change the
    # picture or the details of the next selection.
    panel._preview_finished('blue-hd', None)
    assert panel._preview_path.endswith('aiohd.png')
    panel.switch_tab(0)
    assert panel['skin_preview'].visible and not panel['flash_value'].visible
    panel.open_support()
    assert session.last[0] is FeatureCardScreen
    card = session.activate_last_dialog()
    assert 'Polska_13E_AIO_Panel.zip' in ensure_unicode(card['source'].getText())
    assert 'bukiety' in ensure_unicode(card['body'].getText()).lower()
    card.execEnd()
    for ti, (_, items) in enumerate(panel.tabs):
        unknown = [ri for ri, (_, a) in enumerate(items) if a == 'feed:native-enigma2-skin-aio-unknown-test']
        if unknown:
            panel.switch_tab(ti)
            panel['menu'].moveToIndex(unknown[0])
            panel.open_support()
            assert session.last[0] is FeatureCardScreen
            card = session.activate_last_dialog()
            assert card.package == 'enigma2-skin-aio-unknown-test'
            assert 'pakiecie' in ensure_unicode(card['keys'].getText())
            card.execEnd()
            break
    for lang in ('PL','EN'):
        panel.set_language(lang)
        panel._prompt_picon_pack('Picon')
        assert session.last[0] is PiconPackScreen
        callback = session.callback
        chooser = session.activate_last_dialog()
        for i, (slug, url) in enumerate(zip(media_catalog.PICON_FILES,
                (runtime.PICON_SET_13E, runtime.PICON_SET_19E, runtime.PICON_SET_COMBINED))):
            chooser['rows'].moveToIndex(i)
            assert chooser['sample'].path.endswith('/picons/' + slug + '.png')
            chooser['actions'].actions['info']()
            assert session.last[0] is appearance.PreviewScreen and session.last[1][1] == chooser['sample'].path
            chooser.select()
            assert chooser.result[0][1] == url
        chooser['actions'].actions['yellow']()
        assert chooser['backdrop'].background == '#E7EBEE'
        chooser.enlarge()
        enlarged = session.activate_last_dialog()
        assert enlarged._sample_background == '#E7EBEE'
        enlarged['background_actions'].actions['yellow']()
        assert enlarged.instance.background == '#182633'
        enlarged.execEnd()
        chooser['actions'].actions['yellow']()
        assert chooser['backdrop'].background == '#182633'
        callback(chooser.result[0])
        assert session.last[0] is runtime.ChoiceBox
        assert session.last[2]['list'][0][1] == '/usr/share/enigma2/picon'
        chooser['actions'].actions['cancel']()
        assert chooser.result == (None,)
        chooser.execEnd()
    appearance.settings()[2].value=False
    panel._prompt_picon_pack('Picon')
    assert session.last[0] is runtime.ChoiceBox
    appearance.settings()[2].value=True
    panel.set_language('PL')
    panel['appearance_actions'].actions['menu']()
    assert session.last[0] is appearance.AppearanceScreen
    assert len(os.listdir(skin_previews.BUNDLED)) >= 12
    panel._get_backup_path=lambda: '/test/backups'
    captured=[]
    real_install = runtime.install_archive
    runtime.install_archive=lambda *args,**kwargs: captured.append((args,kwargs))
    for variant in ('deps_only','install_basic_no_picons','install_with_picons'):
        panel._start_super_wizard(variant, ('flash','/usr/share/enigma2/picon') if variant=='install_with_picons' else None)
        cls,_,kw=session.last
        assert cls is runtime.WizardProgressScreen
        assert ('channel_list' in kw['steps'])==(variant!='deps_only')
        if variant!='deps_only':
            wizard=cls(session,**kw)
            wizard._wizard_step_channel_list()
            args,kw2=captured[-1]
            assert args[2]==runtime.WIZARD_CHANNEL_URL
            assert kw2['channel_install_mode']=='replace' and kw2['backup_dir']=='/test/backups'
            wizard.running=True
            wizard.cancelled=True
            wizard._step_done({'success':True})
            assert wizard.result==()
    old=session.last
    panel._start_super_wizard('install_with_picons',None)
    assert session.last is old
    runtime.install_archive=real_install
    real_install(session,'SAT',runtime.WIZARD_CHANNEL_URL,action_type='channels')
    assert [c[1] for c in session.last[2]['list']]==['preserve','replace','cancel']
    check_theme_controls(panel, session, appearance, modern)
    print('OK | Python %d.%d | %d distinct menu actions per language | %d tabs | themes, icons, previews, wizard and manual mode' %
          (sys.version_info[0],sys.version_info[1],len(observations[0]),len(panel.tabs)))


if __name__=='__main__':
    exercise()
