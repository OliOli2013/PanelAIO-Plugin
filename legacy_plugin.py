# -*- coding: utf-8 -*-
"""Panel AIO
by Paweł Pawełek | aio-iptv@wp.pl
Wersja 14.0.0
UNIVERSAL VERSION (Python 2 & Python 3 Compatible)

Kompletna wersja repozytoryjna przygotowana do publikacji na GitHubie
i dalszej przebudowy architektury bez gubienia zgodności runtime.
"""
from __future__ import print_function
from __future__ import absolute_import

# === IMPORTY SYSTEMOWE I KOMPATYBILNOŚĆ ===
import sys
import os
import socket
import datetime
import subprocess
import shutil
import re
import json
import time
import io
import gc
import tempfile
import inspect
import hashlib
import base64
from threading import Thread, Timer
from twisted.internet import reactor

# Wykrywanie wersji Pythona
IS_PY2 = sys.version_info[0] < 3
IS_PY3 = sys.version_info[0] >= 3

# --- String helpers (critical for Python 2 Enigma2 MenuList) ---
# Enigma2's MenuList on many Python2 images expects native `str` (bytes). Passing `unicode`
# may render as "<not-a-string>" or randomly drop list labels depending on code-path.
try:
    _unicode_type = unicode  # noqa: F821 (Py2)
except Exception:
    _unicode_type = str

def ensure_unicode(val):
    """Return a text (unicode on Py2) representation for safe internal processing."""
    if val is None:
        return u"" if IS_PY2 else ""
    if IS_PY2:
        try:
            if isinstance(val, _unicode_type):
                return val
        except Exception:
            pass
        # bytes -> unicode
        try:
            return val.decode("utf-8", "ignore")
        except Exception:
            try:
                return _unicode_type(str(val), "utf-8", "ignore")
            except Exception:
                return u""
    # Py3
    try:
        return str(val)
    except Exception:
        return ""

def _encode_action_payload(kind, url, bouquet_id, name):
    payload = {'kind': ensure_unicode(kind), 'url': ensure_unicode(url), 'bouquet_id': ensure_unicode(bouquet_id), 'name': ensure_unicode(name)}
    raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    token = base64.urlsafe_b64encode(raw)
    if not isinstance(token, str):
        token = token.decode('ascii')
    return token.rstrip('=')


def _decode_action_payload(token, expected_kind):
    token = ensure_unicode(token).strip()
    if not re.match(r'^[A-Za-z0-9_-]+$', token):
        raise ValueError('invalid encoded action')
    token += '=' * ((4 - len(token) % 4) % 4)
    raw = base64.urlsafe_b64decode(token.encode('ascii'))
    if not isinstance(raw, str):
        raw = raw.decode('utf-8')
    data = json.loads(raw)
    if not isinstance(data, dict) or ensure_unicode(data.get('kind')) != ensure_unicode(expected_kind):
        raise ValueError('unexpected action kind')
    url = ensure_unicode(data.get('url', '')).strip()
    bouquet_id = ensure_unicode(data.get('bouquet_id', '')).strip()
    name = ensure_unicode(data.get('name', '')).strip()
    if not url or not bouquet_id:
        raise ValueError('incomplete action payload')
    return url, bouquet_id, name

def ensure_str(val):
    """Return native string type for UI widgets.

    - Py2: bytes (utf-8)
    - Py3: str
    """
    if val is None:
        return ""
    if IS_PY2:
        try:
            if isinstance(val, _unicode_type):
                return val.encode("utf-8")
        except Exception:
            pass
        try:
            # already bytes or other primitive
            return str(val)
        except Exception:
            try:
                return ensure_unicode(val).encode("utf-8")
            except Exception:
                return ""
    try:
        return str(val)
    except Exception:
        return ""

# Fix dla polskich znaków i kodowania w Python 2
if IS_PY2:
    try:
        reload(sys)
        sys.setdefaultencoding('utf-8')
    except Exception:
        pass

# Kompatybilność sieciowa (urllib vs urllib2)
try:
    # Python 3
    from urllib.request import urlopen, Request
    from urllib.parse import urlparse, quote
except ImportError:
    # Python 2
    from urllib2 import urlopen, Request
    from urlparse import urlparse
    from urllib import quote

# === POLYFILLS (Funkcje brakujące w Python 2) ===

# 1. shutil.which (Dla Python 2)
if not hasattr(shutil, "which"):
    def shutil_which(cmd, mode=os.F_OK | os.X_OK, path=None):
        def _access_check(fn, mode):
            return (os.path.exists(fn) and os.access(fn, mode) and not os.path.isdir(fn))

        if os.path.dirname(cmd):
            if _access_check(cmd, mode):
                return cmd
            return None

        if path is None:
            path = os.environ.get("PATH", os.defpath)
        if not path:
            return None
        path = path.split(os.pathsep)

        if sys.platform == "win32":
            if not os.curdir in path:
                path.insert(0, os.curdir)
            pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
            if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
                files = [cmd]
            else:
                files = [cmd + ext for ext in pathext]
        else:
            files = [cmd]

        seen = set()
        for dir in path:
            normdir = os.path.normcase(dir)
            if not normdir in seen:
                seen.add(normdir)
                for thefile in files:
                    name = os.path.join(dir, thefile)
                    if _access_check(name, mode):
                        return name
        return None
else:
    shutil_which = shutil.which

# 2. shutil.disk_usage (Dla Python 2)
if not hasattr(shutil, "disk_usage"):
    class _DiskUsage(object):
        def __init__(self, total, used, free):
            self.total = total
            self.used = used
            self.free = free
            
    def shutil_disk_usage(path):
        try:
            st = os.statvfs(path)
            free = st.f_bavail * st.f_frsize
            total = st.f_blocks * st.f_frsize
            used = (st.f_blocks - st.f_bfree) * st.f_frsize
            return _DiskUsage(total, used, free)
        except Exception:
            return _DiskUsage(0, 0, 0)
else:
    shutil_disk_usage = shutil.disk_usage

# === IMPORTY ENIGMA2 ===
try:
    from enigma import eDVBDB, eTimer, getDesktop
except Exception:
    from enigma import eDVBDB, eTimer
    getDesktop = None
from Screens.Screen import Screen
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop
from Screens.ChoiceBox import ChoiceBox
from Screens.InputBox import InputBox
try:
    from Components.Input import Input
except Exception:
    Input = None
from Components.ActionMap import ActionMap
from Components.Label import Label
try:
    from Components.config import config, ConfigSubsection, ConfigSelection, ConfigYesNo, configfile
except Exception:
    config = None
    ConfigSubsection = None
    ConfigSelection = None
    ConfigYesNo = None
    configfile = None

# --- Persistent settings (v6.0) ---
if config is not None:
    try:
        if not hasattr(config.plugins, "panelaio"):
            config.plugins.panelaio = ConfigSubsection()
        if not hasattr(config.plugins.panelaio, "auto_ram_interval"):
            config.plugins.panelaio.auto_ram_interval = ConfigSelection(
                default="off",
                choices=[("off", "off"), ("10", "10"), ("30", "30"), ("60", "60")]
            )
        if not hasattr(config.plugins.panelaio, 'language'):
            config.plugins.panelaio.language = ConfigSelection(default='auto', choices=[('auto', 'auto'), ('PL', 'PL'), ('EN', 'EN')])
        # Show/Hide AIO Panel entry in receiver main/system menu
        if ConfigYesNo is not None and not hasattr(config.plugins.panelaio, "show_in_menu"):
            config.plugins.panelaio.show_in_menu = ConfigYesNo(default=True)
    except Exception as e:
        print("[AIO Panel] Config init error:", e)


# --- Menu visibility helpers (v12) ---
# Some Enigma2 images do not persist custom ConfigSubsection values reliably until a
# full settings save/restart.  Keep a small fallback file as the source of truth for
# the AIO entry in the receiver main/system menu.
MENU_VISIBILITY_FALLBACK_FILE = "/etc/enigma2/.panelaio_show_in_menu"

def _ensure_panelaio_config():
    try:
        if config is None or ConfigSubsection is None:
            return False
        if not hasattr(config.plugins, "panelaio"):
            config.plugins.panelaio = ConfigSubsection()
        if ConfigYesNo is not None and not hasattr(config.plugins.panelaio, "show_in_menu"):
            config.plugins.panelaio.show_in_menu = ConfigYesNo(default=True)
        return hasattr(config.plugins.panelaio, "show_in_menu")
    except Exception as e:
        print("[AIO Panel] Menu visibility config init error:", e)
        return False

def _bool_from_text(value, default=True):
    txt = ensure_unicode(value).strip().lower()
    if txt in ("1", "true", "yes", "on", "enabled", "wlaczone", "włączone"):
        return True
    if txt in ("0", "false", "no", "off", "disabled", "wylaczone", "wyłączone"):
        return False
    return default

def _read_menu_visibility_fallback():
    try:
        if os.path.exists(MENU_VISIBILITY_FALLBACK_FILE):
            with open(MENU_VISIBILITY_FALLBACK_FILE, "r") as f:
                return _bool_from_text(f.read(), True)
    except Exception as e:
        print("[AIO Panel] Menu visibility fallback read error:", e)
    return None

def _write_menu_visibility_fallback(value):
    try:
        parent = os.path.dirname(MENU_VISIBILITY_FALLBACK_FILE)
        if parent and not os.path.exists(parent):
            os.makedirs(parent)
        with open(MENU_VISIBILITY_FALLBACK_FILE, "w") as f:
            f.write("1\n" if value else "0\n")
        return True
    except Exception as e:
        print("[AIO Panel] Menu visibility fallback write error:", e)
        return False

def _get_show_in_menu_setting(default=True):
    fallback = _read_menu_visibility_fallback()
    if fallback is not None:
        try:
            if _ensure_panelaio_config():
                config.plugins.panelaio.show_in_menu.value = bool(fallback)
        except Exception:
            pass
        return bool(fallback)
    try:
        if _ensure_panelaio_config():
            return bool(config.plugins.panelaio.show_in_menu.value)
    except Exception:
        pass
    return bool(default)

def _set_show_in_menu_setting(value):
    value = bool(value)
    saved = False
    try:
        if _ensure_panelaio_config():
            config.plugins.panelaio.show_in_menu.value = value
            try:
                config.plugins.panelaio.show_in_menu.save()
            except Exception:
                pass
            try:
                if configfile is not None:
                    configfile.save()
            except Exception:
                pass
            saved = True
    except Exception as e:
        print("[AIO Panel] Menu visibility config save error:", e)
    return _write_menu_visibility_fallback(value) or saved

try:
    from Components.ScrollLabel import ScrollLabel
except Exception:
    ScrollLabel = None
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileExists
try:
    from Plugins.SystemPlugins.PanelAIO.core.runtime_safety import (
        invoke_callback as _invoke_safe_callback,
        run_commands as _run_commands_safe,
        is_https_allowed as _is_https_allowed,
        unique_tmp_dir as _unique_tmp_dir,
        cleanup_owned_tmp as _cleanup_owned_tmp,
        encode_service_url as _encode_service_url,
        sanitize_service_name as _sanitize_service_name,
        validate_identifier as _validate_identifier,
        atomic_write as _atomic_write,
    )
except Exception:
    from core.runtime_safety import (
        invoke_callback as _invoke_safe_callback,
        run_commands as _run_commands_safe,
        is_https_allowed as _is_https_allowed,
        unique_tmp_dir as _unique_tmp_dir,
        cleanup_owned_tmp as _cleanup_owned_tmp,
        encode_service_url as _encode_service_url,
        sanitize_service_name as _sanitize_service_name,
        validate_identifier as _validate_identifier,
        atomic_write as _atomic_write,
    )
try:
    from Components.Network import iNetworkInfo, iNetworkInformation
    network = iNetworkInformation()
except ImportError:
    network = None
    try:
        from Components.Network import Network
        iNetworkInfo = Network()
    except ImportError:
        iNetworkInfo = None


# === GLOBALNE ZMIENNE DLA AUTO RAM CLEANER ===
g_auto_ram_timer = eTimer()
g_auto_ram_active = False

def run_auto_ram_clean_task():
    """Niedestrukcyjne zadanie konserwacyjne: GC i stare pliki AIO, bez drop_caches."""
    try:
        gc.collect()
        removed = _cleanup_owned_tmp(PLUGIN_TMP_PATH, 86400)
        print("[AIO Panel] Maintenance: removed {} stale AIO files.".format(removed))
    except Exception as e:
        print("[AIO Panel] Maintenance Error:", e)

# Obsługa timera zależnie od wersji E2 (callback vs timeout.connect)
try:
    g_auto_ram_timer.callback.append(run_auto_ram_clean_task)
except AttributeError:
    g_auto_ram_timer.timeout.connect(run_auto_ram_clean_task)

def _apply_auto_ram_from_config():
    """Restore Auto RAM Cleaner setting after GUI/system restart."""
    global g_auto_ram_active
    try:
        if config is None or not hasattr(config.plugins, "panelaio") or not hasattr(config.plugins.panelaio, "auto_ram_interval"):
            return
        val = getattr(config.plugins.panelaio.auto_ram_interval, "value", "off")
        if val and val != "off":
            minutes = int(val)
            g_auto_ram_timer.start(minutes * 60000, False)
            g_auto_ram_active = True
            print("[AIO Panel] Auto RAM Cleaner restored: {} min".format(minutes))
        else:
            g_auto_ram_timer.stop()
            g_auto_ram_active = False
    except Exception as e:
        print("[AIO Panel] Auto RAM apply error:", e)


# === GLOBALNE ===
PLUGIN_PATH = os.path.dirname(os.path.realpath(__file__))
PLUGIN_TMP_PATH = "/tmp/PanelAIO/"
PLUGIN_ICON_PATH = os.path.join(PLUGIN_PATH, "logo.png")
PLUGIN_SELECTION_PATH = os.path.join(PLUGIN_PATH, "selection.png")
"""QR assets.

Enigma2 Pixmap widgets may crop large images if scaling isn't enabled. To make the QR reliable on
different images (OpenATV/OpenPLi/VTi/Hyperion), we ship two sizes:

 - qr_support.png : big QR for the Support screen
 - qr_header.png  : small QR for the header
"""
PLUGIN_QR_CODE_BIG_PATH = os.path.join(PLUGIN_PATH, "qr_support.png")
PLUGIN_QR_CODE_SMALL_PATH = os.path.join(PLUGIN_PATH, "qr_header.png")
PLUGIN_PP_LOGO_PATH = os.path.join(PLUGIN_PATH, "pp_logo.png")
PLUGIN_SEL_MENU_PATH = os.path.join(PLUGIN_PATH, "sel_menu.png")
PLUGIN_SEL_SIDEBAR_PATH = os.path.join(PLUGIN_PATH, "sel_sidebar.png")
AIO_TIPS_FILE = os.path.join(PLUGIN_PATH, "aio_tips.txt")

# --- VERSION: single source of truth (version.txt) ---
# Fixes endless update prompt after GitHub update when version.txt and VER diverge.
def _read_local_version(default="0.0"):
    try:
        p = os.path.join(PLUGIN_PATH, "version.txt")
        with open(p, "r") as f:
            v = f.read().strip()
        return v if v else default
    except Exception:
        return default

VER = _read_local_version("14.0.0")
CUSTOM_UPDATES_MANIFEST_LOCAL = os.path.join(PLUGIN_PATH, "custom_updates.json")
CUSTOM_UPDATES_MANIFEST_REMOTE = "https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/custom_updates.json"

DATE = str(datetime.date.today())
# Stopka dynamiczna zależna od Pythona
FOOT = "AIO {} | {} | by Paweł Pawełek | aio-iptv@wp.pl".format(VER, "Py3" if IS_PY3 else "Py2") 

# Legenda dla przycisków kolorowych
LEGEND_PL_COLOR = r"\c00ff0000●\c00ffffff PL \c0000ff00●\c00ffffff EN \c00ffff00●\c00ffffff Restart GUI \c000000ff●\c00ffffff Aktualizuj  CH±: Kategorie  INFO: QR"
LEGEND_EN_COLOR = r"\c00ff0000●\c00ffffff PL \c0000ff00●\c00ffffff EN \c00ffff00●\c00ffffff Restart GUI \c000000ff●\c00ffffff Update  CH±: Categories  INFO: QR"
LEGEND_INFO = " " 

# === ADAPTIVE UI HELPERS ===
def _desktop_size():
    try:
        if getDesktop is not None:
            desktop = getDesktop(0)
            if desktop is not None:
                sz = desktop.size()
                return int(sz.width()), int(sz.height())
    except Exception:
        pass
    return 1280, 720

def _is_small_ui():
    w, h = _desktop_size()
    return w <= 1024 or h <= 576

def _is_hd_ui():
    w, h = _desktop_size()
    return w <= 1280 or h <= 720

def _super_wizard_choice_skin():
    if _is_small_ui():
        return """
    <screen position="center,center" size="690,420" title="Super Konfigurator">
        <widget name="list" position="18,18" size="654,240" scrollbarMode="showOnDemand" />
        <widget name="description" position="18,272" size="654,92" font="Regular;18" halign="center" valign="center" foregroundColor="#00C2FF" />
        <widget name="actions" position="18,386" size="654,22" font="Regular;16" halign="right" />
    </screen>"""
    if _is_hd_ui():
        return """
    <screen position="center,center" size="760,460" title="Super Konfigurator">
        <widget name="list" position="20,20" size="720,270" scrollbarMode="showOnDemand" />
        <widget name="description" position="20,305" size="720,95" font="Regular;20" halign="center" valign="center" foregroundColor="#00C2FF" />
        <widget name="actions" position="20,420" size="720,24" font="Regular;18" halign="right" />
    </screen>"""
    return """
    <screen position="center,center" size="800,500" title="Super Konfigurator">
        <widget name="list" position="20,20" size="760,300" scrollbarMode="showOnDemand" />
        <widget name="description" position="20,340" size="760,100" font="Regular;22" halign="center" valign="center" foregroundColor="#00C2FF" />
        <widget name="actions" position="20,460" size="760,30" font="Regular;20" halign="right" />
    </screen>"""

def _wizard_progress_skin():
    if _is_small_ui():
        return """
    <screen position="center,center" size="660,300" title="Super Konfigurator">
        <widget name="message" position="24,24" size="612,252" font="Regular;21" halign="center" valign="center" />
    </screen>"""
    if _is_hd_ui():
        return """
    <screen position="center,center" size="720,340" title="Super Konfigurator">
        <widget name="message" position="30,30" size="660,280" font="Regular;24" halign="center" valign="center" />
    </screen>"""
    return """
    <screen position="center,center" size="800,400" title="Super Konfigurator">
        <widget name="message" position="40,40" size="720,320" font="Regular;28" halign="center" valign="center" />
    </screen>"""

def _support_screen_skin():
    if _is_small_ui():
        return """
    <screen position="center,center" size="680,500" title="Wsparcie / Support" backgroundColor="#0B0F14">
        <eLabel position="0,0" size="680,500" backgroundColor="#0B0F14" zPosition="-1" />
        <eLabel position="0,0" size="680,64" backgroundColor="#121824" zPosition="-1" />
        <widget name="title" position="16,14" size="648,30" font="Regular;22" halign="center" foregroundColor="#00C2FF" transparent="1" />
        <widget name="qr_big" position="160,86" size="360,360" pixmap="{qr}" alphatest="blend" scale="1" />
        <widget name="qr_huge" position="24,78" size="632,400" pixmap="{qr}" alphatest="blend" scale="1" />
        <widget name="txt" position="16,468" size="648,20" font="Regular;16" halign="center" valign="center" foregroundColor="#D7DEE9" transparent="1" />
    </screen>""".format(qr=PLUGIN_QR_CODE_BIG_PATH)
    if _is_hd_ui():
        return """
    <screen position="center,center" size="760,560" title="Wsparcie / Support" backgroundColor="#0B0F14">
        <eLabel position="0,0" size="760,560" backgroundColor="#0B0F14" zPosition="-1" />
        <eLabel position="0,0" size="760,70" backgroundColor="#121824" zPosition="-1" />
        <widget name="title" position="20,15" size="720,34" font="Regular;26" halign="center" foregroundColor="#00C2FF" transparent="1" />
        <widget name="qr_big" position="170,88" size="420,420" pixmap="{qr}" alphatest="blend" scale="1" />
        <widget name="qr_huge" position="30,82" size="700,450" pixmap="{qr}" alphatest="blend" scale="1" />
        <widget name="txt" position="20,525" size="720,24" font="Regular;18" halign="center" valign="center" foregroundColor="#D7DEE9" transparent="1" />
    </screen>""".format(qr=PLUGIN_QR_CODE_BIG_PATH)
    return """
    <screen position="center,center" size="900,650" title="Wsparcie / Support" backgroundColor="#0B0F14">
        <eLabel position="0,0" size="900,650" backgroundColor="#0B0F14" zPosition="-1" />
        <eLabel position="0,0" size="900,80" backgroundColor="#121824" zPosition="-1" />
        <widget name="title" position="20,18" size="860,40" font="Regular;30" halign="center" foregroundColor="#00C2FF" transparent="1" />
        <widget name="qr_big" position="200,100" size="500,500" pixmap="{qr}" alphatest="blend" scale="1" />
        <widget name="qr_huge" position="50,90" size="800,540" pixmap="{qr}" alphatest="blend" scale="1" />
        <widget name="txt" position="20,610" size="860,35" font="Regular;22" halign="center" valign="center" foregroundColor="#D7DEE9" transparent="1" />
    </screen>""".format(qr=PLUGIN_QR_CODE_BIG_PATH)

def _aio_tip_screen_skin():
    if _is_small_ui():
        return """
    <screen position="center,center" size="720,320" title="AIO Tip dnia">
        <widget name="title" position="18,14" size="684,30" font="Regular;22" halign="center" valign="center" />
        <widget name="counter" position="18,48" size="684,22" font="Regular;18" halign="center" valign="center" foregroundColor="#D7DEE9" />
        <widget name="text" position="24,84" size="672,170" font="Regular;22" halign="center" valign="center" />
        <widget name="help" position="18,284" size="684,20" font="Regular;16" halign="center" valign="center" foregroundColor="#8A94A6" />
    </screen>"""
    if _is_hd_ui():
        return """
    <screen position="center,center" size="820,360" title="AIO Tip dnia">
        <widget name="title" position="20,16" size="780,34" font="Regular;26" halign="center" valign="center" />
        <widget name="counter" position="20,56" size="780,24" font="Regular;20" halign="center" valign="center" foregroundColor="#D7DEE9" />
        <widget name="text" position="28,96" size="764,190" font="Regular;25" halign="center" valign="center" />
        <widget name="help" position="20,324" size="780,22" font="Regular;18" halign="center" valign="center" foregroundColor="#8A94A6" />
    </screen>"""
    return """
    <screen position="center,center" size="980,420" title="AIO Tip dnia">
        <widget name="title" position="24,18" size="932,38" font="Regular;30" halign="center" valign="center" />
        <widget name="counter" position="24,62" size="932,26" font="Regular;22" halign="center" valign="center" foregroundColor="#D7DEE9" />
        <widget name="text" position="34,110" size="912,220" font="Regular;30" halign="center" valign="center" />
        <widget name="help" position="24,382" size="932,24" font="Regular;20" halign="center" valign="center" foregroundColor="#8A94A6" />
    </screen>"""

def _info_screen_skin():
    if _is_small_ui():
        return """
    <screen position="center,center" size="690,430" title="Informacje o AIO Panel">
        <widget name="title" position="16,16" size="658,26" font="Regular;20" halign="center" valign="center" />
        <widget name="author" position="16,48" size="658,20" font="Regular;16" halign="center" valign="center" />
        <widget name="facebook" position="16,70" size="658,20" font="Regular;16" halign="center" valign="center" />
        <widget name="legal_title" position="16,100" size="658,24" font="Regular;19" halign="center" foregroundColor="yellow" />
        <widget name="legal_text" position="16,132" size="658,164" font="Regular;15" halign="center" valign="top" />
        <widget name="changelog_title" position="16,304" size="658,24" font="Regular;19" halign="center" foregroundColor="cyan" />
        <widget name="changelog_text" position="20,336" size="650,76" font="Regular;16" halign="left" valign="top" />
    </screen>"""
    if _is_hd_ui():
        return """
    <screen position="center,center" size="760,470" title="Informacje o AIO Panel">
        <widget name="title" position="20,18" size="720,30" font="Regular;24" halign="center" valign="center" />
        <widget name="author" position="20,54" size="720,22" font="Regular;18" halign="center" valign="center" />
        <widget name="facebook" position="20,78" size="720,22" font="Regular;18" halign="center" valign="center" />
        <widget name="legal_title" position="20,112" size="720,26" font="Regular;22" halign="center" foregroundColor="yellow" />
        <widget name="legal_text" position="20,145" size="720,185" font="Regular;17" halign="center" valign="top" />
        <widget name="changelog_title" position="20,338" size="720,26" font="Regular;22" halign="center" foregroundColor="cyan" />
        <widget name="changelog_text" position="25,372" size="710,85" font="Regular;18" halign="left" valign="top" />
    </screen>"""
    return """
    <screen position="center,center" size="900,540" title="Informacje o AIO Panel">
        <widget name="title" position="20,20" size="860,35" font="Regular;28" halign="center" valign="center" />
        <widget name="author" position="20,60" size="860,25" font="Regular;22" halign="center" valign="center" />
        <widget name="facebook" position="20,85" size="860,25" font="Regular;22" halign="center" valign="center" />
        <widget name="legal_title" position="20,125" size="860,30" font="Regular;24" halign="center" foregroundColor="yellow" />
        <widget name="legal_text" position="20,165" size="860,200" font="Regular;20" halign="center" valign="top" />
        <widget name="changelog_title" position="20,375" size="860,30" font="Regular;26" halign="center" foregroundColor="cyan" />
        <widget name="changelog_text" position="30,415" size="840,105" font="Regular;22" halign="left" valign="top" />
    </screen>"""

def _panel_main_skin():
    if _is_small_ui():
        return """
    <screen name='PanelAIO' position='center,center' size='900,560' title='AIO Panel' backgroundColor='#0B0F14' zPosition='99'>
        <eLabel position='0,0' size='900,560' backgroundColor='#0B0F14' zPosition='-10' />
        <eLabel position='0,76' size='900,434' backgroundColor='#0B0F14' zPosition='-9' />
        <eLabel position='0,0' size='900,74' backgroundColor='#121824' zPosition='-1' />
        <widget name='qr_code_small' position='14,18' size='36,36' pixmap="{qr}" alphatest='blend' scale='1' />
        <widget name='pp_logo' position='850,18' size='36,36' pixmap="{pp_logo}" alphatest='blend' scale='1' />
        <widget name='support_label' position='58,8' size='300,52' font='Regular;18' halign='left' valign='center' foregroundColor='#00C2FF' transparent='1' />
        <widget name='title_label' position='362,9' size='478,28' font='Regular;24' halign='right' valign='center' foregroundColor='#00C2FF' transparent='1' />
        <widget name='health' position='362,40' size='478,20' font='Regular;16' halign='right' valign='center' foregroundColor='#A9B4C2' transparent='1' />
        <eLabel position='0,74' size='900,2' backgroundColor='#00C2FF' />

        <widget name='sidebar' position='0,76' size='220,434' itemHeight='46' font='Regular;19' scrollbarMode='showOnDemand' selectionPixmap='{sel_sidebar}' foregroundColor='#00C2FF' foregroundColorSelected='#FFFFFF' backgroundColor='#0B0F14' transparent='0'/>
        <eLabel position='220,76' size='2,434' backgroundColor='#203346' />
        <widget name='menu' position='234,76' size='650,370' itemHeight='36' font='Regular;18' scrollbarMode='showOnDemand' selectionPixmap='{sel_menu}' foregroundColor='#D7DEE9' foregroundColorSelected='#FFFFFF' backgroundColor='#0B0F14' transparent='0'/>
        <widget name='function_description' position='234,450' size='650,50' font='Regular;16' halign='left' valign='top' foregroundColor='#00C2FF' backgroundColor='#121824' transparent='0' />
        <widget name='tabs_display' position='0,0' size='0,0' font='Regular;1' transparent='1' />

        <eLabel position='0,510' size='900,50' backgroundColor='#121824' zPosition='-1' />
        <widget name='update_status' position='10,518' size='300,18' font='Regular;15' halign='left' foregroundColor='#FFD200' transparent='1'/>
        <widget name='legend' position='320,518' size='570,18' font='Regular;16' halign='right' foregroundColor='#D7DEE9' transparent='1'/>
        <widget name='footer' position='10,538' size='880,16' font='Regular;14' halign='center' valign='center' foregroundColor='#8A94A6' transparent='1'/>
    </screen>""".format(qr=PLUGIN_QR_CODE_SMALL_PATH, pp_logo=PLUGIN_PP_LOGO_PATH, sel_menu=PLUGIN_SEL_MENU_PATH, sel_sidebar=PLUGIN_SEL_SIDEBAR_PATH)
    if _is_hd_ui():
        return """
    <screen name='PanelAIO' position='center,center' size='980,620' title='AIO Panel' backgroundColor='#0B0F14' zPosition='99'>
        <eLabel position='0,0' size='980,620' backgroundColor='#0B0F14' zPosition='-10' />
        <eLabel position='0,84' size='980,490' backgroundColor='#0B0F14' zPosition='-9' />
        <eLabel position='0,0' size='980,82' backgroundColor='#121824' zPosition='-1' />
        <widget name='qr_code_small' position='16,20' size='40,40' pixmap="{qr}" alphatest='blend' scale='1' />
        <widget name='pp_logo' position='924,20' size='40,40' pixmap="{pp_logo}" alphatest='blend' scale='1' />
        <widget name='support_label' position='66,9' size='350,60' font='Regular;20' halign='left' valign='center' foregroundColor='#00C2FF' transparent='1' />
        <widget name='title_label' position='420,10' size='490,30' font='Regular;28' halign='right' valign='center' foregroundColor='#00C2FF' transparent='1' />
        <widget name='health' position='420,44' size='490,22' font='Regular;18' halign='right' valign='center' foregroundColor='#A9B4C2' transparent='1' />
        <eLabel position='0,82' size='980,2' backgroundColor='#00C2FF' />

        <widget name='sidebar' position='0,84' size='240,490' itemHeight='52' font='Regular;21' scrollbarMode='showOnDemand' selectionPixmap='{sel_sidebar}' foregroundColor='#00C2FF' foregroundColorSelected='#FFFFFF' backgroundColor='#0B0F14' transparent='0'/>
        <eLabel position='240,84' size='2,490' backgroundColor='#203346' />
        <widget name='menu' position='255,84' size='710,420' itemHeight='40' font='Regular;20' scrollbarMode='showOnDemand' selectionPixmap='{sel_menu}' foregroundColor='#D7DEE9' foregroundColorSelected='#FFFFFF' backgroundColor='#0B0F14' transparent='0'/>
        <widget name='function_description' position='255,508' size='710,56' font='Regular;18' halign='left' valign='top' foregroundColor='#00C2FF' backgroundColor='#121824' transparent='0' />
        <widget name='tabs_display' position='0,0' size='0,0' font='Regular;1' transparent='1' />

        <eLabel position='0,574' size='980,46' backgroundColor='#121824' zPosition='-1' />
        <widget name='update_status' position='10,580' size='330,20' font='Regular;17' halign='left' foregroundColor='#FFD200' transparent='1'/>
        <widget name='legend' position='350,580'  size='620,20'  font='Regular;18' halign='right' foregroundColor='#D7DEE9' transparent='1'/>
        <widget name='footer' position='10,600' size='960,16' font='Regular;15' halign='center' valign='center' foregroundColor='#8A94A6' transparent='1'/>
    </screen>""".format(qr=PLUGIN_QR_CODE_SMALL_PATH, pp_logo=PLUGIN_PP_LOGO_PATH, sel_menu=PLUGIN_SEL_MENU_PATH, sel_sidebar=PLUGIN_SEL_SIDEBAR_PATH)
    return """
    <screen name='PanelAIO' position='center,center' size='1100,690' title='AIO Panel' backgroundColor='#0B0F14' zPosition='99'>
        <eLabel position='0,0' size='1100,690' backgroundColor='#0B0F14' zPosition='-10' />
        <eLabel position='0,92' size='1100,548' backgroundColor='#0B0F14' zPosition='-9' />
        <eLabel position='0,0' size='1100,90' backgroundColor='#121824' zPosition='-1' />
        <widget name='qr_code_small' position='18,23' size='44,44' pixmap="{qr}" alphatest='blend' scale='1' />
        <widget name='pp_logo' position='1036,23' size='44,44' pixmap="{pp_logo}" alphatest='blend' scale='1' />
        <widget name='support_label' position='72,10' size='420,70' font='Regular;22' halign='left' valign='center' foregroundColor='#00C2FF' transparent='1' />
        <widget name='title_label' position='470,12' size='560,36' font='Regular;32' halign='right' valign='center' foregroundColor='#00C2FF' transparent='1' />
        <widget name='health' position='470,52' size='560,26' font='Regular;20' halign='right' valign='center' foregroundColor='#A9B4C2' transparent='1' />
        <eLabel position='0,90' size='1100,2' backgroundColor='#00C2FF' />

        <widget name='sidebar' position='0,92' size='270,548' itemHeight='58' font='Regular;24' scrollbarMode='showOnDemand' selectionPixmap='{sel_sidebar}' foregroundColor='#00C2FF' foregroundColorSelected='#FFFFFF' backgroundColor='#0B0F14' transparent='0'/>
        <eLabel position='270,92' size='2,548' backgroundColor='#203346' />
        <widget name='menu' position='285,92' size='800,468' itemHeight='44' font='Regular;22' scrollbarMode='showOnDemand' selectionPixmap='{sel_menu}' foregroundColor='#D7DEE9' foregroundColorSelected='#FFFFFF' backgroundColor='#0B0F14' transparent='0'/>
        <widget name='function_description' position='285,565' size='800,70' font='Regular;20' halign='left' valign='top' foregroundColor='#00C2FF' backgroundColor='#121824' transparent='0' />
        <widget name='tabs_display' position='0,0' size='0,0' font='Regular;1' transparent='1' />

        <eLabel position='0,640' size='1100,50' backgroundColor='#121824' zPosition='-1' />
        <widget name='update_status' position='10,646' size='380,22' font='Regular;18' halign='left' foregroundColor='#FFD200' transparent='1'/>
        <widget name='legend' position='400,646'  size='690,22'  font='Regular;20' halign='right' foregroundColor='#D7DEE9' transparent='1'/>
        <widget name='footer' position='10,668' size='1080,18' font='Regular;16' halign='center' valign='center' foregroundColor='#8A94A6' transparent='1'/>
    </screen>""".format(qr=PLUGIN_QR_CODE_SMALL_PATH, pp_logo=PLUGIN_PP_LOGO_PATH, sel_menu=PLUGIN_SEL_MENU_PATH, sel_sidebar=PLUGIN_SEL_SIDEBAR_PATH)

# === TŁUMACZENIA ===
TRANSLATIONS = {
    "PL": {
        "support_text": "Wesprzyj rozwój wtyczki",
        "update_available_title": "Dostępna nowa wersja!",
        "update_available_msg": """Dostępna jest nowa wersja AIO Panel: {latest_ver}
Twoja wersja: {current_ver}

Lista zmian:
{changelog}
Czy chcesz ją teraz zainstalować?\n\nPo instalacji lub aktualizacji zalecany jest pełny restart tunera!""",
        "already_latest": "Używasz najnowszej wersji wtyczki ({ver}).",
        "update_check_error": "Nie można sprawdzić dostępności aktualizacji.\nSprawdź połączenie z internetem.",
        "update_generic_error": "Wystąpił błąd podczas sprawdzania aktualizacji.",
        "update_status_label": "🔔 Dostępna aktualizacja AIO",
        "update_menu_label": "🔔 Dostępna aktualizacja AIO Panel {ver} - pokaż zmiany",
        "update_changelog_unavailable": "Nie udało się pobrać listy zmian. Spróbuj ponownie później.",
        "loading_text": "Ładowanie...",
        "loading_error_text": "Błąd wczytywania danych",
        "sk_wizard_title": ">>> Super Konfigurator (Pierwsza Instalacja)",
        "sk_choice_title": "Super Konfigurator - Wybierz opcję",
        "sk_option_deps": "1) [PKG] Zainstaluj tylko zależności (wget, tar, unzip)",
        "sk_option_basic_no_picons": "2) [START] Podstawowa Konfiguracja (bez Picon)",
        "sk_option_full_picons": "3) [FULL] Pełna Konfiguracja (z Piconami)",
        "sk_option_cancel": "[X] Anuluj",
        "sk_confirm_deps": "Czy na pewno chcesz zainstalować tylko podstawowe zależności systemowe?",
        "sk_confirm_basic": "Rozpocznie się podstawowa konfiguracja systemu.\n\n- Instalacja zależności\n- Instalacja listy kanałów\n- Instalacja Softcam (skrypt)\n- Instalacja i aktywacja OSCam-Emu\n\nCzy chcesz kontynuować?",
        "sk_confirm_full": "Rozpocznie się pełna konfiguracja systemu.\n\n- Instalacja zależności\n- Instalacja listy kanałów\n- Instalacja Softcam (skrypt)\n- Instalacja i aktywacja OSCam-Emu\n- Instalacja Piconów (duży plik)\n\nCzy chcesz kontynuować?",
        "net_diag_title": "Diagnostyka Sieci",
        "net_diag_wait": "Trwa diagnostyka sieci, proszę czekać...",
        "net_diag_error": "Wystąpił błąd podczas testu prędkości.",
        "net_diag_no_connection": "BŁĄD: Brak połączenia z internetem!",
        "net_diag_results_title": "Wyniki Diagnostyki Sieci",
        "net_diag_local_ip": "IP Tunera (Lokalne):",
        "net_diag_ip": "Publiczne IP:",
        "net_diag_ping": "Ping:",
        "net_diag_download": "Pobieranie:",
        "net_diag_upload": "Wysyłanie:",
        "net_diag_na": "N/A"
    },
    "EN": {
        "support_text": "Support plugin development",
        "update_available_title": "New version available!",
        "update_available_msg": """A new version of AIO Panel is available: {latest_ver}
Your version: {current_ver}

Changelog:
{changelog}
Do you want to install it now?\n\nA manual reboot is recommended after checking that the system is stable.""",
        "already_latest": "You are using the latest version of the plugin ({ver}).",
        "update_check_error": "Could not check for updates.\nPlease check your internet connection.",
        "update_generic_error": "An error occurred while checking for updates.",
        "update_status_label": "🔔 AIO update available",
        "update_menu_label": "🔔 AIO Panel {ver} update available - show changes",
        "update_changelog_unavailable": "Could not download the changelog. Try again later.",
        "loading_text": "Loading...",
        "loading_error_text": "Error loading data",
        "sk_wizard_title": ">>> Super Setup Wizard (First Installation)",
        "sk_choice_title": "Super Setup Wizard - Select an option",
        "sk_option_deps": "1) [PKG] Install dependencies only (wget, tar, unzip)",
        "sk_option_basic_no_picons": "2) [START] Basic Configuration (without Picons)",
        "sk_option_full_picons": "3) [FULL] Full Configuration (with Picons)",
        "sk_option_cancel": "[X] Cancel",
        "sk_confirm_deps": "Are you sure you want to install only the basic system dependencies?",
        "sk_confirm_basic": "A basic system configuration will now begin.\n\n- Install dependencies\n- Install channel list\n- Install Softcam (script)\n- Install and activate OSCam-Emu\n\nDo you want to continue?",
        "sk_confirm_full": "A full system configuration will now begin.\n\n- Install dependencies\n- Install channel list\n- Install Softcam (script)\n- Install and activate OSCam-Emu\n- Install Picons (large file)\n\nDo you want to continue?",
        "net_diag_title": "Network Diagnostics",
        "net_diag_wait": "Running network diagnostics, please wait...",
        "net_diag_error": "An error occurred during the speed test.",
        "net_diag_no_connection": "ERROR: No internet connection!",
        "net_diag_results_title": "Network Diagnostics Results",
        "net_diag_local_ip": "Tuner IP (Local):",
        "net_diag_ip": "Public IP:",
        "net_diag_ping": "Ping:",
        "net_diag_download": "Download:",
        "net_diag_upload": "Upload:",
        "net_diag_na": "N/A"
    }
}

# === POMOCNICZE (GLOBALNE) ===
def _safe_messagebox_open_now(session, message, message_type=MessageBox.TYPE_INFO, timeout=10, on_close=None, default=None):
    """Safe MessageBox opener for skins with broken/strict MessageBox skin applets.

    Some FHD skins (reported: Algare FHD) can crash Enigma2 while applying the
    system MessageBox skin, especially with uncommon kwargs such as
    enable_input=False. AIO must never crash the GUI just because a wait/info
    window cannot be skinned.
    """
    try:
        kwargs = {}
        if timeout is not None:
            kwargs["timeout"] = timeout
        if default is not None:
            kwargs["default"] = default
        if on_close:
            return session.openWithCallback(on_close, MessageBox, message, message_type, **kwargs)
        return session.open(MessageBox, message, message_type, **kwargs)
    except Exception as e:
        print("[AIO Panel] MessageBox blocked by skin compatibility guard:", e)
        try:
            if on_close:
                on_close(False)
        except Exception:
            pass
        return None


def show_message_compat(session, message, message_type=MessageBox.TYPE_INFO, timeout=10, on_close=None):
    def _open_safe():
        _safe_messagebox_open_now(session, message, message_type, timeout=timeout, on_close=on_close)
    if reactor.running:
        reactor.callLater(0.2, _open_safe)
    else:
        _open_safe()

# --- FUNKCJA URUCHAMIANIA W TLE (Dla zadań wewnętrznych) ---
def run_command_in_background(session, title, cmd_list, callback_on_finish=None, stop_on_error=True, redact=None):
    """Run shell commands asynchronously and propagate a structured result.

    No success callback is silently fired after a failed command. Legacy no-argument
    callbacks are invoked only on success; callbacks accepting one argument receive
    the result on both success and failure.
    """
    wait_message = None
    try:
        wait_message = _safe_messagebox_open_now(
            session,
            "Trwa wykonywanie: {}\n\nProszę czekać...".format(title),
            MessageBox.TYPE_INFO,
            timeout=3
        )
    except Exception as e:
        print("[AIO Panel] Wait MessageBox skipped:", e)

    state = {'result': None}

    def command_thread():
        try:
            state['result'] = _run_commands_safe(cmd_list, stop_on_error=stop_on_error, redact=redact)
        except Exception as exc:
            state['result'] = {
                'success': False, 'returncode': 127, 'stdout': '',
                'stderr': ensure_unicode(exc), 'failed_command': '', 'commands': []
            }
        try:
            reactor.callFromThread(on_finish_thread)
        except Exception:
            on_finish_thread()

    def on_finish_thread():
        if wait_message is not None:
            try:
                wait_message.close()
            except Exception:
                pass
        result = state.get('result') or {'success': False, 'returncode': 127, 'stderr': 'No result'}
        if not result.get('success'):
            print("[AIO Panel] Background task failed [{}]: {}".format(title, result.get('stderr', '')))
        if callback_on_finish:
            try:
                _invoke_safe_callback(callback_on_finish, result, noarg_only_on_success=True)
            except Exception as e:
                print("[AIO Panel] callback error:", e)

    thread = Thread(target=command_thread)
    try:
        thread.setDaemon(True)
    except Exception:
        pass
    thread.start()

# Funkcja konsoli (teraz używana do diagnostyki i instalatorów zewnętrznych)
def console_screen_open(session, title, cmds_with_args, callback=None, close_on_finish=False):
    cmds_list = cmds_with_args if isinstance(cmds_with_args, list) else [cmds_with_args]

    def _delayed_console_callback(*args):
        if not callback:
            return
        try:
            # Na części obrazów/skinów bezpośrednie otwieranie MessageBox z onClose Console
            # potrafi wywołać błąd modalny. Krótkie opóźnienie pozwala domknąć Console.
            if reactor.running:
                reactor.callLater(0.4, callback)
            else:
                callback()
        except Exception as e:
            print("[AIO Panel] Console close callback error:", e)

    def _open_console():
        c_dialog = session.open(Console, title=title, cmdlist=cmds_list, closeOnSuccess=close_on_finish)
        if callback:
            c_dialog.onClose.append(_delayed_console_callback)

    if reactor.running:
        reactor.callLater(0.1, _open_console)
    else:
        _open_console()

def prepare_tmp_dir():
    if not os.path.exists(PLUGIN_TMP_PATH):
        try:
            os.makedirs(PLUGIN_TMP_PATH)
        except OSError as e:
            print("[AIO Panel] Error creating tmp dir:", e)


def _read_text_file(path, default=""):
    try:
        with io.open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        return default

def _write_text_file(path, data):
    try:
        directory = os.path.dirname(path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)
        with io.open(path, 'w', encoding='utf-8') as f:
            f.write(ensure_unicode(data))
        return True
    except Exception:
        return False


def _payload_looks_like_html_error(payload):
    try:
        if payload is None:
            return False
        head = payload[:512]
        if not isinstance(head, str):
            try:
                head = head.decode('utf-8', 'ignore')
            except Exception:
                head = str(head)
        head = head.strip().lower()
        if head.startswith('<!doctype') or head.startswith('<html'):
            return True
        if '<html' in head[:256] or '404: not found' in head[:256] or 'accessdenied' in head[:256]:
            return True
    except Exception:
        pass
    return False

def _file_looks_like_html_error(path):
    try:
        if not path or not os.path.exists(path) or os.path.getsize(path) <= 0:
            return False
        with open(path, 'rb') as handle:
            payload = handle.read(512)
        return _payload_looks_like_html_error(payload)
    except Exception:
        return False

def _download_shell_command(url, output_path, expected_type='file'):
    """Build a strict HTTPS downloader command using the bundled safety helper."""
    if not _is_https_allowed(url):
        return "echo '[AIO Panel] ERROR: blocked non-HTTPS or untrusted download URL'; exit 64"
    common = os.path.join(PLUGIN_PATH, 'aio_safe_common.sh')
    validator = os.path.join(PLUGIN_PATH, 'core', 'archive_validator.py')
    return r'''
set -eu
. %s
URL=%s
OUT=%s
EXPECTED=%s
rm -f "$OUT" "$OUT.tmp"
aio_secure_download "$URL" "$OUT" 120 4
aio_not_html "$OUT"
case "$EXPECTED" in
  ipk)
    dd if="$OUT" bs=8 count=1 2>/dev/null | grep -q '^!<arch>'
  ;;
  zip|tar.gz|tgz)
    PY=$(aio_python) || { echo '[AIO Panel] ERROR: Python unavailable for archive validation'; exit 65; }
    "$PY" %s "$OUT"
  ;;
  script|sh)
    [ -s "$OUT" ]
    head -c 2 "$OUT" | grep -q '<!' && { echo '[AIO Panel] ERROR: HTML payload'; exit 66; } || true
  ;;
  file)
    [ -s "$OUT" ]
  ;;
esac
''' % (_safe_shell_arg(common), _safe_shell_arg(url), _safe_shell_arg(output_path), _safe_shell_arg(expected_type or 'file'), _safe_shell_arg(validator))

def _download_url_to_file(url, path, timeout=30, tries=3, allow_insecure_fallback=False):
    """Strict HTTPS download with normal certificate verification only."""
    if not _is_https_allowed(url):
        print('[AIO Panel] blocked download URL: {}'.format(url))
        return False
    tmp_path = path + '.tmp'
    last_error = None
    parent = os.path.dirname(path)
    try:
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
    except Exception:
        return False
    for _idx in range(max(1, int(tries))):
        try:
            request = Request(url, headers={'User-Agent': 'Enigma2/AIO-Panel-14'})
            response = urlopen(request, timeout=timeout)
            try:
                payload = response.read()
            finally:
                try:
                    response.close()
                except Exception:
                    pass
            if payload and not _payload_looks_like_html_error(payload):
                with open(tmp_path, 'wb') as handle:
                    handle.write(payload)
                    handle.flush()
                    try:
                        os.fsync(handle.fileno())
                    except Exception:
                        pass
                os.rename(tmp_path, path)
                return True
            last_error = 'empty or HTML/error response'
        except Exception as exc:
            last_error = exc

        tool_cmds = []
        if _command_exists('wget'):
            tool_cmds.append(['wget', '-4', '-U', 'Enigma2/AIO-Panel-14', '-q', '-T', str(timeout), '-t', '2', '-O', tmp_path, url])
        if _command_exists('curl'):
            tool_cmds.append(['curl', '-fL', '--ipv4', '-A', 'Enigma2/AIO-Panel-14', '--connect-timeout', '15', '--max-time', str(timeout), '-o', tmp_path, url])
        for cmd in tool_cmds:
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                _, stderr = process.communicate()
                if process.returncode == 0 and os.path.isfile(tmp_path) and os.path.getsize(tmp_path) > 0 and not _file_looks_like_html_error(tmp_path):
                    os.rename(tmp_path, path)
                    return True
                last_error = _decode_bytes(stderr) or 'invalid download'
            except Exception as exc:
                last_error = exc
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
    print('[AIO Panel] secure download error for {}: {}'.format(url, last_error))
    return False

def _load_json_from_file(path):
    try:
        raw = _read_text_file(path, '')
        if not raw.strip():
            return None
        raw = raw.lstrip(u'﻿')
        return json.loads(raw)
    except Exception as e:
        print('[AIO Panel] JSON parse error for {}: {}'.format(path, e))
        return None

def _normalize_repo_manifest(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ('entries', 'items', 'lists', 'data'):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []

def _version_to_tuple(version_value):
    try:
        txt = ensure_unicode(version_value).strip()
        parts = re.findall(r"\d+", txt)
        if not parts:
            return (0,)
        return tuple(int(p) for p in parts)
    except Exception:
        return (0,)

def _command_exists(cmd):
    try:
        return shutil_which(cmd) is not None
    except Exception:
        return False


def _decode_bytes(payload):
    if payload is None:
        return ""
    try:
        if IS_PY3:
            if isinstance(payload, bytes):
                return payload.decode("utf-8", "ignore")
            return str(payload)
        try:
            if isinstance(payload, _unicode_type):
                return payload
        except Exception:
            pass
        try:
            return payload.decode("utf-8", "ignore")
        except Exception:
            return str(payload)
    except Exception:
        return ""

def _kill_process_safe(process):
    try:
        process.kill()
        return
    except Exception:
        pass
    try:
        process.terminate()
        return
    except Exception:
        pass
    try:
        os.kill(process.pid, 9)
    except Exception:
        pass

def _run_shell_capture(cmd, timeout=30):
    process = None
    try:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if IS_PY3:
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except getattr(subprocess, 'TimeoutExpired', Exception):
                _kill_process_safe(process)
                try:
                    stdout, stderr = process.communicate()
                except Exception:
                    stdout, stderr = b'', b''
                return 255, _decode_bytes(stdout), 'Timeout'
        else:
            timed_out = [False]
            timer = None
            try:
                if timeout and int(timeout) > 0:
                    def _timeout_kill():
                        timed_out[0] = True
                        _kill_process_safe(process)
                    timer = Timer(float(timeout), _timeout_kill)
                    timer.daemon = True
                    timer.start()
            except Exception:
                timer = None
            try:
                stdout, stderr = process.communicate()
            finally:
                try:
                    if timer is not None:
                        timer.cancel()
                except Exception:
                    pass
            if timed_out[0]:
                return 255, _decode_bytes(stdout), 'Timeout'
        return process.returncode, _decode_bytes(stdout), _decode_bytes(stderr)
    except Exception as e:
        try:
            if process is not None:
                _kill_process_safe(process)
        except Exception:
            pass
        return 255, '', ensure_unicode(e)

def _safe_shell_arg(value):
    # POSIX-safe quoting, zgodne z Python 2 i Python 3.
    txt = ensure_unicode(value)
    return "'" + txt.replace("'", "'\"'\"'") + "'"

def _parse_opkg_installed_map(raw_text):
    installed = {}
    for raw_line in ensure_unicode(raw_text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(" - ", 1)
        pkg = parts[0].strip()
        ver = parts[1].strip() if len(parts) > 1 else ""
        if pkg:
            installed[pkg] = ver
    return installed

def _parse_opkg_upgradable_list(raw_text):
    updates = []
    for raw_line in ensure_unicode(raw_text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(" - ")]
        if len(parts) >= 3:
            pkg = parts[0]
            current_ver = parts[1]
            new_ver = parts[2]
        elif len(parts) == 2:
            pkg = parts[0]
            current_ver = ""
            new_ver = parts[1]
        else:
            continue
        if not pkg.startswith("enigma2-plugin-"):
            continue
        updates.append({
            "type": "opkg",
            "package": pkg,
            "name": pkg,
            "current_version": current_ver,
            "remote_version": new_ver
        })
    updates.sort(key=lambda item: ensure_unicode(item.get("name", item.get("package", ""))).lower())
    return updates

def _opkg_compare_versions(v1, operator, v2):
    if not _command_exists("opkg"):
        return None
    try:
        cmd = "opkg compare-versions {v1} {op} {v2}".format(
            v1=_safe_shell_arg(v1),
            op=operator,
            v2=_safe_shell_arg(v2)
        )
        return subprocess.call(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0
    except Exception:
        return None

def _is_remote_version_newer(local_ver, remote_ver):
    local_txt = ensure_unicode(local_ver).strip()
    remote_txt = ensure_unicode(remote_ver).strip()
    if not local_txt or not remote_txt:
        return False
    cmp_result = _opkg_compare_versions(local_txt, "<", remote_txt)
    if cmp_result is not None:
        return bool(cmp_result)
    return _version_to_tuple(remote_txt) > _version_to_tuple(local_txt)

def _fetch_text_url(url, timeout=20, tries=2):
    if not url:
        return ""
    prepare_tmp_dir()
    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", ensure_unicode(url))[:80] or "remote"
    tmp_path = os.path.join(PLUGIN_TMP_PATH, "fetch_{0}.txt".format(safe_name))
    if _download_url_to_file(url, tmp_path, timeout=timeout, tries=tries, allow_insecure_fallback=True):
        return _read_text_file(tmp_path, "")
    return ""

def _fetch_json_url(url, timeout=20, tries=2):
    if not url:
        return None
    prepare_tmp_dir()
    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", ensure_unicode(url))[:80] or "remote_json"
    tmp_path = os.path.join(PLUGIN_TMP_PATH, "fetch_{0}.json".format(safe_name))
    if _download_url_to_file(url, tmp_path, timeout=timeout, tries=tries, allow_insecure_fallback=True):
        return _load_json_from_file(tmp_path)
    return None

def _resolve_final_url(url, timeout=20, tries=2):
    if not url or not _is_https_allowed(url):
        return ""
    last_error = None
    for _idx in range(max(1, int(tries))):
        try:
            request = Request(url, headers={'User-Agent': 'Enigma2'})
            response = urlopen(request, timeout=timeout)
            try:
                final_url = ensure_unicode(getattr(response, 'geturl', lambda: url)())
            finally:
                try:
                    response.close()
                except Exception:
                    pass
            if final_url:
                return final_url
        except Exception as exc:
            last_error = exc
        tool_cmds = []
        if _command_exists('curl'):
            tool_cmds.append(['curl', '-L', '--ipv4', '-A', 'Enigma2', '--max-time', str(timeout), '-o', '/dev/null', '-w', '%{url_effective}', url])
        for cmd in tool_cmds:
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                if process.returncode == 0:
                    final_url = _decode_bytes(stdout).strip()
                    if final_url:
                        return final_url
                last_error = stderr
            except Exception as exc:
                last_error = exc
    if last_error:
        print('[AIO Panel] final URL resolve error for {}: {}'.format(url, last_error))
    return ""

def _extract_remote_version(value, version_regex=""):
    text = ensure_unicode(value).strip()
    if not text:
        return ""
    if version_regex:
        try:
            match = re.search(version_regex, text)
            if match:
                return ensure_unicode(match.group(1)).strip()
        except Exception:
            pass
    if text.startswith("v") and len(text) > 1 and re.search(r"\d", text[1:]):
        return text[1:]
    return text

def _load_custom_updates_manifest_entries():
    """Load the bundled trust-anchor manifest only.

    Remote metadata may describe versions/assets later, but it can never replace
    executable policy or inject shell commands.
    """
    manifest = _load_json_from_file(CUSTOM_UPDATES_MANIFEST_LOCAL)
    entries = []
    if isinstance(manifest, list):
        entries = manifest
    elif isinstance(manifest, dict):
        for key in ('entries', 'items', 'plugins', 'data'):
            value = manifest.get(key)
            if isinstance(value, list):
                entries = value
                break
    safe = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        clean = dict(entry)
        clean.pop('install_cmd', None)
        safe.append(clean)
    return safe

def _entry_local_package_name(entry):
    package = ensure_unicode(entry.get("package", "")).strip()
    if package:
        return package
    packages = entry.get("packages")
    if isinstance(packages, list):
        for item in packages:
            item_txt = ensure_unicode(item).strip()
            if item_txt:
                return item_txt
    return ""

def _entry_candidate_packages(entry):
    packages = []
    exact = ensure_unicode(entry.get("package", "")).strip()
    if exact:
        packages.append(exact)

    extra = entry.get("packages")
    if isinstance(extra, list):
        for item in extra:
            item_txt = ensure_unicode(item).strip()
            if item_txt and item_txt not in packages:
                packages.append(item_txt)

    guessed = []
    name_seed = ensure_unicode(entry.get("package_hint") or entry.get("slug") or entry.get("repo") or entry.get("name") or "").lower()
    if "/" in name_seed:
        name_seed = name_seed.split("/")[-1]
    name_seed = re.sub(r"[^a-z0-9]+", "", name_seed)
    if name_seed:
        guessed.extend([
            "enigma2-plugin-extensions-" + name_seed,
            "enigma2-plugin-systemplugins-" + name_seed,
            name_seed,
        ])
    for item in guessed:
        if item and item not in packages:
            packages.append(item)
    return packages

def _find_installed_package_for_entry(entry, installed_map):
    candidates = _entry_candidate_packages(entry)

    # Exact package names first.
    for pkg in candidates:
        if pkg in installed_map:
            return pkg

    # Optional explicit regex for packages that changed naming scheme.
    regex_value = ensure_unicode(entry.get("installed_match_regex") or entry.get("package_regex") or "").strip()
    if regex_value:
        try:
            matcher = re.compile(regex_value, re.I)
            for pkg in sorted(installed_map.keys()):
                if matcher.search(pkg):
                    return pkg
        except Exception:
            pass

    # Conservative fuzzy fallback: match the normalized trailing token.
    normalized = []
    for item in candidates:
        token = item.lower().split("/")[-1]
        token = token.replace("enigma2-plugin-extensions-", "").replace("enigma2-plugin-systemplugins-", "")
        token = re.sub(r"[^a-z0-9]+", "", token)
        if token and token not in normalized:
            normalized.append(token)
    for pkg in sorted(installed_map.keys()):
        pkg_norm = re.sub(r"[^a-z0-9]+", "", ensure_unicode(pkg).lower())
        for token in normalized:
            if token and token in pkg_norm:
                return pkg
    return ""

def _resolve_latest_url_by_shell(url, timeout=20):
    if not url or not _is_https_allowed(url):
        return ''
    probes = []
    if _command_exists('wget'):
        probes.append("wget -S --max-redirect=0 -U Enigma2 -T {t} -O /dev/null {u} 2>&1".format(t=max(5, int(timeout)), u=_safe_shell_arg(url)))
    if _command_exists('curl'):
        probes.append("curl -fI -L --ipv4 -A Enigma2 --max-time {t} {u} 2>/dev/null".format(t=max(5, int(timeout)), u=_safe_shell_arg(url)))
    for cmd in probes:
        rc, out, err = _run_shell_capture(cmd)
        blob = ensure_unicode(out or err)
        for line in blob.splitlines():
            match = re.search(r'Location:\s*(https://\S+)', line, re.I)
            if match and _is_https_allowed(match.group(1)):
                return ensure_unicode(match.group(1)).strip()
    return ''

def _entry_display_name(entry, lang="PL"):
    lang = "PL" if lang == "PL" else "EN"
    if lang == "PL":
        return ensure_unicode(entry.get("name_pl") or entry.get("name") or entry.get("title") or "").strip()
    return ensure_unicode(entry.get("name_en") or entry.get("name") or entry.get("title") or "").strip()

def _resolve_custom_remote_data(entry):
    source = ensure_unicode(entry.get('source', 'github_release')).strip() or 'github_release'
    version_regex = ensure_unicode(entry.get('version_regex', '')).strip()
    remote_version = ''
    download_url = ensure_unicode(entry.get('download_url', '')).strip()
    expected_sha256 = ensure_unicode(entry.get('sha256', '')).strip().lower()
    package_regex = ensure_unicode(entry.get('expected_package_regex') or entry.get('package_regex') or '').strip()

    if source == 'github_release':
        repo = ensure_unicode(entry.get('repo', '')).strip()
        api_url = ensure_unicode(entry.get('api_url', '')).strip() or ('https://api.github.com/repos/{}/releases/latest'.format(repo) if repo else '')
        latest_url = ensure_unicode(entry.get('latest_url', '')).strip() or ('https://github.com/{}/releases/latest'.format(repo) if repo else '')
        payload = _fetch_json_url(api_url, timeout=20, tries=2) if _is_https_allowed(api_url) else None
        if isinstance(payload, dict):
            remote_version = _extract_remote_version(payload.get('tag_name') or payload.get('name') or '', version_regex)
            asset_name = ensure_unicode(entry.get('asset_name', '')).strip()
            for asset in payload.get('assets', []) if isinstance(payload.get('assets', []), list) else []:
                if not isinstance(asset, dict):
                    continue
                candidate = ensure_unicode(asset.get('browser_download_url', '')).strip()
                current_name = ensure_unicode(asset.get('name', '')).strip()
                if candidate and _is_https_allowed(candidate) and ((not asset_name) or current_name == asset_name):
                    download_url = candidate
                    break
        if not remote_version and latest_url and _is_https_allowed(latest_url):
            final_url = _resolve_final_url(latest_url, timeout=20, tries=2) or _resolve_latest_url_by_shell(latest_url, timeout=20)
            match = re.search(r'/releases/tag/v?([^/?#]+)', ensure_unicode(final_url), re.I)
            if match:
                remote_version = _extract_remote_version(match.group(1), version_regex)
    elif source == 'github_latest_redirect':
        latest_url = ensure_unicode(entry.get('latest_url', '')).strip()
        if _is_https_allowed(latest_url):
            final_url = _resolve_final_url(latest_url, timeout=20, tries=2) or _resolve_latest_url_by_shell(latest_url, timeout=20)
            match = re.search(r'/releases/tag/v?([^/?#]+)', ensure_unicode(final_url), re.I)
            if match:
                remote_version = _extract_remote_version(match.group(1), version_regex)
    elif source == 'version_text':
        version_url = ensure_unicode(entry.get('version_url', '')).strip()
        if _is_https_allowed(version_url):
            remote_version = _extract_remote_version(_fetch_text_url(version_url, timeout=20, tries=2), version_regex)
    elif source == 'static':
        remote_version = _extract_remote_version(entry.get('remote_version', ''), version_regex)

    if download_url and not _is_https_allowed(download_url):
        download_url = ''
    return {
        'remote_version': remote_version,
        'download_url': download_url,
        'expected_sha256': expected_sha256,
        'expected_package_regex': package_regex
    }

def _collect_custom_manifest_updates(installed_map, lang='PL'):
    results = []
    for entry in _load_custom_updates_manifest_entries():
        try:
            if not isinstance(entry, dict):
                continue
            package = _find_installed_package_for_entry(entry, installed_map)
            if not package:
                continue
            local_version = ensure_unicode(installed_map.get(package, '')).strip()
            remote_data = _resolve_custom_remote_data(entry)
            remote_version = ensure_unicode(remote_data.get('remote_version', '')).strip()
            download_url = ensure_unicode(remote_data.get('download_url', '')).strip()
            package_regex = ensure_unicode(remote_data.get('expected_package_regex', '')).strip()
            if not remote_version or not download_url or not package_regex:
                continue
            try:
                re.compile(package_regex)
            except Exception:
                continue
            if not _is_remote_version_newer(local_version, remote_version):
                continue
            results.append({
                'type': 'custom',
                'package': package,
                'name': _entry_display_name(entry, lang) or package,
                'current_version': local_version,
                'remote_version': remote_version,
                'download_url': download_url,
                'expected_sha256': ensure_unicode(remote_data.get('expected_sha256', '')).strip(),
                'expected_package_regex': package_regex
            })
        except Exception as e:
            print('[AIO Panel] Custom update entry skipped:', e)
    results.sort(key=lambda item: ensure_unicode(item.get('name', item.get('package', ''))).lower())
    return results

def _collect_plugin_updates_snapshot(lang="PL"):
    update_rc, _, update_err = _run_shell_capture("opkg update")
    if update_rc != 0:
        print("[AIO Panel] opkg update returned {}".format(update_rc))
        if update_err:
            print("[AIO Panel] opkg update stderr: {}".format(update_err))
    _, installed_raw, _ = _run_shell_capture("opkg list-installed")
    _, upgradable_raw, _ = _run_shell_capture("opkg list-upgradable")
    installed_map = _parse_opkg_installed_map(installed_raw)
    return {
        "opkg": _parse_opkg_upgradable_list(upgradable_raw),
        "custom": _collect_custom_manifest_updates(installed_map, lang)
    }

def _pick_tip_index(total):
    try:
        return datetime.date.today().toordinal() % max(total, 1)
    except Exception:
        return 0

def _load_external_aio_tips(lang="PL"):
    data = _read_text_file(AIO_TIPS_FILE, "")
    if not data.strip():
        return []
    sections = {"PL": [], "EN": []}
    plain = []
    current = None
    for raw_line in data.splitlines():
        line = ensure_unicode(raw_line).strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith(";"):
            continue
        upper = line.upper()
        if upper in ("[PL]", "[EN]"):
            current = upper[1:-1]
            continue
        if current in sections:
            sections[current].append(line)
        else:
            plain.append(line)
    if plain:
        return plain
    lang_key = "PL" if lang == "PL" else "EN"
    if sections.get(lang_key):
        return sections.get(lang_key)
    if sections.get("PL"):
        return sections.get("PL")
    if sections.get("EN"):
        return sections.get("EN")
    return []

def _get_aio_tips(lang="PL"):
    external_tips = _load_external_aio_tips(lang)
    if external_tips:
        return external_tips
    tips_pl = [
        "Użyj AIO Quick Start, gdy chcesz pokazać najciekawsze funkcje bez przekopywania całego menu.",
        "Po większej instalacji uruchom Tryb Naprawy po Instalacji – często wystarczy do przywrócenia uprawnień i usług.",
        "Gdy flash zaczyna się zapełniać, najpierw uruchom Smart Cleanup zamiast ręcznie kasować pliki systemowe.",
        "Auto RAM Cleaner ustaw tylko na boxach z małą ilością RAM – na mocniejszych tunerach zwykle wystarcza tryb ręczny.",
        "Jeżeli feedy przestaną działać, sprawdź najpierw Menedżer Feedów / Repozytoriów i test połączenia, zanim zrobisz reinstall obrazu.",
        "Przed podmianą list kanałów zrób szybki backup – przywrócenie trwa chwilę i oszczędza nerwów.",
        "Zakładka Informacje o Systemie to dobry pierwszy krok przy diagnozie: od razu widać uptime, RAM i aktywne IP.",
        "Lokalny changelog działa także bez internetu – przydatne, gdy GitHub chwilowo nie odpowiada na starszych obrazach.",
        "Po większej aktualizacji AIO Panel wykonaj restart ręcznie dopiero wtedy, gdy system działa stabilnie.",
        "W wersji 12.0 możesz nadal edytować Tip dnia w pliku aio_tips.txt bez ingerencji w plugin.py – wystarczy dopisać nowe linie w sekcji [PL]."
    ]
    tips_en = [
        "Use AIO Quick Start when you want to showcase the most useful features without browsing the full menu.",
        "After a bigger install, run Post-Install Repair first – permissions and service fixes often solve the issue immediately.",
        "When flash space gets tight, start with Smart Cleanup before deleting system files manually.",
        "Use Auto RAM Cleaner mainly on low-memory boxes – manual mode is often enough on stronger receivers.",
        "If feeds stop working, check Feed / Repository Manager and connectivity first before reinstalling the image.",
        "Create a quick backup before replacing channel lists – restore takes only a moment and avoids frustration.",
        "System Information is a good first stop for troubleshooting: uptime, RAM and active IPs are visible immediately.",
        "The local changelog works even without internet access, which helps on older images when GitHub is unreachable.",
        "After a larger AIO Panel update, reboot manually only after checking that the system is stable.",
        "In version 12.0 you can still edit the daily tip in aio_tips.txt without touching plugin.py – just add new lines under [EN]."
    ]
    return tips_pl if lang == "PL" else tips_en

def _build_compat_report(lang, image_type="unknown"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    title = "Raport zgodności AIO Panel" if lang == "PL" else "AIO Panel compatibility report"
    lines.append("{} v{}".format(title, VER))
    lines.append("Data: {}".format(now) if lang == "PL" else "Date: {}".format(now))
    lines.append("")
    lines.append(("Środowisko:" if lang == "PL" else "Environment:"))
    lines.append("- Python: {}".format(get_python_version() or "N/A"))
    lines.append("- Tryb: {}".format("Py3" if IS_PY3 else "Py2"))
    lines.append("- Obraz/typ: {}".format(image_type or "unknown") if lang == "PL" else "- Image/type: {}".format(image_type or "unknown"))
    lines.append("- Enigma2 plugin path: {}".format(PLUGIN_PATH))
    lines.append("")

    checks = [
        ("opkg", _command_exists("opkg")),
        ("wget", _command_exists("wget")),
        ("tar", _command_exists("tar")),
        ("unzip", _command_exists("unzip")),
        ("bash", _command_exists("bash")),
        ("crontab", _command_exists("crontab")),
        ("systemctl", _command_exists("systemctl")),
    ]
    lines.append(("Kluczowe narzędzia:" if lang == "PL" else "Core tools:"))
    for name, ok in checks:
        lines.append("- [{}] {}".format("OK" if ok else "WARN", name))

    ca_paths = [
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/ssl/certs/ca-bundle.crt",
        "/etc/ssl/cert.pem"
    ]
    has_ca = any(os.path.exists(p) for p in ca_paths)
    lines.append("- [{}] {}".format("OK" if has_ca else "WARN", "CA certificates"))

    temp_paths = [
        "/proc/stb/sensors/temp0/value",
        "/proc/stb/fp/temp_sensor",
        "/sys/class/thermal/thermal_zone0/temp"
    ]
    has_temp = any(os.path.exists(p) for p in temp_paths)
    lines.append("- [{}] {}".format("OK" if has_temp else "WARN", "czujnik temperatury" if lang == "PL" else "temperature sensor"))

    lines.append("")
    lines.append(("Pamięć i system plików:" if lang == "PL" else "Storage and filesystem:"))
    try:
        root_du = shutil_disk_usage("/")
        lines.append("- / free: {:.1f} MB".format(root_du.free / (1024.0 * 1024.0)))
    except Exception:
        lines.append("- / free: N/A")
    lines.append("- /tmp writable: {}".format("YES" if os.access("/tmp", os.W_OK) else "NO"))
    lines.append("- /etc/enigma2 present: {}".format("YES" if os.path.isdir("/etc/enigma2") else "NO"))

    lines.append("")
    lines.append(("Sugestie:" if lang == "PL" else "Suggestions:"))
    suggestions = []
    if not _command_exists("wget"):
        suggestions.append("- Zainstaluj wget – część instalatorów online nie zadziała." if lang == "PL" else "- Install wget – several online installers depend on it.")
    if not _command_exists("unzip"):
        suggestions.append("- Doinstaluj unzip dla archiwów ZIP z listami/piconami." if lang == "PL" else "- Install unzip for ZIP-based lists and picons.")
    if not has_ca:
        suggestions.append("- Brak certyfikatów CA może utrudniać połączenia HTTPS z GitHub." if lang == "PL" else "- Missing CA certificates may break HTTPS access to GitHub.")
    if not suggestions:
        suggestions.append("- System wygląda poprawnie i jest gotowy do pracy z AIO Panel." if lang == "PL" else "- The system looks healthy and ready for AIO Panel tasks.")
    lines.extend(suggestions)
    return "\n".join(lines)

def _download_s4_archive_shell_command(url, output_path, expected_type):
    """Download a data-only S4a archive, then validate it before extraction."""
    if not _s4a_archive_url_allowed(url):
        return "echo '[AIO Panel] ERROR: invalid S4a archive URL'; exit 64"
    validator = os.path.join(PLUGIN_PATH, 'core', 'archive_validator.py')
    return r'''
set -eu
URL=%s
OUT=%s
EXPECTED=%s
VALIDATOR=%s
rm -f "$OUT" "$OUT.tmp"
OK=0
if command -v wget >/dev/null 2>&1; then
    wget -4 -T 180 -t 3 -O "$OUT.tmp" "$URL" && OK=1 || true
    if [ "$OK" -eq 0 ]; then wget -T 180 -t 3 -O "$OUT.tmp" "$URL" && OK=1 || true; fi
fi
if [ "$OK" -eq 0 ] && command -v curl >/dev/null 2>&1; then
    curl -fL --ipv4 --connect-timeout 25 --max-time 240 --retry 3 -o "$OUT.tmp" "$URL" && OK=1 || true
fi
if [ "$OK" -eq 0 ]; then
    PY=""
    command -v python3 >/dev/null 2>&1 && PY=python3
    [ -n "$PY" ] || { command -v python >/dev/null 2>&1 && PY=python; }
    [ -n "$PY" ] || { echo '[AIO Panel] ERROR: no downloader available'; exit 65; }
    AIO_URL="$URL" AIO_OUT="$OUT.tmp" "$PY" - <<'PY'
from __future__ import print_function
import os, sys
try:
    try:
        from urllib.request import Request, urlopen
    except ImportError:
        from urllib2 import Request, urlopen
    req = Request(os.environ['AIO_URL'], headers={'User-Agent': 'Enigma2/AIO-Panel-14'})
    response = urlopen(req, timeout=240)
    handle = open(os.environ['AIO_OUT'], 'wb')
    try:
        while True:
            chunk = response.read(65536)
            if not chunk:
                break
            handle.write(chunk)
    finally:
        handle.close()
        try:
            response.close()
        except Exception:
            pass
    if os.path.getsize(os.environ['AIO_OUT']) <= 0:
        raise ValueError('empty download')
except Exception as exc:
    print(exc, file=sys.stderr)
    sys.exit(1)
PY
    OK=1
fi
[ "$OK" -eq 1 ] && [ -s "$OUT.tmp" ] || { rm -f "$OUT.tmp"; echo '[AIO Panel] ERROR: S4a archive download failed'; exit 66; }
HEAD=$(dd if="$OUT.tmp" bs=1024 count=1 2>/dev/null | tr 'A-Z' 'a-z')
case "$HEAD" in *'<html'*|*'<!doctype'*|*'404: not found'*|*'access denied'*) rm -f "$OUT.tmp"; echo '[AIO Panel] ERROR: server returned HTML'; exit 67 ;; esac
mv -f "$OUT.tmp" "$OUT"
PYBIN=""
command -v python3 >/dev/null 2>&1 && PYBIN=python3
[ -n "$PYBIN" ] || { command -v python >/dev/null 2>&1 && PYBIN=python; }
[ -n "$PYBIN" ] || { echo '[AIO Panel] ERROR: Python unavailable for archive validation'; exit 68; }
"$PYBIN" "$VALIDATOR" "$OUT" "$EXPECTED" 100000 2147483648
''' % (_safe_shell_arg(url), _safe_shell_arg(output_path), _safe_shell_arg(expected_type), _safe_shell_arg(validator))


# === FUNKCJA install_archive (GLOBALNA) ===
def install_archive(session, title, url, callback_on_finish=None, picon_path=None, action_type=None):
    """Install a channel list, picon archive or IPK with verified completion."""
    requested_type = ensure_unicode(action_type or '').strip().lower()
    allow_s4a_data = requested_type == 'channels_s4a' and _s4a_archive_url_allowed(url)
    clean_url = ensure_unicode(url).split('?', 1)[0].split('#', 1)[0]
    lower_url = clean_url.lower()
    if not _is_https_allowed(url) and not allow_s4a_data:
        result = {'success': False, 'returncode': 64, 'stderr': 'Blocked non-HTTPS or untrusted URL', 'type': requested_type or 'archive'}
        show_message_compat(session, 'Zablokowano niezabezpieczony lub niezaufany adres pobierania.', MessageBox.TYPE_ERROR)
        _invoke_safe_callback(callback_on_finish, result, noarg_only_on_success=True)
        return
    if lower_url.endswith('.zip'):
        archive_type, archive_ext = 'zip', 'zip'
    elif lower_url.endswith(('.tar.gz', '.tgz')):
        archive_type, archive_ext = 'tar.gz', 'tar.gz'
    elif lower_url.endswith('.ipk') and not allow_s4a_data:
        archive_type, archive_ext = 'ipk', 'ipk'
    else:
        result = {'success': False, 'returncode': 65, 'stderr': 'Unsupported archive format'}
        show_message_compat(session, 'Nieobsługiwany format archiwum!', MessageBox.TYPE_ERROR)
        _invoke_safe_callback(callback_on_finish, result, noarg_only_on_success=True)
        return

    prepare_tmp_dir()
    unique_id = '%s_%s' % (os.getpid(), int(time.time() * 1000))
    status_path = os.path.join(PLUGIN_TMP_PATH, 'install_%s.status' % unique_id)
    is_picon = requested_type == 'picons' or (not requested_type and 'picon' in ensure_unicode(title).lower())

    if is_picon:
        target = ensure_unicode(picon_path or '/usr/share/enigma2/picon').strip() or '/usr/share/enigma2/picon'
        script_path = os.path.join(PLUGIN_PATH, 'picon_install_script.sh')
        if not os.path.isfile(script_path):
            result = {'success': False, 'returncode': 66, 'stderr': 'Missing picon installer'}
            show_message_compat(session, 'BŁĄD: Brak pliku picon_install_script.sh!', MessageBox.TYPE_ERROR)
            _invoke_safe_callback(callback_on_finish, result, noarg_only_on_success=True)
            return
        command = '/bin/sh {script} {url} {target} {status}'.format(script=_safe_shell_arg(script_path), url=_safe_shell_arg(url), target=_safe_shell_arg(target), status=_safe_shell_arg(status_path))

        def finished(command_result):
            status_value = _read_text_file(status_path, '').strip()
            try:
                os.remove(status_path)
            except Exception:
                pass
            success = bool(command_result and command_result.get('success')) and (status_value.startswith('OK|') or status_value == 'OK')
            result = dict(command_result or {})
            result.update({'success': success, 'status': status_value, 'type': 'picons', 'target': target})
            if success:
                parts = status_value.split('|', 2)
                result['count'] = parts[1] if len(parts) > 1 else '?'
                if callback_on_finish:
                    _invoke_safe_callback(callback_on_finish, result, noarg_only_on_success=True)
                else:
                    show_message_compat(session, 'Picony zostały zainstalowane.\n\nPliki: %s\nKatalog: %s' % (result['count'], target), timeout=7)
            else:
                status_parts = status_value.split('|', 2)
                detail = status_parts[1] if status_value.startswith('ERROR|') and len(status_parts) > 1 else ensure_unicode(result.get('stderr') or 'Instalator nie potwierdził skopiowania piconów.')
                show_message_compat(session, 'Nie udało się zainstalować piconów.\n\n%s\n\nLog: /tmp/aio_picons_install.log' % detail, MessageBox.TYPE_ERROR, timeout=15)
                _invoke_safe_callback(callback_on_finish, result, noarg_only_on_success=True)
        run_command_in_background(session, title, [command], callback_on_finish=finished)
        return

    if archive_type == 'ipk':
        safe_script = os.path.join(PLUGIN_PATH, 'safe_ipk_install.sh')
        expected = '^enigma2-plugin-(extensions|systemplugins)-[A-Za-z0-9.+_-]+$'
        command = '/bin/sh {script} {url} {expected} {status}'.format(script=_safe_shell_arg(safe_script), url=_safe_shell_arg(url), expected=_safe_shell_arg(expected), status=_safe_shell_arg(status_path))

        def ipk_finished(command_result):
            status_value = _read_text_file(status_path, '').strip()
            try:
                os.remove(status_path)
            except Exception:
                pass
            result = dict(command_result or {})
            result.update({'success': bool(command_result and command_result.get('success')) and status_value.startswith('OK'), 'status': status_value, 'type': 'ipk'})
            if not result['success']:
                show_message_compat(session, 'Instalacja pakietu IPK nie powiodła się.\n\n%s' % (status_value or result.get('stderr', '')), MessageBox.TYPE_ERROR, timeout=14)
            _invoke_safe_callback(callback_on_finish, result, noarg_only_on_success=True)
        run_command_in_background(session, title, [command], callback_on_finish=ipk_finished)
        return

    archive_path = os.path.join(PLUGIN_TMP_PATH, 'aio_download_%s.%s' % (unique_id, archive_ext))
    script_path = os.path.join(PLUGIN_PATH, 'install_archive_script.sh')
    if not os.path.isfile(script_path):
        result = {'success': False, 'returncode': 66, 'stderr': 'Missing channel list installer'}
        show_message_compat(session, 'BŁĄD: Brak pliku install_archive_script.sh!', MessageBox.TYPE_ERROR)
        _invoke_safe_callback(callback_on_finish, result, noarg_only_on_success=True)
        return
    if allow_s4a_data:
        download = _download_s4_archive_shell_command(url, archive_path, archive_type)
    else:
        download = _download_shell_command(url, archive_path, archive_type)
    command = 'set -eu\n(\n%s\n)\n/bin/sh %s %s %s %s\n' % (download, _safe_shell_arg(script_path), _safe_shell_arg(archive_path), _safe_shell_arg(archive_type), _safe_shell_arg(status_path))

    def channel_finished(command_result):
        status_value = _read_text_file(status_path, '').strip()
        try:
            os.remove(status_path)
        except Exception:
            pass
        result = dict(command_result or {})
        result.update({'success': bool(command_result and command_result.get('success')) and (status_value.startswith('OK|') or status_value == 'OK'), 'status': status_value, 'type': 'channels'})
        if result['success']:
            if callback_on_finish:
                _invoke_safe_callback(callback_on_finish, result, noarg_only_on_success=True)
            else:
                show_message_compat(session, 'Lista kanałów została bezpiecznie zainstalowana.', timeout=6)
        else:
            status_parts = status_value.split('|', 2)
            detail = status_parts[1] if status_value.startswith('ERROR|') and len(status_parts) > 1 else ensure_unicode(result.get('stderr') or 'Brak potwierdzenia poprawnej instalacji.')
            show_message_compat(session, 'Nie udało się zainstalować listy kanałów.\n\n%s\n\nPoprzednia lista została zachowana lub przywrócona. Log: /tmp/aio_install.log' % detail, MessageBox.TYPE_ERROR, timeout=16)
            _invoke_safe_callback(callback_on_finish, result, noarg_only_on_success=True)
    run_command_in_background(session, title, [command], callback_on_finish=channel_finished)


def get_python_version():
    try:
        ver = sys.version_info
        return "{}.{}".format(ver[0], ver[1])
    except Exception:
        return None

def get_e2kodi_package_name():
    # Funkcja tylko dla Pythona 3 - na Py2 Kodi jest rzadkością/inną wersją
    if IS_PY2:
        return None
        
    py_ver = get_python_version()
    if py_ver == "3.9":
        return "enigma2-plugin-extensions--j00zeks-e2kodi-v2-python3.9"
    elif py_ver == "3.12":
        return "enigma2-plugin-extensions--j00zeks-e2kodi-v2-python3.12"
    elif py_ver == "3.13":
        return "enigma2-plugin-extensions--j00zeks-e2kodi-v2-python3.13"
    else:
        return None

def install_e2kodi(session):
    if IS_PY2:
        show_message_compat(session, "E2Kodi (j00zek) wymaga Pythona 3. Twoja wersja to Python 2.", MessageBox.TYPE_ERROR)
        return
        
    pkg = get_e2kodi_package_name()
    if not pkg:
        show_message_compat(session, "Nieznana wersja Pythona. E2Kodi nie zostało zainstalowane.", MessageBox.TYPE_ERROR)
        return

    repo_file = "/etc/opkg/opkg-j00zka.conf"
    repo_url = "https://j00zek.github.io/eeRepo" 
    if not os.path.exists(repo_file):
        try:
            with open(repo_file, "w") as f:
                f.write("src/gz opkg-j00zka {}\n".format(repo_url))
        except Exception as e:
            show_message_compat(session, "Błąd zapisu repozytorium: {}".format(e), MessageBox.TYPE_ERROR)
            return

    cmd = "opkg update && opkg install {}".format(pkg)
    run_command_in_background(session, "E2Kodi v2 (Python {})".format(get_python_version()), [cmd])

# === MENU PL/EN Z E2Kodi (GLOBALNE) ===
SOFTCAM_AND_PLUGINS_PL = [
    (r"\c00FFD200--- Softcamy ---\c00ffffff", "SEPARATOR"),
    ("🔄 Restart Oscam", "CMD:RESTART_OSCAM"),
    ("🧹 Kasuj hasło Oscam", "CMD:CLEAR_OSCAM_PASS"),
    ("⚙️ oscam.dvbapi - kasowanie zawartości", "CMD:MANAGE_DVBAPI"),
    ("⚙️ oscam.dvbapi - aktualizacja Poland", "CMD:UPDATE_DVBAPI_POLAND"),
    ("🔄 Aktualizuj oscam.srvid/srvid2", "CMD:UPDATE_SRVID"),
    ("🔑 Aktualizuj SoftCam.Key (Online)", "CMD:INSTALL_SOFTCAMKEY_ONLINE"),
    ("📥 Softcam - Instalator", "CMD:INSTALL_SOFTCAM_SCRIPT"),
    ("📥 OSCam-Emu - Instalator i aktywacja", "CMD:INSTALL_BEST_OSCAM"),
    ("📥 Oscam Levi45", "CMD:INSTALL_LEVI45_OSCAM"),
    ("📥 NCam (Feed - najnowszy)", "CMD:INSTALL_NCAM_FEED"),
    (r"\c00FFD200--- Wtyczki Online ---\c00ffffff", "SEPARATOR"),
    ("📺 XStreamity - Instalator", "opkg:enigma2-plugin-extensions-xstreamity"),
    ("📺 IPTV Dream - Instalator", "CMD:INSTALL_IPTV_DREAM"),
    ("🩺 E2 Doctor - Instalator (Python 3)", "remote_script:https://raw.githubusercontent.com/OliOli2013/E2-Doctor-Plugin/main/installer.sh"),
    ("⚙️ ServiceApp - Instalator", "CMD:INSTALL_SERVICEAPP"),
    ("📦 Konfiguracja IPTV - zależności", "CMD:IPTV_DEPS"),
    ("⚙️ StreamlinkProxy - Instalator", "opkg:enigma2-plugin-extensions-streamlinkproxy"),
    ("🛠 AJPanel - Instalator", "remote_script:https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh"),
    ("▶️ E2iPlayer Master - Instalacja/Aktualizacja", "remote_script:https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh"),
    ("📅 EPG Import - Instalator", "remote_script_bash:https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh"),
    ("📺 Simple IPTV EPG - Instalator", "remote_script:https://raw.githubusercontent.com/OliOli2013/SimpleIPTV_EPG/main/installer.sh"),
    ("📡 PP Channel Sync - Instalator", "remote_script:https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main/installer.sh"),
    ("📻 NeoRadio Online - Instalator", "safe_ipk:https://github.com/OliOli2013/NeoRadio/releases/latest/download/enigma2-plugin-extensions-neoradio_all.ipk|^(enigma2-plugin-extensions-neoradio(?:online|-online)?|neoradio)$"),
    ("📺 Bouquet Maker Xtream - Instalator", "CMD:INSTALL_BMX_SAFE"),
    ("🔄 MyUpdater v5.1 - Instalator", "remote_script:https://raw.githubusercontent.com/OliOli2013/MyUpdater-Plugin/main/installer.sh"),
    ("📺 JediMakerXtream - Instalator", "remote_script:https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh"),
    ("▶️ YouTube - Instalator", "safe_ipk:https://github.com/Taapat/enigma2-plugin-youtube/releases/download/git1294/enigma2-plugin-extensions-youtube_py3-git1294-cbcf8b0-r0.0.ipk|^enigma2-plugin-extensions-youtube(?:_[A-Za-z0-9.+-]+)?$"),
    ("📦 J00zeks Feed (Repo Installer)", "CMD:INSTALL_J00ZEK_REPO"),
    ("📺 E2Kodi v2 - Instalator (j00zek)", "CMD:INSTALL_E2KODI"),
    ("🖼️ Picon Updater - Instalator (Picony)", "remote_script:https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh"),
    ("🖼️ ChocholousekPicons - Instalator", "remote_script_bash:https://github.com/s3n0/e2plugins/raw/master/ChocholousekPicons/online-setup|install"),
    ("🔑 CIEFP Oscam Editor - Instalator", "remote_script:https://raw.githubusercontent.com/ciefp/CiefpOscamEditor/main/installer.sh"),
    ("📺 e-stralker - Instalator (feed)", "CMD:INSTALL_ESTALKER_SAFE"),
        ("▶️ VAVOO - Instalator", "remote_script:https://raw.githubusercontent.com/Belfagor2005/vavoo/main/installer.sh"),
    ("📺 TV Garden - Instalator", "remote_script:https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/installer.sh"),
    ("🔎 Simple ZOOM Panel - Instalator", "remote_script:https://raw.githubusercontent.com/Belfagor2005/SimpleZooomPanel/main/installer.sh"),
    ("⚽ FootOnsat - Instalator", "remote_script:https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh"),
]


SOFTCAM_AND_PLUGINS_EN = [
    (r"\c00FFD200--- Softcams ---\c00ffffff", "SEPARATOR"),
    ("🔄 Restart Oscam", "CMD:RESTART_OSCAM"),
    ("🧹 Clear Oscam Password", "CMD:CLEAR_OSCAM_PASS"),
    ("⚙️ oscam.dvbapi - clear file", "CMD:MANAGE_DVBAPI"),
    ("⚙️ oscam.dvbapi - Poland update", "CMD:UPDATE_DVBAPI_POLAND"),
    ("🔄 Update oscam.srvid/srvid2", "CMD:UPDATE_SRVID"),
    ("🔑 Update SoftCam.Key (Online)", "CMD:INSTALL_SOFTCAMKEY_ONLINE"),
    ("📥 Softcam - Installer", "CMD:INSTALL_SOFTCAM_SCRIPT"),
    ("📥 OSCam-Emu - Install and activate", "CMD:INSTALL_BEST_OSCAM"),
    ("📥 Oscam Levi45", "CMD:INSTALL_LEVI45_OSCAM"),
    ("📥 NCam (Feed - latest)", "CMD:INSTALL_NCAM_FEED"),
    (r"\c00FFD200--- Online Plugins ---\c00ffffff", "SEPARATOR"),
    ("📺 XStreamity - Installer", "opkg:enigma2-plugin-extensions-xstreamity"),
    ("📺 IPTV Dream - Installer", "CMD:INSTALL_IPTV_DREAM"),
    ("🩺 E2 Doctor - Installer (Python 3)", "remote_script:https://raw.githubusercontent.com/OliOli2013/E2-Doctor-Plugin/main/installer.sh"),
    ("⚙️ ServiceApp - Installer", "CMD:INSTALL_SERVICEAPP"),
    ("📦 IPTV Configuration - dependencies", "CMD:IPTV_DEPS"),
    ("⚙️ StreamlinkProxy - Installer", "opkg:enigma2-plugin-extensions-streamlinkproxy"),
    ("🛠 AJPanel - Installer", "remote_script:https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh"),
    ("▶️ E2iPlayer Master - Install/Update", "remote_script:https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh"),
    ("📅 EPG Import - Installer", "remote_script_bash:https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh"),
    ("📺 Simple IPTV EPG - Installer", "remote_script:https://raw.githubusercontent.com/OliOli2013/SimpleIPTV_EPG/main/installer.sh"),
    ("📡 PP Channel Sync - Installer", "remote_script:https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main/installer.sh"),
    ("📻 NeoRadio Online - Installer", "safe_ipk:https://github.com/OliOli2013/NeoRadio/releases/latest/download/enigma2-plugin-extensions-neoradio_all.ipk|^(enigma2-plugin-extensions-neoradio(?:online|-online)?|neoradio)$"),
    ("📺 Bouquet Maker Xtream - Installer", "CMD:INSTALL_BMX_SAFE"),
    ("🔄 MyUpdater v5.1 - Installer", "remote_script:https://raw.githubusercontent.com/OliOli2013/MyUpdater-Plugin/main/installer.sh"),
    ("📺 JediMakerXtream - Installer", "remote_script:https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh"),
    ("▶️ YouTube - Installer", "safe_ipk:https://github.com/Taapat/enigma2-plugin-youtube/releases/download/git1294/enigma2-plugin-extensions-youtube_py3-git1294-cbcf8b0-r0.0.ipk|^enigma2-plugin-extensions-youtube(?:_[A-Za-z0-9.+-]+)?$"),
    ("📦 J00zeks Feed (Repo Installer)", "CMD:INSTALL_J00ZEK_REPO"),
    ("📺 E2Kodi v2 - Installer (j00zek)", "CMD:INSTALL_E2KODI"),
    ("🖼️ Picon Updater - Installer (Picons)", "remote_script:https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh"),
    ("🖼️ ChocholousekPicons - Installer", "remote_script_bash:https://github.com/s3n0/e2plugins/raw/master/ChocholousekPicons/online-setup|install"),
    ("🔑 CIEFP Oscam Editor - Installer", "remote_script:https://raw.githubusercontent.com/ciefp/CiefpOscamEditor/main/installer.sh"),
    ("📺 e-stralker - Installer (feed)", "CMD:INSTALL_ESTALKER_SAFE"),
        ("▶️ VAVOO - Installer", "remote_script:https://raw.githubusercontent.com/Belfagor2005/vavoo/main/installer.sh"),
    ("📺 TV Garden - Installer", "remote_script:https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/installer.sh"),
    ("🔎 Simple ZOOM Panel - Installer", "remote_script:https://raw.githubusercontent.com/Belfagor2005/SimpleZooomPanel/main/installer.sh"),
    ("⚽ FootOnsat - Installer", "remote_script:https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh"),
]


# === NOWE PODZIELONE LISTY MENU (PL) ===
SYSTEM_TOOLS_PL = [
    (r"\c00FFD200--- Konfigurator ---\c00ffffff", "SEPARATOR"),
    ("✨ Super Konfigurator (Pierwsza Instalacja)", "CMD:SUPER_SETUP_WIZARD"),
    ("👁️ Widoczność w menu tunera (ON/OFF)", "CMD:TOGGLE_MENU_VISIBILITY"),
    (r"\c00FFD200--- Narzędzia Systemowe ---\c00ffffff", "SEPARATOR"),
    ("🗑️ Menadżer Deinstalacji", "CMD:UNINSTALL_MANAGER"),
    ("🔎 Sprawdź aktualizacje zainstalowanych wtyczek", "CMD:PLUGIN_UPDATE_MANAGER"),
    ("📡 Aktualizuj satellites.xml", "CMD:UPDATE_SATELLITES_XML"),
    ("🖼️ Pobierz Picony (Transparent)", "picons:https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip"),
    ("📊 Monitor Systemowy", "CMD:SYSTEM_MONITOR"),
    ("📄 Przeglądarka Logów", "CMD:LOG_VIEWER"),
    ("⏰ Menedżer Cron", "CMD:CRON_MANAGER"),
    ("🔌 Menedżer Usług", "CMD:SERVICE_MANAGER"),
    ("ℹ️ Informacje o Systemie", "CMD:SYSTEM_INFO"),
    (r"\c00FFD200--- Feedy / Repozytoria ---\c00ffffff", "SEPARATOR"),
    ("🌐 Menedżer Feedów / Repozytoriów", "CMD:FEED_MANAGER"),
    (r"\c00FFD200--- Naprawa i Backup ---\c00ffffff", "SEPARATOR"),
    ("🛠 Tryb Naprawy po Instalacji", "CMD:POSTINSTALL_REPAIR"),
    ("💾 Backup Listy Kanałów", "CMD:BACKUP_LIST"),
    ("💾 Backup Konfiguracji Oscam", "CMD:BACKUP_OSCAM"),
    ("♻️ Restore Listy Kanałów", "CMD:RESTORE_LIST"),
    ("♻️ Restore Konfiguracji Oscam", "CMD:RESTORE_OSCAM"),
]


SYSTEM_TOOLS_EN = [
    (r"\c00FFD200--- Configurator ---\c00ffffff", "SEPARATOR"),
    ("✨ Super Setup Wizard (First Installation)", "CMD:SUPER_SETUP_WIZARD"),
    ("👁️ Show in receiver menu (ON/OFF)", "CMD:TOGGLE_MENU_VISIBILITY"),
    (r"\c00FFD200--- System Tools ---\c00ffffff", "SEPARATOR"),
    ("🗑️ Uninstallation Manager", "CMD:UNINSTALL_MANAGER"),
    ("🔎 Check updates for installed plugins", "CMD:PLUGIN_UPDATE_MANAGER"),
    ("📡 Update satellites.xml", "CMD:UPDATE_SATELLITES_XML"),
    ("🖼️ Download Picons (Transparent)", "picons:https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip"),
    ("📊 System Monitor", "CMD:SYSTEM_MONITOR"),
    ("📄 Log Viewer", "CMD:LOG_VIEWER"),
    ("⏰ Cron Manager", "CMD:CRON_MANAGER"),
    ("🔌 Service Manager", "CMD:SERVICE_MANAGER"),
    ("ℹ️ System Information", "CMD:SYSTEM_INFO"),
    (r"\c00FFD200--- Feeds / Repositories ---\c00ffffff", "SEPARATOR"),
    ("🌐 Feed / Repository Manager", "CMD:FEED_MANAGER"),
    (r"\c00FFD200--- Repair & Backup ---\c00ffffff", "SEPARATOR"),
    ("🛠 Post-Install Repair Mode", "CMD:POSTINSTALL_REPAIR"),
    ("💾 Backup Channel List", "CMD:BACKUP_LIST"),
    ("💾 Backup Oscam Config", "CMD:BACKUP_OSCAM"),
    ("♻️ Restore Channel List", "CMD:RESTORE_LIST"),
    ("♻️ Restore Oscam Config", "CMD:RESTORE_OSCAM"),
]


DIAGNOSTICS_PL = [
    (r"\c00FFD200--- Informacje i Aktualizacje ---\c00ffffff", "SEPARATOR"),
    ("ℹ️ Informacje o AIO Panel", "CMD:SHOW_AIO_INFO"),
    ("🔄 Aktualizacja Wtyczki", "CMD:CHECK_FOR_UPDATES"),
    (r"\c00FFD200--- AIO Extra ---\c00ffffff", "SEPARATOR"),
    ("⭐ AIO Szybki Start / Polecane", "CMD:AIO_QUICKSTART"),
    ("🧪 Test zgodności systemu", "CMD:COMPATIBILITY_CHECK"),
    ("💡 Tip dnia AIO", "CMD:SHOW_AIO_TIP"),
    ("📜 Lokalny changelog", "CMD:LOCAL_CHANGELOG"),
    (r"\c00FFD200--- Diagnostyka ---\c00ffffff", "SEPARATOR"),
    ("🌐 Diagnostyka Sieci", "CMD:NETWORK_DIAGNOSTICS"),
    ("💾 Wolne miejsce (dysk/flash)", "CMD:FREE_SPACE_DISPLAY"),
    (r"\c00FFD200--- Czyszczenie i Bezpieczeństwo ---\c00ffffff", "SEPARATOR"),
    ("⏱️ Auto RAM Cleaner (Konfiguruj)", "CMD:SETUP_AUTO_RAM"),
    ("🧹 Wyczyść Pamięć Tymczasową", "CMD:CLEAR_TMP_CACHE"),
    ("🧹 Smart Cleanup (TMP/LOG/CACHE)", "CMD:SMART_CLEANUP"),
    ("🧹 Wyczyść Pamięć RAM", "CMD:CLEAR_RAM_CACHE"),
    ("🔑 Kasuj hasło FTP", "CMD:CLEAR_FTP_PASS"),
    ("🔑 Ustaw Hasło FTP", "CMD:SET_SYSTEM_PASSWORD"),
]


DIAGNOSTICS_EN = [
    (r"\c00FFD200--- Info & Updates ---\c00ffffff", "SEPARATOR"),
    ("ℹ️ About AIO Panel", "CMD:SHOW_AIO_INFO"),
    ("🔄 Update Plugin", "CMD:CHECK_FOR_UPDATES"),
    (r"\c00FFD200--- AIO Extras ---\c00ffffff", "SEPARATOR"),
    ("⭐ AIO Quick Start / Recommended", "CMD:AIO_QUICKSTART"),
    ("🧪 System compatibility check", "CMD:COMPATIBILITY_CHECK"),
    ("💡 AIO tip of the day", "CMD:SHOW_AIO_TIP"),
    ("📜 Local changelog", "CMD:LOCAL_CHANGELOG"),
    (r"\c00FFD200--- Diagnostics ---\c00ffffff", "SEPARATOR"),
    ("🌐 Network Diagnostics", "CMD:NETWORK_DIAGNOSTICS"),
    ("💾 Free Space (disk/flash)", "CMD:FREE_SPACE_DISPLAY"),
    (r"\c00FFD200--- Cleaning & Security ---\c00ffffff", "SEPARATOR"),
    ("⏱️ Auto RAM Cleaner (Setup)", "CMD:SETUP_AUTO_RAM"),
    ("🧹 Clear Temporary Cache", "CMD:CLEAR_TMP_CACHE"),
    ("🧹 Smart Cleanup (TMP/LOG/CACHE)", "CMD:SMART_CLEANUP"),
    ("🧹 Clear RAM Cache", "CMD:CLEAR_RAM_CACHE"),
    ("🔑 Clear FTP Password", "CMD:CLEAR_FTP_PASS"),
    ("🔑 Set FTP Password", "CMD:SET_SYSTEM_PASSWORD"),
]


# === SKINS / SKÓRKI ===
SKINS_PL = [
    ("🎨 Algare FHD - Instalator", "remote_script:https://raw.githubusercontent.com/popking159/skins/refs/heads/main/aglarepli/installer.sh"),
    ("🎨 Fury FHD - Instalator", "remote_script:https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh"),
    ("🎨 Luka FHD - Instalator", "remote_script:https://raw.githubusercontent.com/popking159/skins/refs/heads/main/lukapli/installer.sh"),
    ("🎨 Maxy FHD - Instalator", "remote_script:https://raw.githubusercontent.com/popking159/skins/refs/heads/main/maxyatv/installer.sh"),
    ("🎨 XDreamy - Instalator", "remote_script:https://raw.githubusercontent.com/Insprion80/Skins/main/xDreamy/installer.sh"),
]

SKINS_EN = [
    ("🎨 Algare FHD - Installer", "remote_script:https://raw.githubusercontent.com/popking159/skins/refs/heads/main/aglarepli/installer.sh"),
    ("🎨 Fury FHD - Installer", "remote_script:https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh"),
    ("🎨 Luka FHD - Installer", "remote_script:https://raw.githubusercontent.com/popking159/skins/refs/heads/main/lukapli/installer.sh"),
    ("🎨 Maxy FHD - Installer", "remote_script:https://raw.githubusercontent.com/popking159/skins/refs/heads/main/maxyatv/installer.sh"),
    ("🎨 XDreamy - Installer", "remote_script:https://raw.githubusercontent.com/Insprion80/Skins/main/xDreamy/installer.sh"),
]


# === NOWE 4 KATEGORIE ===
COL_TITLES = {
    "PL": ("📺 Listy Kanałów", "🔑 Softcam i Wtyczki", "⚙️ Narzędzia Systemowe", "ℹ️ Info i Diagnostyka"),
    "EN": ("📺 Channel Lists", "🔑 Softcam & Plugins", "⚙️ System Tools", "ℹ️ Info & Diagnostics")
}



# === SORTOWANIE I FILTROWANIE LIST KANAŁÓW v14.0.0 ===
# Repozytorium AIO pozostaje źródłem podstawowym. S4aUpdater uzupełnia je
# wszystkimi listami z ostatnich 12 miesięcy. Listy Bzyk83 są wykluczone ze
# wszystkich źródeł. Vhannibal pozostaje na końcu listy zgodnie z układem AIO.
CHANNEL_LIST_EXCLUDED_CREATORS = (
    u"bzyk83", u"bzyk 83", u"bzyk_83", u"bzyk-83"
)


def _normalize_channel_sort_text(value):
    txt = ensure_unicode(value).lower()
    replacements = (
        (u"ą", u"a"), (u"ć", u"c"), (u"ę", u"e"), (u"ł", u"l"),
        (u"ń", u"n"), (u"ó", u"o"), (u"ś", u"s"), (u"ż", u"z"), (u"ź", u"z"),
        (u"Ą", u"a"), (u"Ć", u"c"), (u"Ę", u"e"), (u"Ł", u"l"),
        (u"Ń", u"n"), (u"Ó", u"o"), (u"Ś", u"s"), (u"Ż", u"z"), (u"Ź", u"z")
    )
    for src, dst in replacements:
        txt = txt.replace(src, dst)
    txt = re.sub(u"[^a-z0-9]+", u" ", txt)
    return re.sub(u"\\s+", u" ", txt).strip()


def _channel_item_matches_creator(name, action, creator_names):
    txt = _normalize_channel_sort_text(u"%s %s" % (ensure_unicode(name), ensure_unicode(action)))
    compact = txt.replace(u" ", u"")
    padded = u" %s " % txt
    for creator in creator_names:
        normalized = _normalize_channel_sort_text(creator)
        if not normalized:
            continue
        if (u" %s " % normalized) in padded:
            return True
        if normalized.replace(u" ", u"") in compact:
            return True
    return False


def _is_excluded_channel_list_item(name, action=""):
    return _channel_item_matches_creator(name, action, CHANNEL_LIST_EXCLUDED_CREATORS)


def _is_vhannibal_channel_list_item(name, action=""):
    return _channel_item_matches_creator(name, action, (u"vhannibal", u"vhanibal"))


def _make_date_key(year, month=0, day=0):
    try:
        y = int(year)
        m = int(month)
        d = int(day)
        if y < 1900 or y > 2100:
            return 0
        if m == 0 and d == 0:
            return y * 10000
        datetime.date(y, m, d)
        return y * 10000 + m * 100 + d
    except Exception:
        return 0


def _extract_channel_date_key(name, action=""):
    text = ensure_unicode(name) + u" " + ensure_unicode(action)
    text = text.replace(u"_", u"-")
    keys = []
    # YYYY-MM-DD / YYYY.MM.DD / YYYY MM DD
    for match in re.finditer(r"(?<!\d)((?:19|20)\d{2})[-./ ]+([01]?\d)[-./ ]+([0-3]?\d)(?!\d)", text):
        key = _make_date_key(match.group(1), match.group(2), match.group(3))
        if key:
            keys.append(key)
    # DD-MM-YYYY / DD.MM.YYYY
    for match in re.finditer(r"(?<!\d)([0-3]?\d)[-./ ]+([01]?\d)[-./ ]+((?:19|20)\d{2})(?!\d)", text):
        key = _make_date_key(match.group(3), match.group(2), match.group(1))
        if key:
            keys.append(key)
    # DD-MM-YY / DD.MM.YY used by some S4a list descriptions.
    for match in re.finditer(r"(?<!\d)([0-3]?\d)[-./ ]+([01]?\d)[-./ ]+(\d{2})(?!\d)", text):
        year = int(match.group(3))
        year += 2000 if year < 70 else 1900
        key = _make_date_key(year, match.group(2), match.group(1))
        if key:
            keys.append(key)
    if keys:
        return max(keys)
    # A year-only marker is useful for sorting repo entries but is not precise
    # enough to establish the rolling 12-month S4a cutoff.
    for match in re.finditer(r"(?<!\d)((?:19|20)\d{2})(?!\d)", text):
        key = _make_date_key(match.group(1), 0, 0)
        if key:
            keys.append(key)
    return max(keys) if keys else 0


def _date_key_to_date(date_key):
    try:
        value = int(date_key)
        year = value // 10000
        month = (value // 100) % 100
        day = value % 100
        if month == 0 or day == 0:
            return None
        return datetime.date(year, month, day)
    except Exception:
        return None


def _rolling_year_threshold(today=None):
    today = today or datetime.date.today()
    try:
        return today.replace(year=today.year - 1)
    except ValueError:
        # 29 February -> 28 February in the previous year.
        return today.replace(year=today.year - 1, day=28)


def _channel_item_is_recent(item, source="repo", today=None):
    try:
        name, action = item[0], item[1]
    except Exception:
        return False
    if action == "SEPARATOR":
        return True
    today = today or datetime.date.today()
    date_key = _extract_channel_date_key(name, action)
    date_value = _date_key_to_date(date_key)
    if date_value is None:
        # Controlled repo entries without a date (e.g. M3U/BOUQUET tools) stay
        # available. For S4a, a current-year marker is accepted; older/undated
        # entries cannot prove that they satisfy the rolling 12-month rule.
        try:
            year_only = int(date_key) // 10000
        except Exception:
            year_only = 0
        return source == "repo" or (source == "s4a" and year_only == today.year)
    return date_value >= _rolling_year_threshold(today)


def _dedupe_channel_lists(items):
    result = []
    seen_urls = set()
    seen_names = set()
    for item in items or []:
        try:
            name, action = item[0], item[1]
        except Exception:
            continue
        if action == "SEPARATOR":
            result.append(item)
            continue
        normalized_action = ensure_unicode(action).strip()
        url_key = ""
        if ":" in normalized_action:
            prefix, payload = normalized_action.split(":", 1)
            if prefix in ("archive", "s4archive", "picons"):
                url_key = payload.split("?", 1)[0].split("#", 1)[0].lower()
        norm_name = _normalize_channel_sort_text(name)
        norm_name = re.sub(u"\\b(?:19|20)\\d{2}(?:[ -]?[01]?\\d[ -]?[0-3]?\\d)?\\b", u" ", norm_name)
        norm_name = re.sub(u"\\b(?:brak daty|dodaj bukiet m3u|dodaj bukiet ref|s4aupdater|s4a|repo)\\b", u" ", norm_name)
        norm_name = re.sub(u"\\s+", u" ", norm_name).strip()
        if url_key and url_key in seen_urls:
            continue
        if norm_name and norm_name in seen_names:
            continue
        if url_key:
            seen_urls.add(url_key)
        if norm_name:
            seen_names.add(norm_name)
        result.append(item)
    return result


def _sort_channel_lists_v12(items):
    regular = []
    separators = []
    vhannibal = []
    for index, item in enumerate(items or []):
        try:
            name, action = item[0], item[1]
        except Exception:
            continue
        if action == "SEPARATOR":
            separators.append((index, item))
            continue
        row = (-_extract_channel_date_key(name, action), index, item)
        if _is_vhannibal_channel_list_item(name, action):
            vhannibal.append(row)
        else:
            regular.append(row)
    regular.sort(key=lambda row: (row[0], row[1]))
    vhannibal.sort(key=lambda row: (row[0], row[1]))
    ordered = [row[2] for row in regular]
    ordered.extend([row[1] for row in separators])
    ordered.extend([row[2] for row in vhannibal])
    return ordered


def _prepare_channel_lists_v1201(repo_lists, s4a_lists_full):
    repo_filtered = []
    for item in (repo_lists or []):
        try:
            name, action = item[0], item[1]
        except Exception:
            continue
        if _is_excluded_channel_list_item(name, action):
            continue
        if _channel_item_is_recent(item, source="repo"):
            repo_filtered.append(item)

    s4a_filtered = []
    for item in (s4a_lists_full or []):
        try:
            name, action = item[0], item[1]
        except Exception:
            continue
        if _is_excluded_channel_list_item(name, action):
            continue
        if _channel_item_is_recent(item, source="s4a"):
            s4a_filtered.append(item)

    # Repo is first, so an identical list from S4a does not replace the
    # maintained AIO copy. Every other current S4a creator remains visible.
    return _sort_channel_lists_v12(_dedupe_channel_lists(repo_filtered + s4a_filtered))


# === FUNKCJE ŁADOWANIA DANYCH (GLOBALNE) ===

def _get_lists_from_repo_sync():
    manifest_url = "https://raw.githubusercontent.com/OliOli2013/PanelAIO-Lists/main/manifest.json"
    tmp_json_path = os.path.join(PLUGIN_TMP_PATH, 'manifest.json')
    cache_json_path = os.path.join(PLUGIN_TMP_PATH, 'manifest_cache.json')
    prepare_tmp_dir()

    payload = None
    if _download_url_to_file(manifest_url, tmp_json_path, timeout=20, tries=3, allow_insecure_fallback=True):
        payload = _load_json_from_file(tmp_json_path)
        normalized = _normalize_repo_manifest(payload)
        if normalized:
            payload = normalized
            try:
                shutil.copyfile(tmp_json_path, cache_json_path)
            except Exception:
                pass
        else:
            payload = None

    if payload is None:
        payload = _normalize_repo_manifest(_load_json_from_file(cache_json_path))
        if payload:
            print('[AIO Panel] Using cached channel-list manifest.')

    if not payload:
        print('[AIO Panel] Repo data error: manifest unavailable or invalid.')
        return []

    lists_menu = []
    for item in payload:
        try:
            if not isinstance(item, dict):
                continue
            item_type = ensure_unicode(item.get('type', 'LIST')).upper()
            name = ensure_unicode(item.get('name', 'Brak nazwy')).strip() or 'Brak nazwy'
            author = ensure_unicode(item.get('author', '')).strip()
            url = ensure_unicode(item.get('url', '')).strip()
            if not url:
                continue
            if item_type == 'M3U':
                bouquet_id = ensure_unicode(item.get('bouquet_id', 'userbouquet.imported_m3u.tv')).strip() or 'userbouquet.imported_m3u.tv'
                menu_title = '📺 {} - {} (Dodaj Bukiet M3U)'.format(name, author)
                action = 'm3u_json:' + _encode_action_payload('m3u', url, bouquet_id, name)
                lists_menu.append((menu_title, action))
            elif item_type == 'BOUQUET':
                bouquet_id = ensure_unicode(item.get('bouquet_id', 'userbouquet.imported_ref.tv')).strip() or 'userbouquet.imported_ref.tv'
                menu_title = '📺 {} - {} (Dodaj Bukiet REF)'.format(name, author)
                action = 'bouquet_json:' + _encode_action_payload('bouquet', url, bouquet_id, name)
                lists_menu.append((menu_title, action))
            else:
                version = ensure_unicode(item.get('version', '')).strip() or 'brak daty'
                menu_title = '📡 {} - {} ({})'.format(name, author, version)
                action = 'archive:{}'.format(url)
                lists_menu.append((menu_title, action))
        except Exception as e:
            print('[AIO Panel] Pominięto uszkodzony wpis manifestu: {}'.format(e))
    if not lists_menu:
        print('[AIO Panel] Brak list w repozytorium po filtrowaniu manifestu.')
        return []
    return lists_menu

def _s4a_metadata_url_allowed(url):
    try:
        parsed = urlparse(ensure_unicode(url).strip())
        return parsed.scheme in ('http', 'https') and (parsed.hostname or '').lower() == 's4aupdater.one.pl' and parsed.path == '/s4aupdater_list.txt' and not parsed.username and not parsed.password
    except Exception:
        return False


def _s4a_host_is_public_name(host):
    host = ensure_unicode(host).strip().lower().rstrip('.')
    if not host or host in ('localhost', 'localhost.localdomain'):
        return False
    if host.endswith(('.local', '.lan', '.home', '.internal')):
        return False
    # Raw IPv6 and local/private IPv4 destinations are not accepted from an
    # unauthenticated catalog. Normal public DNS names remain supported.
    if ':' in host:
        return False
    if re.match(r'^\d{1,3}(?:\.\d{1,3}){3}$', host):
        try:
            parts = [int(value) for value in host.split('.')]
            if any(value < 0 or value > 255 for value in parts):
                return False
            if parts[0] in (0, 10, 127) or parts[0] >= 224:
                return False
            if parts[0] == 169 and parts[1] == 254:
                return False
            if parts[0] == 172 and 16 <= parts[1] <= 31:
                return False
            if parts[0] == 192 and parts[1] == 168:
                return False
        except Exception:
            return False
    return True


def _s4a_archive_url_allowed(url):
    try:
        parsed = urlparse(ensure_unicode(url).strip())
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            return False
        if parsed.username or parsed.password or not _s4a_host_is_public_name(parsed.hostname):
            return False
        path = ensure_unicode(parsed.path or '').lower()
        return path.endswith('.zip') or path.endswith('.tar.gz') or path.endswith('.tgz')
    except Exception:
        return False


def _download_s4a_metadata(url, destination, timeout=25):
    """Download only the fixed S4a text catalog; never execute its content."""
    if not _s4a_metadata_url_allowed(url):
        return False
    tmp_path = destination + '.tmp'
    try:
        request = Request(url, headers={'User-Agent': 'Enigma2/AIO-Panel-14'})
        response = urlopen(request, timeout=timeout)
        try:
            final_url = ensure_unicode(response.geturl() if hasattr(response, 'geturl') else url)
            if not _s4a_metadata_url_allowed(final_url):
                return False
            payload = response.read((2 * 1024 * 1024) + 1)
        finally:
            try:
                response.close()
            except Exception:
                pass
        if not payload or len(payload) > 2 * 1024 * 1024 or _payload_looks_like_html_error(payload):
            return False
        with open(tmp_path, 'wb') as handle:
            handle.write(payload)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except Exception:
                pass
        os.rename(tmp_path, destination)
        return True
    except Exception as exc:
        print('[AIO Panel] S4a catalog download failed from {}: {}'.format(url, exc))
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return False


def _s4a_catalog_is_valid(path):
    try:
        if not os.path.isfile(path) or os.path.getsize(path) <= 0 or os.path.getsize(path) > 2 * 1024 * 1024:
            return False
        text = _read_text_file(path, '')
        if not text or '<html' in text[:512].lower():
            return False
        return '_url:' in text and '_version:' in text
    except Exception:
        return False


def _get_s4aupdater_lists_dynamic_sync():
    """Return all dated S4a channel lists; age/Bzyk filtering is applied later."""
    prepare_tmp_dir()
    tmp_list_file = os.path.join(PLUGIN_TMP_PATH, 's4aupdater_list.txt')
    cache_candidates = [
        '/etc/enigma2/.panelaio_s4aupdater_list.cache',
        os.path.join(PLUGIN_TMP_PATH, 's4aupdater_list.cache'),
        '/usr/lib/enigma2/python/Plugins/Extensions/S4aUpdater/s4aupdater_list.txt',
        '/usr/lib/enigma2/python/Plugins/SystemPlugins/S4aUpdater/s4aupdater_list.txt',
        '/etc/enigma2/s4aupdater_list.txt'
    ]
    downloaded = False
    # Prefer HTTPS when the provider supports it, then its legacy read-only
    # HTTP endpoint. Only plain text metadata is accepted from HTTP.
    for source_url in (
        'https://s4aupdater.one.pl/s4aupdater_list.txt',
        'http://s4aupdater.one.pl/s4aupdater_list.txt'
    ):
        if _download_s4a_metadata(source_url, tmp_list_file) and _s4a_catalog_is_valid(tmp_list_file):
            downloaded = True
            break

    source_path = tmp_list_file if downloaded else ''
    if downloaded:
        for cache_path in cache_candidates[:2]:
            try:
                parent = os.path.dirname(cache_path)
                if parent and not os.path.isdir(parent):
                    os.makedirs(parent)
                shutil.copyfile(tmp_list_file, cache_path + '.tmp')
                os.rename(cache_path + '.tmp', cache_path)
            except Exception:
                try:
                    os.remove(cache_path + '.tmp')
                except Exception:
                    pass
    else:
        for candidate in cache_candidates:
            if _s4a_catalog_is_valid(candidate):
                source_path = candidate
                print('[AIO Panel] Using cached/local S4aUpdater catalog: {}'.format(candidate))
                break

    if not source_path:
        print('[AIO Panel] S4aUpdater catalog unavailable and no valid cache was found.')
        return []

    urls_dict = {}
    versions_dict = {}
    try:
        with io.open(source_path, 'r', encoding='utf-8', errors='ignore') as handle:
            for raw_line in handle:
                clean_line = raw_line.strip()
                if not clean_line or clean_line.startswith('#'):
                    continue
                match = re.match(r'^([A-Za-z0-9_]+_(?:url|version))\s*:\s*(.*?)\s*$', clean_line, re.I)
                if not match:
                    continue
                key = ensure_unicode(match.group(1)).lower()
                value = ensure_unicode(match.group(2)).strip().strip('"').strip("'")
                if key.endswith('_url'):
                    urls_dict[key] = value
                elif key.endswith('_version'):
                    versions_dict[key] = value
    except Exception as exc:
        print('[AIO Panel] Błąd parsowania katalogu S4aUpdater: {}'.format(exc))
        return []

    lists = []
    for key in sorted(urls_dict.keys()):
        url_value = urls_dict.get(key, '')
        if not _s4a_archive_url_allowed(url_value):
            print('[AIO Panel] Pominięto nieprawidłowy adres archiwum S4a: {}'.format(url_value))
            continue
        base_name = key[:-4]
        display_name = base_name.replace('_', ' ').strip().title() or 'S4aUpdater'
        date_info = versions_dict.get(base_name + '_version', '').strip()
        title = '📡 {} - {}'.format(display_name, date_info or 'brak daty')
        action = 's4archive:{}'.format(url_value)
        if _is_excluded_channel_list_item(title, action):
            continue
        lists.append((title, action))
    print('[AIO Panel] S4aUpdater: wczytano {} wpisów przed filtrem daty.'.format(len(lists)))
    return lists


def _get_best_oscam_version_info_sync():
    try:
        cmd = "opkg list | grep 'oscam' | grep 'ipv4only' | grep -E -m 1 'master|emu|stable'"
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, _ = process.communicate()
        if process.returncode == 0 and stdout:
            line = stdout.decode('utf-8').strip() if hasattr(stdout, 'decode') else stdout.strip()
            parts = line.split(' - ')
            if len(parts) > 1:
                return parts[1].strip()
        return "Auto"
    except Exception:
        return "Error"


def _get_local_oscam_version_info_sync():
    """Return a short local Oscam version label, e.g. r11866, without slow network calls."""
    try:
        candidates = [
            "/usr/softcams/oscam", "/usr/softcams/oscam-emu", "/usr/bin/oscam",
            "/usr/bin/oscam-emu", "/usr/local/bin/oscam"
        ]
        for path in candidates:
            if not os.path.exists(path):
                continue
            cmd = "%s -V 2>&1 | head -n 8" % _safe_shell_arg(path)
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            out = stdout or stderr or b""
            if hasattr(out, 'decode'):
                out = out.decode('utf-8', 'ignore')
            m = re.search(r'(?:r|svn|build[^0-9]{0,8})([0-9]{4,6})', out, re.I)
            if m:
                return "r" + m.group(1)
            m = re.search(r'([0-9]{5})', out)
            if m:
                return "r" + m.group(1)
        return "Online"
    except Exception:
        return "Online"


def _oscam_detect_shell_functions(extra_keys=False):
    """POSIX shell helpers used by Oscam data functions."""
    return r"""
aio_oscam_config_dirs(){
    OUT="/tmp/aio_oscam_dirs_$$"
    : > "$OUT"
    ACTIVE=0
    for PID in $(pidof oscam 2>/dev/null); do
        [ -r "/proc/$PID/cmdline" ] || continue
        CMD=$(tr '\000' ' ' < "/proc/$PID/cmdline" 2>/dev/null)
        PREV=""
        for A in $CMD; do
            if [ "$PREV" = "-c" ]; then
                [ -n "$A" ] && echo "$A" >> "$OUT" && ACTIVE=1
                PREV=""
                continue
            fi
            case "$A" in
                -c) PREV="-c" ;;
                -c*) V="${A#-c}"; [ -n "$V" ] && echo "$V" >> "$OUT" && ACTIVE=1 ;;
            esac
        done
    done
    if [ "$ACTIVE" -eq 0 ]; then
        for D in /etc/tuxbox/config /etc/tuxbox/config/oscam /etc/tuxbox/config/oscam-emu /var/tuxbox/config/oscam /usr/keys /var/keys; do
            [ -f "$D/oscam.conf" ] && echo "$D" >> "$OUT"
        done
        find /etc/tuxbox/config -maxdepth 4 -type f -name oscam.conf -exec dirname {} \; >> "$OUT" 2>/dev/null || true
    fi
    sort -u "$OUT" 2>/dev/null | while IFS= read -r D; do
        [ -n "$D" ] && [ -d "$D" ] && echo "$D"
    done
    rm -f "$OUT" 2>/dev/null || true
}

aio_require_oscam_dirs(){
    DIRS=$(aio_oscam_config_dirs)
    if [ -z "$DIRS" ]; then
        echo "BŁĄD: Nie udało się jednoznacznie wykryć katalogu konfiguracji aktywnego OSCama."
        echo "AIO Panel przerwał operację, żeby nie uszkodzić konfiguracji."
        echo "Uruchom OSCam i sprawdź parametr -c w procesie: cat /proc/$(pidof oscam | awk '{print $1}')/cmdline | tr '\\0' ' '"
        exit 1
    fi
    echo "Wykryte katalogi konfiguracji OSCam:"
    echo "$DIRS" | while IFS= read -r D; do echo " - $D"; done
}

aio_soft_restart_oscam(){
    echo "Odświeżam Oscam/Softcam bez wymuszania restartu GUI..."
    killall -HUP oscam 2>/dev/null || true
    if [ -x /etc/init.d/softcam ]; then /etc/init.d/softcam restart 2>/dev/null || true; fi
    if command -v systemctl >/dev/null 2>&1; then
        systemctl restart softcam 2>/dev/null || systemctl restart oscam 2>/dev/null || true
    fi
}
"""

# === KLASA WizardProgressScreen (GLOBALNA) ===
class WizardProgressScreen(Screen):
    skin = _wizard_progress_skin()

    def __init__(self, session, steps, **kwargs):
        Screen.__init__(self, session)
        self.session = session
        self.lang = kwargs.get('lang', 'PL') if kwargs.get('lang', 'PL') in ('PL', 'EN') else 'PL'
        self.steps = list(steps or [])
        self.index = 0
        self.current_key = None
        self.running = False
        self.failed = False
        self.cancelled = False
        self.wizard_warnings = []
        self.wizard_channel_list_url = kwargs.get('channel_list_url', '')
        self.wizard_channel_list_name = kwargs.get('channel_list_name', 'Polska 13E AIO Panel')
        self.wizard_picon_url = kwargs.get('picon_url', '')
        self.wizard_picon_path = kwargs.get('picon_path', '/usr/share/enigma2/picon')
        self['message'] = Label(self._txt(
            'Przygotowanie bezpiecznej instalacji...\n\nCZERWONY: Anuluj',
            'Preparing safe installation...\n\nRED: Cancel'))
        self['actions'] = ActionMap(['OkCancelActions', 'ColorActions'], {
            'cancel': self.cancel_wizard, 'red': self.cancel_wizard,
            'green': self.retry_step, 'yellow': self.skip_step,
        }, -1)
        self.onShown.append(self.start_wizard)

    def _txt(self, pl, en):
        return pl if self.lang == 'PL' else en

    def start_wizard(self):
        if not self.running and not self.cancelled:
            self._run_current_step()

    def _step_title(self, task):
        return 'Super Konfigurator [{}/{}]: {}'.format(min(self.index + 1, len(self.steps)), len(self.steps), task)

    def _set_progress(self, pl, en):
        controls = self._txt('\n\nCZERWONY: Anuluj', '\n\nRED: Cancel')
        self['message'].setText(self._txt(pl, en) + controls)

    def _run_current_step(self):
        if self.cancelled or self.running:
            return
        if self.index >= len(self.steps):
            self._on_wizard_finish()
            return
        self.current_key = self.steps[self.index]
        self.failed = False
        self.running = True
        func = {
            'deps': self._wizard_step_deps,
            'channel_list': self._wizard_step_channel_list,
            'install_softcam': self._wizard_step_install_softcam,
            'install_oscam': self._wizard_step_install_oscam,
            'picons': self._wizard_step_picons,
            'reload_settings': self._wizard_step_reload_settings,
        }.get(self.current_key)
        if func is None:
            self._step_done({'success': False, 'stderr': 'Unknown wizard step'})
            return
        reactor.callLater(0.2, func)

    def _step_done(self, result):
        self.running = False
        success = bool(result and result.get('success'))
        if success:
            self.index += 1
            self.current_key = None
            reactor.callLater(0.25, self._run_current_step)
            return
        self.failed = True
        detail = ensure_unicode((result or {}).get('stderr') or (result or {}).get('status') or 'Nieznany błąd')
        self['message'].setText(self._txt(
            'Krok został zatrzymany.\n\n%s\n\nZIELONY: Ponów   ŻÓŁTY: Pomiń   CZERWONY/EXIT: Anuluj' % detail,
            'The step was stopped.\n\n%s\n\nGREEN: Retry   YELLOW: Skip   RED/EXIT: Cancel' % detail))

    def retry_step(self):
        if self.failed and not self.running:
            self.failed = False
            self._run_current_step()

    def skip_step(self):
        if not self.failed or self.running:
            return
        # Only the channel-list step is mandatory. OSCam availability depends on
        # the image, architecture and external feed, so it must not trap the user.
        if self.current_key in ('channel_list',):
            show_message_compat(self.session, self._txt('Tego krytycznego kroku nie można pominąć.', 'This critical step cannot be skipped.'), MessageBox.TYPE_ERROR)
            return
        self.failed = False
        self.index += 1
        self.current_key = None
        self._run_current_step()

    def cancel_wizard(self):
        if self.running:
            show_message_compat(self.session, self._txt('Poczekaj na zakończenie bieżącej operacji. Zostanie bezpiecznie zatrzymana po tym kroku.', 'Wait for the current operation to finish. It will stop safely after this step.'), MessageBox.TYPE_INFO, timeout=8)
        self.cancelled = True
        if not self.running:
            self.close()

    def _wizard_step_deps(self):
        self._set_progress('Instalacja wymaganych zależności systemowych...', 'Installing required system dependencies...')
        cmd = "opkg update && opkg install wget ca-certificates && (command -v tar >/dev/null 2>&1 || opkg install tar) && (command -v unzip >/dev/null 2>&1 || opkg install unzip)"
        run_command_in_background(self.session, self._step_title('Zależności'), [cmd], callback_on_finish=self._step_done)

    def _wizard_step_channel_list(self):
        self._set_progress("Instalacja listy kanałów '%s' z kopią i rollbackiem..." % self.wizard_channel_list_name, "Installing channel list '%s' with backup and rollback..." % self.wizard_channel_list_name)
        install_archive(self.session, self._step_title(self.wizard_channel_list_name), self.wizard_channel_list_url, callback_on_finish=self._step_done, action_type='channels')

    def _wizard_step_install_softcam(self):
        self._set_progress('Instalacja feedu Softcam z polecenia mynonpublic...', 'Installing the Softcam feed using the mynonpublic command...')
        status = os.path.join(PLUGIN_TMP_PATH, 'wizard_softcam_%s.status' % int(time.time() * 1000))
        cmd = '/bin/sh %s %s' % (_safe_shell_arg(os.path.join(PLUGIN_PATH, 'install_softcam_feed_safe.sh')), _safe_shell_arg(status))
        def finished(result):
            text = _read_text_file(status, '').strip()
            try: os.remove(status)
            except Exception: pass
            merged = dict(result or {})
            merged['status'] = text
            accepted = text.startswith('OK') or text.startswith('WARN')
            merged['success'] = accepted
            if text.startswith('WARN'):
                self.wizard_warnings.append(text)
            if not merged['success'] and not merged.get('stderr'):
                merged['stderr'] = text or 'Softcam feed installation failed'
            self._step_done(merged)
        run_command_in_background(self.session, self._step_title('Softcam'), [cmd], callback_on_finish=finished)

    def _activate_oscam_config(self):
        changed = False
        try:
            candidates = [
                ('softcam', 'actCam', 'oscam'),
                ('plugins', 'softcamsetup', None),
            ]
            if hasattr(config, 'softcam') and hasattr(config.softcam, 'actCam'):
                config.softcam.actCam.value = 'oscam'; config.softcam.actCam.save(); changed = True
            if hasattr(config.plugins, 'softcamsetup') and hasattr(config.plugins.softcamsetup, 'cam_name'):
                config.plugins.softcamsetup.cam_name.value = 'oscam'; config.plugins.softcamsetup.cam_name.save(); changed = True
            if changed and configfile is not None:
                configfile.save()
        except Exception as exc:
            print('[AIO Panel] OSCam config activation note:', exc)
        return True

    def _wizard_step_install_oscam(self):
        self._set_progress('Instalacja OSCam-Emu, uruchomienie i kontrola procesu...', 'Installing OSCam-Emu, starting it and checking the process...')
        status = os.path.join(PLUGIN_TMP_PATH, 'wizard_oscam_%s.status' % int(time.time() * 1000))
        script = os.path.join(PLUGIN_PATH, 'install_oscam_emu_script.sh')
        cmd = '/bin/sh %s %s' % (_safe_shell_arg(script), _safe_shell_arg(status))
        def finished(result):
            text = _read_text_file(status, '').strip()
            try: os.remove(status)
            except Exception: pass
            merged = dict(result or {})
            merged['status'] = text
            merged['success'] = bool(result and result.get('success')) and text.startswith('OK')
            if merged['success']:
                self._activate_oscam_config()
            elif not merged.get('stderr'):
                merged['stderr'] = text or 'OSCam-Emu did not start'
            self._step_done(merged)
        run_command_in_background(self.session, self._step_title('OSCam-Emu'), [cmd], callback_on_finish=finished)

    def _wizard_step_picons(self):
        self._set_progress('Instalacja piconów do:\n%s' % self.wizard_picon_path, 'Installing picons to:\n%s' % self.wizard_picon_path)
        install_archive(self.session, self._step_title('Picony'), self.wizard_picon_url, callback_on_finish=self._step_done, picon_path=self.wizard_picon_path, action_type='picons')

    def _wizard_step_reload_settings(self):
        try:
            eDVBDB.getInstance().reloadServicelist()
            eDVBDB.getInstance().reloadBouquets()
            self._step_done({'success': True})
        except Exception as exc:
            self._step_done({'success': False, 'stderr': ensure_unicode(exc)})

    def _on_wizard_finish(self):
        self.running = False
        warning_pl = ''
        warning_en = ''
        if self.wizard_warnings:
            warning_pl = '\n\nUwaga: zewnętrzny feed Softcam był niedostępny lub niepotwierdzony. Pozostałe zadania zostały wykonane; OSCam został obsłużony niezależnie albo pominięty przez użytkownika.'
            warning_en = '\n\nNote: the external Softcam feed was unavailable or unconfirmed. Other tasks were completed; OSCam was handled independently or skipped by the user.'
        self['message'].setText(self._txt(
            'Konfiguracja zakończona.\n\nAutomatyczny restart nie został wykonany. Sprawdź działanie tunera i uruchom GUI ręcznie tylko wtedy, gdy jest to potrzebne.' + warning_pl,
            'Configuration completed.\n\nNo automatic restart was performed. Check the receiver and restart the GUI manually only if needed.' + warning_en))
        reactor.callLater(8, self.close)

# === NOWA KLASA EKRANU ŁADOWANIA ===
class AIOLoadingScreen(Screen):
    skin = """
    <screen position="center,center" size="700,220" title="Panel AIO">
        <widget name="message" position="20,20" size="660,180" font="Regular;24" halign="center" valign="center" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self['message'] = Label('Ładowanie danych AIO Panel...\n\nLoading AIO Panel data...')
        self.fetched_data_cache = None
        self._panel_opened = False
        self._loading_timeout_call = None
        self._dependency_prompt_open = False
        self.flag_file = os.path.join(PLUGIN_PATH, '.deps_ok')
        self.onShown.append(self.start_loading_process)

    def _has_cmd(self, cmd):
        try:
            return shutil_which(cmd) is not None
        except Exception:
            return False

    def _deps_present(self):
        ca_paths = ['/etc/ssl/certs/ca-certificates.crt', '/etc/ssl/certs/ca-bundle.crt', '/etc/ssl/cert.pem', '/etc/ssl/certs/ca-certificates.pem']
        return all(self._has_cmd(x) for x in ('wget', 'tar', 'unzip')) and any(os.path.exists(x) for x in ca_paths)

    def start_loading_process(self):
        if self._deps_present():
            self.start_async_data_load()
            return
        self._dependency_prompt_open = True
        text = ('Brakuje części zależności (wget/tar/unzip/certyfikaty).\n\nZainstalować je teraz? Panel może zostać otwarty bez instalacji, ale funkcje sieciowe mogą nie działać.' )
        self.session.openWithCallback(self._dependency_answer, MessageBox, text, MessageBox.TYPE_YESNO)

    def _dependency_answer(self, answer):
        self._dependency_prompt_open = False
        if not answer:
            self.start_async_data_load()
            return
        self['message'].setText('Instalacja zależności...\n\nNie zamykaj tunera.')
        cmd = "opkg update && opkg install wget ca-certificates && (command -v tar >/dev/null 2>&1 || opkg install tar) && (command -v unzip >/dev/null 2>&1 || opkg install unzip)"
        def done(result):
            if result and result.get('success') and self._deps_present():
                try:
                    _atomic_write(self.flag_file, 'ok\n')
                except Exception:
                    pass
            else:
                show_message_compat(self.session, 'Nie udało się zainstalować wszystkich zależności. Panel zostanie otwarty w trybie ograniczonym.', MessageBox.TYPE_ERROR, timeout=10)
            self.start_async_data_load()
        run_command_in_background(self.session, 'Zależności AIO Panel', [cmd], callback_on_finish=done)

    def start_async_data_load(self):
        if self._loading_timeout_call is None:
            self._loading_timeout_call = reactor.callLater(30, self._loading_timeout_fallback)
        thread = Thread(target=self._background_data_loader)
        try: thread.setDaemon(True)
        except Exception: pass
        thread.start()

    def _background_data_loader(self):
        repo_lists, s4a_lists_full, best_oscam_version, local_oscam_version = [], [], 'N/A', 'Online'
        try: repo_lists = _get_lists_from_repo_sync()
        except Exception as exc: print('[AIO Panel] repo list load:', exc)
        try: s4a_lists_full = _get_s4aupdater_lists_dynamic_sync()
        except Exception as exc: print('[AIO Panel] S4a list load:', exc)
        try: best_oscam_version = _get_best_oscam_version_info_sync()
        except Exception as exc: print('[AIO Panel] OSCam version load:', exc)
        try: local_oscam_version = _get_local_oscam_version_info_sync()
        except Exception as exc: print('[AIO Panel] local OSCam version:', exc)
        self.fetched_data_cache = {'repo_lists': repo_lists, 's4a_lists_full': s4a_lists_full, 'best_oscam_version': best_oscam_version, 'local_oscam_version': local_oscam_version}
        reactor.callFromThread(self._on_data_loaded)

    def _open_panel_safe(self, fetched_data=None):
        if self._panel_opened:
            return
        self._panel_opened = True
        try:
            if self._loading_timeout_call is not None and self._loading_timeout_call.active(): self._loading_timeout_call.cancel()
        except Exception: pass
        data = fetched_data or self.fetched_data_cache or {'repo_lists': [], 's4a_lists_full': [], 'best_oscam_version': 'Auto', 'local_oscam_version': 'Online'}
        self.session.open(PanelAIO, data)
        self.close()

    def _loading_timeout_fallback(self):
        if not self._panel_opened:
            self._open_panel_safe()

    def _on_data_loaded(self):
        self._open_panel_safe(self.fetched_data_cache)



# --- Support / QR (INFO) ---
class AIOSupportScreen(Screen):
    skin = _support_screen_skin()

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self._huge = False
        self["title"] = Label("Wesprzyj rozwój wtyczki / Support the plugin")
        self["txt"] = Label("OK/ŻÓŁTY = Zoom   EXIT = Powrót")
        self["qr_big"] = Pixmap()
        self["qr_huge"] = Pixmap()
        self._apply_zoom()

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.toggle_zoom,
            "yellow": self.toggle_zoom,
            "cancel": self.close,
        }, -1)

    def _apply_zoom(self):
        try:
            if self._huge:
                self["qr_big"].hide()
                self["qr_huge"].show()
            else:
                self["qr_huge"].hide()
                self["qr_big"].show()
        except Exception:
            pass

    def toggle_zoom(self):
        self._huge = not self._huge
        self._apply_zoom()

# *** NOWA KLASA EKRANU INFO (z notą prawną) ***
class AIOInfoScreen(Screen):
    skin = _info_screen_skin()

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.setTitle("Informacje o AIO Panel")

        self["title"] = Label("AIO Panel v{}".format(VER))
        self["author"] = Label("Twórca: Paweł Pawełek | aio-iptv@wp.pl")
        self["facebook"] = Label("Facebook: Enigma 2 Oprogramowanie, dodatki")
        self["legal_title"] = Label("--- Nota Prawna i Licencyjna ---")
        
        legal_note_text = "Nota Licencyjna i Prawa Autorskie\n\n" \
                          "Prawa autorskie (C) 2024-2026, Paweł Pawełek (aio-iptv@wp.pl)\n" \
                          "Wszelkie prawa autorskie osobiste zastrzeżone.\n\n" \
                          "Ta wtyczka (AIO Panel) jest wolnym oprogramowaniem: możesz ją\n" \
                          "redystrybuować i/lub modyfikować na warunkach Powszechnej\n" \
                          "Licencji Publicznej GNU (GNU GPL), opublikowanej przez\n" \
                          "Free Software Foundation.\n\n" \
                          "Oprogramowanie to jest rozpowszechniane z nadzieją, że będzie\n" \
                          "użyteczne, ale BEZ JAKIEJKOLWIEK GWARANCJI; even without\n" \
                          "domniemanej gwarancji PRZYDATNOŚCI HANDLOWEJ lub\n" \
                          "PRZYDATNOŚCI DO OKREŚLONEGO CELU. Korzystasz z niej\n" \
                          "na własną odpowiedzialność.\n\n" \
                          "Pełną treść licencji GNU GPL można znaleźć na stronie:\n" \
                          "https://www.gnu.org/licenses/gpl-3.0.html\n\n" \
                          "---\n" \
                          "Wsparcie dla autora\n" \
                          "Jeśli doceniasz moją pracę, możesz postawić mi wirtualną kawę.\n" \
                          "Jest to dobrowolne, ale bardzo motywuje do dalszej pracy. Dziękuję!\n\nKontakt / wsparcie: aio-iptv@wp.pl"
        
        self["legal_text"] = Label(legal_note_text)
        self["changelog_title"] = Label("Ostatnie zmiany (z GitHub)")
        self["changelog_text"] = Label("Trwa pobieranie danych...")
        
        self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close, "ok": self.close}, -1)
        self.onShown.append(self.fetch_changelog)

    def fetch_changelog(self):
        Thread(target=self._background_changelog_fetch).start()

    def _background_changelog_fetch(self):
        changelog_url = "https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/changelog.txt"
        tmp_changelog_path = os.path.join(PLUGIN_TMP_PATH, 'changelog_info.txt')
        prepare_tmp_dir()
        
        found_version_tag = "" 
        
        try:
            cmd_log = "wget -O {} {}".format(tmp_changelog_path, changelog_url)
            process = subprocess.Popen(cmd_log, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.communicate() 

            changelog_text = "Nie można pobrać listy zmian."
            if os.path.exists(tmp_changelog_path) and os.path.getsize(tmp_changelog_path) > 0:
                # UNIVERSAL FIX: Use io.open
                with io.open(tmp_changelog_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                changes = []
                version_count = 0
                in_version_block = False

                for line in lines:
                    line = line.strip()
                    
                    if line.startswith("[") and line.endswith("]"):
                        version_count += 1
                        if version_count > 1: 
                            break
                        in_version_block = True
                        found_version_tag = line 
                        continue 
                    
                    if in_version_block and line:
                        changes.append(line)
                            
                if changes: 
                    changelog_text = "\n".join(changes)
                else:
                    changelog_text = "Nie znaleziono żadnych wpisów w changelogu."
            else:
                local_text = _read_text_file(os.path.join(PLUGIN_PATH, "changelog.txt"), "")
                if local_text:
                    changelog_text = "Tryb lokalny (offline):\n" + "\n".join(local_text.splitlines()[:12])
                    found_version_tag = "LOCAL"
        except Exception as e:
            print("[AIO Panel] Info screen changelog fetch error:", e)
            local_text = _read_text_file(os.path.join(PLUGIN_PATH, "changelog.txt"), "")
            changelog_text = ("Tryb lokalny (offline):\n" + "\n".join(local_text.splitlines()[:12])) if local_text else "Błąd podczas pobierania listy zmian."
            found_version_tag = "LOCAL" if local_text else found_version_tag
        
        reactor.callFromThread(self.update_changelog_label, changelog_text, found_version_tag)

    def update_changelog_label(self, text, version_tag):
        self["changelog_text"].setText(text)
        if version_tag == "LOCAL":
            self["changelog_title"].setText("Zmiany lokalne (offline)")
        elif version_tag:
            self["changelog_title"].setText("Zmiany dla {}".format(version_tag))
        else:
            self["changelog_title"].setText("Ostatnie zmiany (z GitHub)")
# *** KONIEC KLASY EKRANU INFO ***


class AIOTextViewerScreen(Screen):
    skin_large = """
    <screen position="center,center" size="900,560" title="AIO Viewer">
        <widget name="title" position="20,10" size="860,36" font="Regular;28" />
        <widget name="text" position="20,55" size="860,455" font="Regular;24" />
        <widget name="help" position="20,520" size="860,28" font="Regular;22" />
    </screen>
    """
    skin_small = """
    <screen position="center,center" size="690,430" title="AIO Viewer">
        <widget name="title" position="15,8" size="660,30" font="Regular;21" />
        <widget name="text" position="15,46" size="660,330" font="Regular;18" />
        <widget name="help" position="15,390" size="660,25" font="Regular;17" />
    </screen>
    """

    def __init__(self, session, title, content, help_text=None):
        self.skin = self.skin_small if _is_small_ui() else self.skin_large
        Screen.__init__(self, session)
        self.setTitle(title)
        self["title"] = Label(title)
        if ScrollLabel:
            self["text"] = ScrollLabel(content)
        else:
            self["text"] = Label(content)
        self["help"] = Label(help_text or "▲/▼ Scroll  EXIT=Back")
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "cancel": self.close,
            "ok": self.close,
            "up": self.page_up,
            "down": self.page_down,
        }, -1)

    def page_up(self):
        try:
            if ScrollLabel:
                self["text"].pageUp()
        except Exception:
            pass

    def page_down(self):
        try:
            if ScrollLabel:
                self["text"].pageDown()
        except Exception:
            pass


class AIOTipPopupScreen(Screen):
    skin = _aio_tip_screen_skin()

    def __init__(self, session, lang, tips, start_index=0):
        Screen.__init__(self, session)
        self.session = session
        self.lang = lang or "PL"
        self.tips = tips or ["Brak wskazówek."]
        self.idx = max(0, min(int(start_index or 0), len(self.tips) - 1))
        self.setTitle("💡 Tip dnia AIO" if self.lang == "PL" else "💡 AIO tip of the day")
        self["title"] = Label("💡 Tip dnia AIO" if self.lang == "PL" else "💡 AIO tip of the day")
        self["counter"] = Label("")
        if ScrollLabel:
            self["text"] = ScrollLabel("")
        else:
            self["text"] = Label("")
        self["help"] = Label("◀/▶ Poprzednia/Następna  ▲/▼ Scroll  OK/EXIT Zamknij" if self.lang == "PL" else "◀/▶ Previous/Next  ▲/▼ Scroll  OK/EXIT Close")
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "cancel": self.close,
            "ok": self.close,
            "left": self.prev_tip,
            "right": self.next_tip,
            "up": self.page_up,
            "down": self.page_down,
        }, -1)
        self._refresh_tip()

    def _refresh_tip(self):
        total = len(self.tips)
        if total <= 0:
            total = 1
        counter = ("Wskazówka {0}/{1}" if self.lang == "PL" else "Tip {0}/{1}").format(self.idx + 1, total)
        self["counter"].setText(counter)
        text = ensure_str(ensure_unicode(self.tips[self.idx]))
        try:
            self["text"].setText(text)
        except Exception:
            try:
                self["text"] = Label(text)
            except Exception:
                pass

    def prev_tip(self):
        if not self.tips:
            return
        self.idx = (self.idx - 1) % len(self.tips)
        self._refresh_tip()

    def next_tip(self):
        if not self.tips:
            return
        self.idx = (self.idx + 1) % len(self.tips)
        self._refresh_tip()

    def page_up(self):
        try:
            if ScrollLabel:
                self["text"].pageUp()
        except Exception:
            pass

    def page_down(self):
        try:
            if ScrollLabel:
                self["text"].pageDown()
        except Exception:
            pass


# === KLASA PanelAIO (GŁÓWNE OKNO) - WERSJA Z ZAKŁADKAMI v2 (Sterowanie L/R) ===

# === NOWE EKRANY v5.0 ===

class SystemMonitorScreen(Screen):
    skin = ("""
    <screen position="center,center" size="680,480" title="System Monitor">
        <widget name="title" position="16,10" size="648,34" font="Regular;24" />
        <widget name="info" position="16,54" size="648,370" font="Regular;21" />
        <widget name="help" position="16,440" size="648,26" font="Regular;18" />
    </screen>""" if _is_small_ui() else """
    <screen position="center,center" size="900,520" title="System Monitor">
        <widget name="title" position="20,10" size="860,40" font="Regular;32" />
        <widget name="info" position="20,60" size="860,420" font="Regular;26" />
        <widget name="help" position="20,485" size="860,30" font="Regular;22" />
    </screen>""")

    def __init__(self, session, lang="PL"):
        Screen.__init__(self, session)
        self.session = session
        self.lang = lang or "PL"
        self["title"] = Label("📊 Monitor Systemowy" if self.lang == "PL" else "📊 System Monitor")
        self["info"] = Label("")
        self["help"] = Label("🔴5s  🟢10s  🟡30s  OK=Refresh  EXIT=Back")
        self._timer = eTimer()
        try:
            self._timer_conn = self._timer.timeout.connect(self._update)
        except Exception:
            self._timer.callback.append(self._update)
        self._interval = 10
        self._prev_cpu = None
        self._closed = False
        self.onClose.append(self._stop_timer)
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "InfoActions"], {
            "ok": self._update,
            "cancel": self.close,
            "red": lambda: self._set_interval(5),
            "green": lambda: self._set_interval(10),
            "yellow": lambda: self._set_interval(30),
        }, -1)
        self.onShown.append(self._start)

    def _stop_timer(self):
        self._closed = True
        try: self._timer.stop()
        except Exception: pass

    def _start(self):
        if self._closed: return
        self._update()
        self._timer.start(self._interval * 1000, True)

    def _set_interval(self, sec):
        self._interval = int(sec)
        self._update()
        self._timer.start(self._interval * 1000, True)

    def _read_cpu_percent(self):
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
            parts = line.split()
            if parts[0] != "cpu":
                return None
            nums = list(map(int, parts[1:8]))
            total = sum(nums)
            idle = nums[3] + nums[4]  # idle + iowait
            if self._prev_cpu is None:
                self._prev_cpu = (total, idle)
                return 0.0
            prev_total, prev_idle = self._prev_cpu
            dt = total - prev_total
            di = idle - prev_idle
            self._prev_cpu = (total, idle)
            if dt <= 0:
                return 0.0
            used = (dt - di) * 100.0 / float(dt)
            return max(0.0, min(100.0, used))
        except Exception:
            return None

    def _read_mem(self):
        try:
            mem = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    mem[k.strip()] = int(v.strip().split()[0])
            total = mem.get("MemTotal", 0)
            avail = mem.get("MemAvailable", mem.get("MemFree", 0))
            used = max(0, total - avail)
            pct = (used * 100.0 / float(total)) if total else 0.0
            return total, used, pct
        except Exception:
            return None, None, None

    def _read_temp_c(self):
        # Try thermal zones
        paths = []
        try:
            base = "/sys/class/thermal"
            if os.path.isdir(base):
                for d in os.listdir(base):
                    if d.startswith("thermal_zone"):
                        p = os.path.join(base, d, "temp")
                        paths.append(p)
        except Exception:
            pass
        # Try hwmon
        try:
            base = "/sys/class/hwmon"
            if os.path.isdir(base):
                for d in os.listdir(base):
                    dp = os.path.join(base, d)
                    for fn in os.listdir(dp):
                        if fn.startswith("temp") and fn.endswith("_input"):
                            paths.append(os.path.join(dp, fn))
        except Exception:
            pass
        vals = []
        for p in paths:
            try:
                if os.path.isfile(p):
                    raw = open(p, "r").read().strip()
                    if not raw:
                        continue
                    v = float(raw)
                    if v > 1000:
                        v = v / 1000.0
                    if 0.0 < v < 150.0:
                        vals.append(v)
            except Exception:
                continue
        if not vals:
            return None
        return max(vals)

    def _disk_usage_str(self, path):
        try:
            if not os.path.exists(path):
                return None
            # UNIVERSAL FIX: Use polyfilled shutil_disk_usage
            du = shutil_disk_usage(path)
            total = du.total
            used = du.used
            pct = (used * 100.0 / float(total)) if total else 0.0
            return "%s: %.1f%% (%.1fGB/%.1fGB)" % (path, pct, used/1e9, total/1e9)
        except Exception:
            return None

    def _update(self, *args):
        cpu = self._read_cpu_percent()
        mt, mu, mp = self._read_mem()
        temp = self._read_temp_c()
        disk_root = self._disk_usage_str("/")
        disk_hdd = self._disk_usage_str("/media/hdd")
        lines = []
        if cpu is None: lines.append("CPU: N/A")
        else: lines.append("CPU: %.1f%%" % cpu)
        if mt is None: lines.append("RAM: N/A")
        else: lines.append("RAM: %.1f%% (%.1fMB/%.1fMB)" % (mp, mu/1024.0, mt/1024.0))
        if temp is None: lines.append(("TEMP: N/A (brak czujnika)" if self.lang=="PL" else "TEMP: N/A (no sensor)"))
        else: lines.append("TEMP: %.1f°C" % temp)
        if disk_root: lines.append(disk_root)
        if disk_hdd: lines.append(disk_hdd)
        self["info"].setText("\n".join(lines))
        self._timer.start(self._interval * 1000, True)


class LogViewerScreen(Screen):
    skin = ("""
    <screen position="center,center" size="690,500" title="Log Viewer">
        <widget name="title" position="16,10" size="658,34" font="Regular;23" />
        <widget name="log" position="16,52" size="658,390" font="Regular;18" />
        <widget name="help" position="16,458" size="658,26" font="Regular;17" />
    </screen>""" if _is_small_ui() else """
    <screen position="center,center" size="1050,650" title="Log Viewer">
        <widget name="title" position="20,10" size="1010,40" font="Regular;30" />
        <widget name="log" position="20,60" size="1010,540" font="Regular;22" />
        <widget name="help" position="20,610" size="1010,30" font="Regular;22" />
    </screen>""")

    SOURCES = [
        ("messages", "/var/log/messages"),
        ("syslog", "/var/log/syslog"),
        ("enigma2.log", "/tmp/enigma2.log"),
        ("enigma2_debug.log", "/home/root/logs/enigma2_debug.log"),
        ("enigma2_crash.log", "/home/root/logs/enigma2_crash.log"),
    ]

    def __init__(self, session, lang="PL"):
        Screen.__init__(self, session)
        self.session = session
        self.lang = lang or "PL"
        self._idx = 0
        self["title"] = Label("")
        if ScrollLabel:
            self["log"] = ScrollLabel("")
        else:
            self["log"] = Label("")
        self["help"] = Label("◄/► Source  🟡AutoRefresh  OK=Refresh  ▲/▼ Scroll  EXIT=Back")
        self._auto = False
        self._closed = False
        self._timer = eTimer()
        try:
            self._timer_conn = self._timer.timeout.connect(self._on_timer)
        except Exception:
            self._timer.callback.append(self._on_timer)
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
            "ok": self.refresh,
            "cancel": self.close,
            "left": self.prev_source,
            "right": self.next_source,
            "up": self.page_up,
            "down": self.page_down,
            "yellow": self.toggle_auto,
        }, -1)
        self.onShown.append(self.refresh)
        self.onClose.append(self._stop_timer)

    def _stop_timer(self):
        self._closed = True
        try: self._timer.stop()
        except Exception: pass

    def _on_timer(self):
        if self._auto:
            self.refresh()

    def toggle_auto(self):
        self._auto = not self._auto
        if self._auto:
            self._timer.start(5000, True)
        self.refresh()

    def prev_source(self):
        self._idx = (self._idx - 1) % len(self.SOURCES)
        self.refresh()

    def next_source(self):
        self._idx = (self._idx + 1) % len(self.SOURCES)
        self.refresh()

    def _tail(self, path, n=100):
        if not fileExists(path):
            return "Brak pliku: %s" % path if self.lang == "PL" else "Missing file: %s" % path
        try:
            cmd = "tail -n %d %s 2>/dev/null" % (n, path)
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = p.communicate()
            if IS_PY3:
                return out.decode("utf-8", "ignore")
            else:
                return out
        except Exception as e:
            return "Error: %s" % e

    def refresh(self):
        name, path = self.SOURCES[self._idx]
        title = ("📄 Logi: %s" % name) if self.lang == "PL" else ("📄 Logs: %s" % name)
        if self._auto:
            title += " [AUTO]"
        self["title"].setText(title)
        data = self._tail(path, 100)
        if ScrollLabel:
            self["log"].setText(data)
        else:
            self["log"].setText(data)
        if self._auto and not self._closed:
            self._timer.start(5000, True)

    def page_up(self):
        try:
            if ScrollLabel: self["log"].pageUp()
        except Exception:
            pass

    def page_down(self):
        try:
            if ScrollLabel: self["log"].pageDown()
        except Exception:
            pass


def _get_cron_file_path():
    candidates = ["/etc/crontabs/root", "/var/spool/cron/crontabs/root", "/etc/cron/crontabs/root"]
    for p in candidates:
        if os.path.exists(p):
            return p
    # ensure directory exists for /etc/crontabs
    try:
        os.makedirs("/etc/crontabs")
    except Exception:
        pass
    return "/etc/crontabs/root"


class CronManagerScreen(Screen):
    skin_large = """
    <screen position="center,center" size="950,620" title="Cron Manager">
        <widget name="title" position="20,10" size="910,40" font="Regular;30" />
        <widget name="list" position="20,60" size="910,500" scrollbarMode="showOnDemand" />
        <widget name="help" position="20,570" size="910,40" font="Regular;22" />
    </screen>"""
    skin_small = """
    <screen position="center,center" size="690,440" title="Cron Manager">
        <widget name="title" position="15,8" size="660,32" font="Regular;22" />
        <widget name="list" position="15,48" size="660,330" scrollbarMode="showOnDemand" />
        <widget name="help" position="15,392" size="660,30" font="Regular;17" />
    </screen>"""

    DISABLED_PREFIX = "#AIO_DISABLED# "

    def __init__(self, session, lang="PL"):
        self.skin = self.skin_small if _is_small_ui() else self.skin_large
        Screen.__init__(self, session)
        self.session = session
        self.lang = lang or "PL"
        self.cron_path = _get_cron_file_path()
        self["title"] = Label("⏰ Menedżer Cron" if self.lang=="PL" else "⏰ Cron Manager")
        self["list"] = MenuList([])
        self["help"] = Label("🔴Add  🟢Edit  🟡Enable/Disable  🔵Delete  OK=View  EXIT=Back")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.view_entry,
            "cancel": self.close,
            "red": self.add_entry,
            "green": self.edit_entry,
            "yellow": self.toggle_entry,
            "blue": self.delete_entry,
        }, -1)
        self.onShown.append(self.reload)

    def _read_lines(self):
        try:
            if not os.path.exists(self.cron_path):
                return []
            with open(self.cron_path, "r") as f:
                return [l.rstrip("\n") for l in f.readlines()]
        except Exception:
            return []

    def _write_lines(self, lines):
        try:
            parent = os.path.dirname(self.cron_path)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent)
            _atomic_write(self.cron_path, "\n".join(lines).rstrip("\n") + "\n")
            try:
                os.chmod(self.cron_path, 0o600)
            except Exception:
                pass
            self._reload_daemon()
            return True
        except Exception as e:
            show_message_compat(self.session, "Błąd zapisu cron: %s" % e, MessageBox.TYPE_ERROR, timeout=6)
            return False

    def _reload_daemon(self):
        for script in ('/etc/init.d/cron', '/etc/init.d/crond'):
            if os.path.isfile(script) and os.access(script, os.X_OK):
                subprocess.call([script, 'restart'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return
        if shutil_which('systemctl'):
            for unit in ('cron.service', 'crond.service'):
                try:
                    out = subprocess.check_output(['systemctl', 'show', unit, '--property=LoadState', '--value'], stderr=subprocess.STDOUT)
                    value = out.decode('utf-8', 'ignore').strip() if not isinstance(out, str) else out.strip()
                    if value == 'loaded':
                        subprocess.call(['systemctl', 'restart', unit], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        return
                except Exception:
                    continue
        try:
            subprocess.call(['killall', '-HUP', 'crond'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            pass

    def reload(self):
        self.lines = [l for l in self._read_lines() if l.strip() and not l.strip().startswith("#") or l.strip().startswith(self.DISABLED_PREFIX)]
        items = []
        for l in self.lines:
            disabled = l.startswith(self.DISABLED_PREFIX)
            view = l[len(self.DISABLED_PREFIX):] if disabled else l
            prefix = "[OFF] " if disabled else "[ON]  "
            items.append(prefix + view)
        if not items:
            items = ["(brak wpisów)" if self.lang=="PL" else "(no entries)"]
            self.lines = []
        self["list"].setList(items)

    def _get_index(self):
        return self["list"].getSelectionIndex()

    def view_entry(self):
        i = self._get_index()
        if i < 0 or i >= len(self.lines):
            return
        l = self.lines[i]
        disabled = l.startswith(self.DISABLED_PREFIX)
        view = l[len(self.DISABLED_PREFIX):] if disabled else l
        self.session.open(MessageBox, view, type=MessageBox.TYPE_INFO, timeout=10)

    def add_entry(self):
        def cb(txt):
            if not txt:
                return
            lines = self._read_lines()
            lines.append(txt.strip())
            if self._write_lines(lines):
                self.reload()
        self.session.openWithCallback(cb, InputBox, title="Cron line (e.g. */5 * * * * /path/script.sh)", text="")

    def edit_entry(self):
        i = self._get_index()
        if i < 0 or i >= len(self.lines):
            return
        old = self.lines[i]
        disabled = old.startswith(self.DISABLED_PREFIX)
        view = old[len(self.DISABLED_PREFIX):] if disabled else old

        def cb(txt):
            if txt is None:
                return
            lines = self._read_lines()
            # locate exact line and replace first match
            try:
                idx = lines.index(old)
                new_line = (self.DISABLED_PREFIX + txt.strip()) if disabled else txt.strip()
                lines[idx] = new_line
            except Exception:
                pass
            if self._write_lines(lines):
                self.reload()
        self.session.openWithCallback(cb, InputBox, title="Edit cron line", text=view)

    def toggle_entry(self):
        i = self._get_index()
        if i < 0 or i >= len(self.lines):
            return
        old = self.lines[i]
        lines = self._read_lines()
        try:
            idx = lines.index(old)
        except Exception:
            return
        if old.startswith(self.DISABLED_PREFIX):
            lines[idx] = old[len(self.DISABLED_PREFIX):]
        else:
            lines[idx] = self.DISABLED_PREFIX + old
        if self._write_lines(lines):
            self.reload()

    def delete_entry(self):
        i = self._get_index()
        if i < 0 or i >= len(self.lines):
            return
        old = self.lines[i]

        def cb(ret):
            if not ret:
                return
            lines = self._read_lines()
            try:
                lines.remove(old)
            except Exception:
                pass
            if self._write_lines(lines):
                self.reload()
        self.session.openWithCallback(cb, MessageBox, "Delete selected cron entry?", type=MessageBox.TYPE_YESNO)


class ServiceManagerScreen(Screen):
    skin_large = """
    <screen position="center,center" size="950,620" title="Service Manager">
        <widget name="title" position="20,10" size="910,40" font="Regular;30" />
        <widget name="list" position="20,60" size="910,500" scrollbarMode="showOnDemand" />
        <widget name="help" position="20,570" size="910,40" font="Regular;22" />
    </screen>"""
    skin_small = """
    <screen position="center,center" size="690,440" title="Service Manager">
        <widget name="title" position="15,8" size="660,32" font="Regular;22" />
        <widget name="list" position="15,48" size="660,330" scrollbarMode="showOnDemand" />
        <widget name="help" position="15,392" size="660,30" font="Regular;17" />
    </screen>"""

    SERVICES = [
        ("SSH", ["sshd", "dropbear"]),
        ("FTP", ["vsftpd", "proftpd", "pure-ftpd"]),
        ("Samba", ["smbd", "samba", "nmbd"]),
        ("NFS", ["nfs-server", "nfs"]),
        ("Cron", ["cron", "crond"]),
        ("Telnet", ["telnetd"]),
    ]

    def __init__(self, session, lang="PL"):
        self.skin = self.skin_small if _is_small_ui() else self.skin_large
        Screen.__init__(self, session)
        self.session = session
        self.lang = lang or "PL"
        self["title"] = Label("🔌 Menedżer Usług" if self.lang=="PL" else "🔌 Service Manager")
        self["list"] = MenuList([])
        self["help"] = Label("🔴Stop  🟢Start  🟡Restart  OK=Status  EXIT=Back")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.show_status,
            "cancel": self.close,
            "red": lambda: self._action("stop"),
            "green": lambda: self._action("start"),
            "yellow": lambda: self._action("restart"),
        }, -1)
        self.onShown.append(self.refresh)

    def _systemctl(self, args):
        cmd = "systemctl %s 2>/dev/null" % args
        return subprocess.call(cmd, shell=True) == 0

    def _is_systemd(self):
        return os.path.exists("/bin/systemctl") or os.path.exists("/usr/bin/systemctl")

    def _is_active(self, svc):
        if self._is_systemd():
            cmd = "systemctl is-active %s 2>/dev/null" % svc
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = p.communicate()
            if IS_PY3:
                return out.decode("utf-8","ignore").strip() == "active"
            else:
                return out.strip() == "active"
        # fallback pidof
        cmd = "pidof %s >/dev/null 2>&1" % svc
        return subprocess.call(cmd, shell=True) == 0

    def refresh(self):
        items = []
        for disp, names in self.SERVICES:
            status = "unknown"
            active = False
            for n in names:
                if self._is_active(n):
                    active = True
                    status = n
                    break
            items.append("%s: %s" % (disp, ("ON" if active else "OFF")))
        self["list"].setList(items)

    def _get_selected_service_names(self):
        i = self["list"].getSelectionIndex()
        if i < 0 or i >= len(self.SERVICES):
            return None
        return self.SERVICES[i][1]

    def _detect_service_backend(self, names):
        for name in names or []:
            unit = name + '.service'
            if self._is_systemd():
                try:
                    proc = subprocess.Popen(['systemctl', 'show', unit, '--property=LoadState', '--value'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    output, _error = proc.communicate()
                    if IS_PY3 and not isinstance(output, str):
                        output = output.decode('utf-8', 'ignore')
                    state = ensure_unicode(output).strip().lower()
                    if proc.returncode == 0 and state == 'loaded':
                        return ('systemd', unit, name)
                except Exception:
                    pass
            script = '/etc/init.d/' + name
            if os.path.isfile(script) and os.access(script, os.X_OK):
                return ('init', script, name)
        for name in names or []:
            if self._is_active(name):
                return ('process', name, name)
        return (None, None, names[0] if names else '')

    def _action(self, act):
        names = self._get_selected_service_names()
        if not names:
            return
        backend, target, display = self._detect_service_backend(names)
        if backend == 'systemd':
            cmd = 'systemctl %s %s' % (act, _safe_shell_arg(target))
        elif backend == 'init':
            cmd = '%s %s' % (_safe_shell_arg(target), act)
        else:
            show_message_compat(self.session, ('Nie znaleziono usługi: %s' if self.lang == 'PL' else 'Service not found: %s') % ', '.join(names), MessageBox.TYPE_ERROR)
            return
        self.session.openWithCallback(lambda *a: self.refresh(), Console, title='Service: %s (%s)' % (display, act), cmdlist=[cmd], closeOnSuccess=False)

    def show_status(self):
        names = self._get_selected_service_names()
        if not names:
            return
        backend, target, display = self._detect_service_backend(names)
        if backend == 'systemd':
            cmd = 'systemctl status %s --no-pager | tail -n 60' % _safe_shell_arg(target)
        elif backend == 'init':
            cmd = '%s status 2>/dev/null || ps | grep -E %s | grep -v grep' % (_safe_shell_arg(target), _safe_shell_arg('|'.join(names)))
        else:
            cmd = 'ps | grep -E %s | grep -v grep || true' % _safe_shell_arg('|'.join(names))
        self.session.open(Console, title='Status: %s' % display, cmdlist=[cmd], closeOnSuccess=False)

class SystemInfoScreen(Screen):
    skin_large = """
    <screen position="center,center" size="1050,650" title="System Information">
        <widget name="title" position="20,10" size="1010,40" font="Regular;30" />
        <widget name="info" position="20,60" size="1010,530" font="Regular;22" halign="left" valign="top" />
        <widget name="help" position="20,610" size="1010,25" font="Regular;22" />
    </screen>"""
    skin_small = """
    <screen position="center,center" size="690,440" title="System Information">
        <widget name="title" position="15,8" size="660,30" font="Regular;21" />
        <widget name="info" position="15,46" size="660,330" font="Regular;17" halign="left" valign="top" />
        <widget name="help" position="15,394" size="660,25" font="Regular;17" />
    </screen>"""

    def __init__(self, session, lang="PL"):
        self.skin = self.skin_small if _is_small_ui() else self.skin_large
        Screen.__init__(self, session)
        self.session = session
        self.lang = lang or "PL"
        self["title"] = Label("ℹ️ Informacje o Systemie" if self.lang=="PL" else "ℹ️ System Information")
        if ScrollLabel:
            self["info"] = ScrollLabel("")
        else:
            self["info"] = Label("")
        self["help"] = Label("▲/▼ Scroll  EXIT=Back")
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "cancel": self.close,
            "up": self.page_up,
            "down": self.page_down,
        }, -1)
        self.onShown.append(self.refresh)

    def _read_first(self, path):
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except Exception:
            return ""

    def refresh(self):
        lines = []
        # Image / kernel / uptime
        lines.append("Kernel: " + self._read_first("/proc/version").split("\n")[0])
        try:
            up = float(self._read_first("/proc/uptime").split()[0])
            lines.append("Uptime: %.1f h" % (up/3600.0))
        except Exception:
            pass
        # CPU
        cpuinfo = self._read_first("/proc/cpuinfo")
        model = ""
        for l in cpuinfo.splitlines():
            if l.lower().startswith("model name") or l.lower().startswith("hardware") or l.lower().startswith("processor"):
                model = l.split(":",1)[-1].strip()
                if model:
                    break
        if model:
            lines.append("CPU: " + model)
        # Mem
        try:
            mem = {}
            for l in self._read_first("/proc/meminfo").splitlines():
                k, v = l.split(":",1)
                mem[k.strip()] = int(v.strip().split()[0])
            total = mem.get("MemTotal",0)/1024.0
            avail = mem.get("MemAvailable", mem.get("MemFree",0))/1024.0
            used = total - avail
            lines.append("RAM: %.1fMB used / %.1fMB total" % (used, total))
        except Exception:
            pass
        # Network ips
        try:
            cmd = "ip -4 addr 2>/dev/null | grep -E 'inet ' | awk '{print $2\" \"$NF}'"
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = p.communicate()
            if IS_PY3:
                ips = out.decode("utf-8","ignore").strip()
            else:
                ips = out.strip()
            if ips:
                lines.append("")
                lines.append("IP:")
                lines.append(ips)
        except Exception:
            pass
        # Disks
        try:
            lines.append("")
            lines.append("Disks:")
            out = subprocess.check_output("df -h | head -n 20", shell=True)
            if IS_PY3:
                lines.append(out.decode("utf-8","ignore"))
            else:
                lines.append(out)
        except Exception:
            pass

        data = "\n".join(lines)
        if ScrollLabel:
            self["info"].setText(data)
        else:
            self["info"].setText(data)

    def page_up(self):
        try:
            if ScrollLabel: self["info"].pageUp()
        except Exception:
            pass

    def page_down(self):
        try:
            if ScrollLabel: self["info"].pageDown()
        except Exception:
            pass

class UninstallManagerScreen(Screen):
    skin_large = """
    <screen name="UninstallManagerScreen" position="center,center" size="1100,660" title="Uninstall">
        <widget name="list" position="20,20" size="1060,560" scrollbarMode="showOnDemand" />
        <widget name="status" position="20,595" size="1060,40" font="Regular;24" halign="left" valign="center" />
    </screen>
    """
    skin_small = """
    <screen name="UninstallManagerScreen" position="center,center" size="690,440" title="Uninstall">
        <widget name="list" position="15,15" size="660,340" scrollbarMode="showOnDemand" />
        <widget name="status" position="15,374" size="660,45" font="Regular;17" halign="left" valign="center" />
    </screen>
    """

    def __init__(self, session, lang='PL'):
        self.skin = self.skin_small if _is_small_ui() else self.skin_large
        Screen.__init__(self, session)
        self.lang = lang or 'PL'
        self.session = session

        if self.lang == 'PL':
            self.setTitle("Menadżer deinstalacji (opkg)")
            self._t_loading = "Pobieranie listy pakietów..."
            self._t_ready = "Znaleziono: {n} pakietów. OK=usuń, Czerwony=odśwież, Zielony=usuń, Niebieski=wyjście"
            self._t_err = "Błąd: nie udało się pobrać listy pakietów."
            self._t_confirm = "Odinstalować pakiet:\n\n{pkg}\n\nPotwierdzasz?"
            self._t_no_sel = "Brak zaznaczonego pakietu."
        else:
            self.setTitle("Uninstall manager (opkg)")
            self._t_loading = "Loading package list..."
            self._t_ready = "Found: {n} packages. OK=remove, Red=refresh, Green=remove, Blue=exit"
            self._t_err = "Error: could not fetch package list."
            self._t_confirm = "Remove package:\n\n{pkg}\n\nConfirm?"
            self._t_no_sel = "No package selected."

        self["list"] = MenuList([])
        self["status"] = Label(self._t_loading)

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self.uninstall_selected,
                "cancel": self.close,
                "red": self.reload_list,
                "green": self.uninstall_selected,
                "blue": self.close,
            },
            -1
        )

        self.onShown.append(self.reload_list)

    def _current_pkg(self):
        try:
            cur = self["list"].getCurrent()
            if not cur:
                return None
            return cur[1]
        except Exception:
            return None

    def reload_list(self):
        self["status"].setText(self._t_loading)
        try:
            out = os.popen("opkg list-installed").read().splitlines()
        except Exception:
            out = []

        items = []
        for line in out:
            line = (line or "").strip()
            if not line:
                continue
            parts = line.split(" - ", 1)
            pkg = parts[0].strip()
            ver = parts[1].strip() if len(parts) > 1 else ""
            disp = ("%s - %s" % (pkg, ver)) if ver else pkg
            items.append((disp, pkg))

        items.sort(key=lambda x: x[0].lower())
        self["list"].setList(items)

        if items:
            self["status"].setText(self._t_ready.format(n=len(items)))
        else:
            self["status"].setText(self._t_err)

    def uninstall_selected(self):
        pkg = self._current_pkg()
        if not pkg:
            show_message_compat(self.session, self._t_no_sel, title="Info")
            return
        self.session.openWithCallback(
            lambda ans: self._do_uninstall(ans, pkg),
            MessageBox,
            self._t_confirm.format(pkg=pkg),
            MessageBox.TYPE_YESNO
        )

    def _do_uninstall(self, answer, pkg):
        if not answer:
            return
        if not _validate_identifier(pkg):
            show_message_compat(self.session, self._t_no_sel, MessageBox.TYPE_ERROR)
            return
        cmd = "opkg remove %s" % _safe_shell_arg(pkg)
        console_screen_open(
            self.session,
            ("Odinstalowanie: %s" % pkg) if self.lang == 'PL' else ("Removing: %s" % pkg),
            [cmd],
            callback=lambda *a: self.reload_list(),
            close_on_finish=True
        )




class PluginUpdateManagerScreen(Screen):
    skin_large = """
    <screen name="PluginUpdateManagerScreen" position="center,center" size="1160,690" title="Plugin Updates">
        <widget name="list" position="20,20" size="1120,560" scrollbarMode="showOnDemand" />
        <widget name="status" position="20,595" size="1120,35" font="Regular;24" halign="left" valign="center" />
        <widget name="hint" position="20,635" size="1120,35" font="Regular;22" halign="left" valign="center" />
    </screen>
    """
    skin_small = """
    <screen name="PluginUpdateManagerScreen" position="center,center" size="690,445" title="Plugin Updates">
        <widget name="list" position="15,15" size="660,330" scrollbarMode="showOnDemand" />
        <widget name="status" position="15,355" size="660,32" font="Regular;18" halign="left" valign="center" />
        <widget name="hint" position="15,398" size="660,32" font="Regular;17" halign="left" valign="center" />
    </screen>
    """

    def __init__(self, session, lang='PL'):
        self.skin = self.skin_small if _is_small_ui() else self.skin_large
        Screen.__init__(self, session)
        self.lang = lang or 'PL'
        self.session = session
        self._load_started = False
        self._loading = False
        self._closed = False
        self._worker_state = {"done": False, "result": None, "error": None}

        if self.lang == 'PL':
            self.setTitle("Aktualizacje zainstalowanych wtyczek")
            self._t_loading = "Sprawdzanie aktualizacji OPKG i GitHub/Custom..."
            self._t_ready = "OPKG: {opkg} | GitHub/Custom: {custom} | Czerwony=odśwież, Zielony/OK=aktualizuj, Niebieski=wyjście"
            self._t_none = "Brak dostępnych aktualizacji."
            self._t_error = "Błąd sprawdzania aktualizacji."
            self._t_opkg_header = r"\c00FFD200--- Aktualizacje OPKG ---\c00ffffff"
            self._t_custom_header = r"\c00FFD200--- Aktualizacje GitHub/Custom ---\c00ffffff"
            self._t_no_opkg = "Brak aktualizacji OPKG"
            self._t_no_custom = "Brak aktualizacji GitHub/Custom"
            self._t_no_sel = "Wybierz pozycję z listy aktualizacji."
            self._t_confirm_opkg = "Zaktualizować pakiet OPKG?\n\n{pkg}\n\nWersja lokalna: {local}\nWersja dostępna: {remote}"
            self._t_confirm_custom = "Zainstalować aktualizację GitHub/Custom?\n\n{name}\n\nWersja lokalna: {local}\nWersja dostępna: {remote}"
            self._t_running = "Uruchamianie aktualizacji: {name}"
            self._t_refresh_hint = "Lista obejmuje tylko zainstalowane wtyczki Enigma2 z widoczną nowszą wersją."
        else:
            self.setTitle("Installed plugin updates")
            self._t_loading = "Checking OPKG and GitHub/Custom updates..."
            self._t_ready = "OPKG: {opkg} | GitHub/Custom: {custom} | Red=refresh, Green/OK=update, Blue=exit"
            self._t_none = "No updates available."
            self._t_error = "Update check error."
            self._t_opkg_header = r"\c00FFD200--- OPKG Updates ---\c00ffffff"
            self._t_custom_header = r"\c00FFD200--- GitHub/Custom Updates ---\c00ffffff"
            self._t_no_opkg = "No OPKG updates"
            self._t_no_custom = "No GitHub/Custom updates"
            self._t_no_sel = "Select an update entry from the list."
            self._t_confirm_opkg = "Update OPKG package?\n\n{pkg}\n\nLocal version: {local}\nAvailable version: {remote}"
            self._t_confirm_custom = "Install GitHub/Custom update?\n\n{name}\n\nLocal version: {local}\nAvailable version: {remote}"
            self._t_running = "Running update: {name}"
            self._t_refresh_hint = "The list contains only installed Enigma2 plugins with a newer visible release."

        self["list"] = MenuList([])
        self["status"] = Label(self._t_loading)
        self["hint"] = Label(self._t_refresh_hint)

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self.update_selected,
                "cancel": self.close,
                "red": self.reload_list,
                "green": self.update_selected,
                "blue": self.close,
            },
            -1
        )

        self._poll_timer = eTimer()
        try:
            self._poll_conn = self._poll_timer.timeout.connect(self._poll_worker)
        except Exception:
            self._poll_conn = None
            try:
                self._poll_timer.callback.append(self._poll_worker)
            except Exception:
                pass

        self.onShown.append(self._start_reload_once)
        self.onClose.append(self._stop_polling)

    def _stop_polling(self):
        self._closed = True
        try: self._poll_timer.stop()
        except Exception: pass

    def _start_reload_once(self):
        if self._load_started:
            return
        self._load_started = True
        self.reload_list()

    def _build_list_entries(self, result):
        entries = []
        opkg_items = result.get("opkg", []) if isinstance(result, dict) else []
        custom_items = result.get("custom", []) if isinstance(result, dict) else []

        entries.append((self._t_opkg_header, {"type": "separator"}))
        if opkg_items:
            for item in opkg_items:
                text = "📦 {name} | {local} → {remote}".format(
                    name=ensure_unicode(item.get("name") or item.get("package") or "").strip(),
                    local=ensure_unicode(item.get("current_version", "")).strip() or "?",
                    remote=ensure_unicode(item.get("remote_version", "")).strip() or "?"
                )
                entries.append((text, item))
        else:
            entries.append((self._t_no_opkg, {"type": "placeholder"}))

        entries.append((self._t_custom_header, {"type": "separator"}))
        if custom_items:
            for item in custom_items:
                text = "🌐 {name} | {local} → {remote}".format(
                    name=ensure_unicode(item.get("name") or item.get("package") or "").strip(),
                    local=ensure_unicode(item.get("current_version", "")).strip() or "?",
                    remote=ensure_unicode(item.get("remote_version", "")).strip() or "?"
                )
                entries.append((text, item))
        else:
            entries.append((self._t_no_custom, {"type": "placeholder"}))
        return entries

    def _current_entry(self):
        try:
            current = self["list"].getCurrent()
            if not current or len(current) < 2:
                return None
            data = current[1]
            if not isinstance(data, dict):
                return None
            if data.get("type") in ("separator", "placeholder"):
                return None
            return data
        except Exception:
            return None

    def reload_list(self):
        if self._loading:
            return
        self._loading = True
        self["status"].setText(self._t_loading)
        self["list"].setList([(self._t_loading, {"type": "placeholder"})])
        self._worker_state = {"done": False, "result": None, "error": None}

        def worker():
            try:
                self._worker_state["result"] = _collect_plugin_updates_snapshot(self.lang)
            except Exception as e:
                self._worker_state["error"] = ensure_unicode(e)
            self._worker_state["done"] = True

        thread = Thread(target=worker)
        try:
            thread.setDaemon(True)
        except Exception:
            pass
        thread.start()

        try:
            self._poll_timer.start(250, True)
        except Exception:
            pass

    def _poll_worker(self):
        if self._closed:
            return
        if not self._worker_state.get("done"):
            try:
                self._poll_timer.start(250, True)
            except Exception:
                pass
            return

        self._loading = False
        error = self._worker_state.get("error")
        result = self._worker_state.get("result") or {"opkg": [], "custom": []}

        if error:
            self["list"].setList([(self._t_error, {"type": "placeholder"})])
            self["status"].setText("{0}: {1}".format(self._t_error, error))
            return

        entries = self._build_list_entries(result)
        self["list"].setList(entries)

        opkg_count = len(result.get("opkg", []))
        custom_count = len(result.get("custom", []))
        total = opkg_count + custom_count
        if total > 0:
            self["status"].setText(self._t_ready.format(opkg=opkg_count, custom=custom_count))
        else:
            self["status"].setText(self._t_none)

    def update_selected(self):
        entry = self._current_entry()
        if not entry:
            show_message_compat(self.session, self._t_no_sel)
            return

        entry_type = ensure_unicode(entry.get("type", "")).strip()
        package = ensure_unicode(entry.get("package", "")).strip()
        display_name = ensure_unicode(entry.get("name") or package).strip()
        local_ver = ensure_unicode(entry.get("current_version", "")).strip() or "?"
        remote_ver = ensure_unicode(entry.get("remote_version", "")).strip() or "?"

        if entry_type == "opkg":
            message = self._t_confirm_opkg.format(pkg=package, local=local_ver, remote=remote_ver)
        else:
            message = self._t_confirm_custom.format(name=display_name, local=local_ver, remote=remote_ver)

        self.session.openWithCallback(
            lambda answer: self._run_update(answer, entry),
            MessageBox,
            message,
            MessageBox.TYPE_YESNO
        )

    def _run_update(self, answer, entry):
        if not answer:
            return
        entry_type = ensure_unicode(entry.get('type', '')).strip()
        package = ensure_unicode(entry.get('package', '')).strip()
        display_name = ensure_unicode(entry.get('name') or package).strip()
        if entry_type == 'opkg':
            if not _validate_identifier(package):
                show_message_compat(self.session, self._t_error, MessageBox.TYPE_ERROR)
                return
            cmd = 'opkg update && opkg upgrade %s' % _safe_shell_arg(package)
        else:
            url = ensure_unicode(entry.get('download_url', '')).strip()
            expected = ensure_unicode(entry.get('expected_package_regex', '')).strip()
            checksum = ensure_unicode(entry.get('expected_sha256', '')).strip()
            if not _is_https_allowed(url) or not expected:
                show_message_compat(self.session, self._t_error, MessageBox.TYPE_ERROR)
                return
            status = os.path.join(PLUGIN_TMP_PATH, 'custom_update_%s.status' % int(time.time() * 1000))
            cmd = '/bin/sh %s %s %s %s %s' % tuple(_safe_shell_arg(x) for x in (os.path.join(PLUGIN_PATH, 'safe_ipk_install.sh'), url, expected, status, checksum))
        def finished(result):
            if result and result.get('success'):
                show_message_compat(self.session, ('Aktualizacja zakończona. Restart wykonaj ręcznie po sprawdzeniu działania.' if self.lang == 'PL' else 'Update completed. Restart manually after checking operation.'), timeout=8)
                self.reload_list()
            else:
                show_message_compat(self.session, self._t_error + '\n\n' + ensure_unicode((result or {}).get('stderr', '')), MessageBox.TYPE_ERROR, timeout=14)
        run_command_in_background(self.session, self._t_running.format(name=display_name), [cmd], callback_on_finish=finished)


# === OPISY FUNKCJI DLA SYSTEMU TOOLTIP (v6.1) ===
FUNCTION_DESCRIPTIONS = {
    "PL": {
        # Lista kanałów
        "📺 Listy Kanałów": "Zarządzanie listami kanałów: instalacja, aktualizacja i przywracanie.\nObsługa importu list IPTV (M3U) oraz szybki powrót do poprzedniego stanu.",
        "📡 Paweł Pawełek HB 13E (04.01.2026)": "Oficjalna lista kanałów dla HotBird 13E.\nInstalacja listy wraz z automatycznym odświeżeniem bouquetów w Enigma2.",
        "📺 XStreamity - Instalator": "Instaluje XStreamity (IPTV).\nObsługa M3U oraz Xtream Codes; po instalacji uruchom z menu Wtyczki.",
        "📺 IPTV Dream - Instalator": "Instaluje IPTV Dream (zaawansowany odtwarzacz IPTV).\nWymagane biblioteki możesz doinstalować z pozycji zależności IPTV.",
        "🩺 E2 Doctor - Instalator (Python 3)": "Instaluje E2 Doctor z oficjalnego repozytorium autora.\nNarzędzie wykonuje diagnostykę tunera i bezpieczne naprawy; pozycja jest dostępna wyłącznie na Pythonie 3.",
        "📦 Konfiguracja IPTV - zależności": "Instaluje wymagane zależności/biblioteki dla wtyczek IPTV.\nZalecane uruchomienie przed instalacją playerów IPTV.",

        # Softcam i Wtyczki
        "🔑 Softcam i Wtyczki": "Sekcja narzędzi CAM i instalatorów wtyczek.\nWybierz pozycję, aby zainstalować lub uruchomić daną funkcję.",
        "🔄 Restart Oscam": "Restartuje usługę Oscam (jeśli działa w systemie).\nPrzydatne po zmianie konfiguracji lub po zawieszeniu emulatora.",
        "🧹 Kasuj hasło Oscam": "Czyści hasło dostępu do WWW Oscam (jeśli jest ustawione).\nUłatwia odzyskanie dostępu do panelu bez reinstalacji.",
        "⚙️ oscam.dvbapi - kasowanie zawartości": "Czyści (kasuje zawartość) pliku oscam.dvbapi w konfiguracji Oscam.\nPrzydatne, gdy plik zawiera błędne wpisy lub chcesz zacząć od zera.",
        "⚙️ oscam.dvbapi - aktualizacja Poland": "Podmienia oscam.dvbapi na gotową konfigurację Poland dołączoną do AIO Panel.\nPrzed podmianą tworzy kopię starego pliku i próbuje odświeżyć usługę Softcam/Oscam.",
        "📥 Softcam - Instalator": "Uruchamia oficjalne polecenie feedu Softcam: wget -O - -q http://updates.mynonpublic.com/oea/feed | bash.\nNastępnie odświeża OPKG i umożliwia instalację OSCam.",
        "📥 OSCam-Emu - Instalator i aktywacja": "Preferuje OSCam-Emu z feedu, instaluje lub naprawczo przeinstalowuje pakiet, ustawia go jako aktywny softcam i sprawdza, czy proces faktycznie wystartował.\nLog diagnostyczny: /tmp/aio_oscam_install.log.",
        "📥 Oscam Levi45": "Instaluje Oscam Levi45 z oficjalnego instalatora Levi45Emulator.\nAIO pokazuje tylko nazwę Oscam Levi45 oraz wykryty numer lokalnej binarki, bez technicznej komendy w menu.",
        "📥 NCam 15.6 (Instalator)": "Instaluje NCam 15.6 z feedu/instalatora.\nPo instalacji zalecany restart GUI i wybór emu w ustawieniach Softcam.",
        "📥 NCam (Feed - najnowszy)": "Instaluje najnowszy NCam z feedu Twojego systemu (opkg).\nPo instalacji zalecany restart GUI i wybór emu w ustawieniach Softcam.",
        "⚙️ ServiceApp - Instalator": "Instaluje ServiceApp (alternatywny odtwarzacz) dla lepszej obsługi streamów IPTV.\nMoże wymagać restartu Enigma2 po instalacji.",
        "🛠 AJPanel - Instalator": "Instaluje AJPanel – zestaw narzędzi serwisowych i administracyjnych.\nPrzydatne do szybkiej diagnostyki i obsługi systemu.",
        "▶️ E2iPlayer Master - Instalacja/Aktualizacja": "Instaluje lub aktualizuje E2iPlayer (Master).\nDostarcza dostęp do wielu serwisów VOD/stream i narzędzi multimedialnych.",
        "📅 EPG Import - Instalator": "Instaluje EPGImport – automatyczny import programu TV.\nPo instalacji skonfiguruj źródła EPG i harmonogram aktualizacji.",
        "📻 NeoRadio Online - Instalator": "Instaluje NeoRadio Online z najnowszej paczki GitHub.\nPo instalacji wykonuje restart GUI, aby wtyczka była od razu widoczna.",
        "📺 Bouquet Maker Xtream - Instalator": "Instaluje Bouquet Maker Xtream 1.76-20260510 z archiwum GitHub.\nPo skopiowaniu plików wykonuje restart Enigma2, aby plugin był widoczny w menu.",
        "🔄 S4aUpdater - Instalator": "Instaluje S4aUpdater do aktualizacji wybranych dodatków.\nUłatwia utrzymanie wtyczek w aktualnej wersji bez ręcznej instalacji.",
        "🔄 MyUpdater v5.1 - Instalator": "Instaluje MyUpdater v5.1 z oficjalnego skryptu instalacyjnego.\nSłuży do aktualizacji i utrzymania dodatków bez ręcznego pobierania paczek.",
        "📺 JediMakerXtream - Instalator": "Instaluje JediMakerXtream do budowy bukietów IPTV z kont Xtream.\nPo instalacji dodaj dane logowania i wygeneruj listę/bukiety.",
        "▶️ YouTube - Instalator": "Instaluje wtyczkę YouTube dla Enigma2.\nMoże wymagać dodatkowych bibliotek zależnych od obrazu.",
        "📦 J00zeks Feed (Repo Installer)": "Dodaje repozytorium J00zeks (feed) do systemu.\nPo instalacji możesz pobierać jego wtyczki z poziomu Menedżera wtyczek.",
        "📺 E2Kodi v2 - Instalator (j00zek)": "Instaluje E2Kodi v2 (wersja z feedu j00zek).\nUmożliwia uruchomienie środowiska Kodi na Enigma2 (zależności zależą od obrazu).",
        "🖼️ Picon Updater - Instalator (Picony)": "Instaluje narzędzie do aktualizacji piconów.\nUłatwia pobieranie i odświeżanie ikon kanałów w systemie.",
        "📺 TV Garden - Instalator": "Instaluje TV Garden z oficjalnego skryptu Belfagor2005.\nPo zamknięciu konsoli AIO Panel zaproponuje pełny restart tunera dla pewnego startu wtyczki.",
        "🔎 Simple ZOOM Panel - Instalator": "Instaluje Simple ZOOM Panel z oficjalnego skryptu Belfagor2005.\nPo zamknięciu konsoli AIO Panel zaproponuje pełny restart tunera dla pewnego startu wtyczki.",

        # Narzędzia Systemowe
        "⚙️ Narzędzia Systemowe": "Zaawansowane narzędzia administracyjne systemu",
        "✨ Super Konfigurator (Pierwsza Instalacja)": "Asystent pierwszej konfiguracji tunera",
        ">>> Super Konfigurator (Pierwsza Instalacja)": "Automatyczna pierwsza konfiguracja tunera.\n\nWykonuje kolejno:\n- instalację listy kanałów (Polska 13E AIO Panel)\n- instalację obsługi Softcam\n- instalację OSCam-Emu, ustawienie jako aktywny softcam i uruchomienie\n- pobranie piconów (Transparent)\nNa końcu przeładowuje listę kanałów. Restart GUI wykonujesz ręcznie tylko wtedy, gdy jest potrzebny.",
        "🗑️ Menadżer Deinstalacji": "Odinstalowywanie pakietów z systemu",
        "🔎 Sprawdź aktualizacje zainstalowanych wtyczek": "Sprawdza zainstalowane wtyczki i pokazuje dwie sekcje aktualizacji: OPKG oraz GitHub/Custom.\nPozwala uruchomić aktualizację tylko dla pozycji, dla których wykryto nowszą wersję.",
        "📡 Aktualizuj satellites.xml": "Pobiera i aktualizuje satellites.xml w systemie.\nPrzydatne przy dodawaniu nowych transponderów; zalecany restart Enigmy2.",
        "🖼️ Pobierz Picony (Transparent)": "Pobiera zestaw piconów (transparent) obejmujący 13E, 19.2E oraz IPTV i przed instalacją pyta o katalog docelowy.\nMożesz wybrać lokalizację domyślną albo urządzenie zewnętrzne; po zakończeniu zalecany jest restart GUI lub pełny restart przy większych zmianach.",
        "📊 Monitor Systemowy": "Podgląd wykorzystania CPU, RAM, temperatury",
        "📄 Przeglądarka Logów": "Przeglądanie logów systemowych i Enigmy2",
        "⏰ Menedżer Cron": "Zarządzanie zadaniami harmonogramu",
        "🔌 Menedżer Usług": "Zarządzanie usługami systemowymi (SSH, FTP itd.)",
        "ℹ️ Informacje o Systemie": "Szczegółowe informacje o sprzęcie i oprogramowaniu",
        "🔄 Aktualizuj oscam.srvid/srvid2": "Aktualizacja listy identyfikatorów kanałów",
        "🔑 Aktualizuj SoftCam.Key (Online)": "Pobiera i aktualizuje plik SoftCam.Key (Online) w typowych lokalizacjach kluczy.\nPo zakończeniu wykonuje restart emulatora (jeśli uruchomiony).",
        "🌐 Menedżer Feedów / Repozytoriów": "Menedżer repozytoriów opkg. Pozwala podejrzeć aktywne feedy, wykonać test połączenia z feedami, wyczyścić cache list pakietów i odświeżyć repozytoria.",
        "🛠 Tryb Naprawy po Instalacji": "Uruchamia zestaw naprawczy po instalacji dodatków lub po nieudanym update. Dostępne moduły: uprawnienia, Softcam, EPG, picony, ServiceApp i Streamlink oraz tryb pełny.",
        "💾 Backup Listy Kanałów": "Tworzy pełną kopię list kanałów: lamedb/lamedb5, bouquets.tv/radio, wszystkie userbouquet TV/Radio i pliki pomocnicze.\nBackup zapisuje się na HDD/USB w katalogu aio_backups.",
        "💾 Backup Konfiguracji Oscam": "Kopia zapasowa konfiguracji Oscam",
        "♻️ Restore Listy Kanałów": "Przywraca pełną kopię list kanałów z aio_channels_backup.tar.gz.\nDla poprawnego odtworzenia bukietów zatrzymuje Enigma2, czyści stare pliki list i uruchamia GUI ponownie.",
        "♻️ Restore Konfiguracji Oscam": "Przywracanie konfiguracji Oscam z backupu",

        # Info i Diagnostyka
        "ℹ️ Info i Diagnostyka": "Informacje o wtyczce i narzędzia diagnostyczne",
        "ℹ️ Informacje o AIO Panel": "Informacje o wersji, licencji i autorze",
        "🔄 Aktualizacja Wtyczki": "Sprawdzenie i instalacja aktualizacji AIO Panel",
        "🔔 Dostępna aktualizacja AIO": "Informacja o wykrytej aktualizacji AIO Panel. Kliknij pozycję aktualizacji w zakładce Informacje i Aktualizacje, aby zobaczyć listę zmian oraz wybrać TAK/NIE.",
        "⭐ AIO Szybki Start / Polecane": "Nowa, atrakcyjna sekcja startowa z polecanymi akcjami i skrótami do najważniejszych funkcji AIO Panel.",
        "🧪 Test zgodności systemu": "Generuje lokalny raport zgodności: Python, narzędzia systemowe, certyfikaty CA, pamięć flash i podstawowe zależności AIO.",
        "💡 Tip dnia AIO": "Wyświetla praktyczną wskazówkę dnia dotyczącą obsługi AIO Panel i konserwacji systemu.",
        "📜 Lokalny changelog": "Otwiera lokalny changelog z paczki wtyczki – działa także wtedy, gdy GitHub jest chwilowo niedostępny.",
        "🌐 Diagnostyka Sieci": "Test prędkości i parametrów połączenia internetowego",
        "💾 Wolne miejsce (dysk/flash)": "Informacja o wykorzystaniu pamięci",
        "⏱️ Auto RAM Cleaner (Konfiguruj)": "Automatyczne czyszczenie pamięci RAM",
        "🧹 Wyczyść Pamięć Tymczasową": "Usunięcie plików tymczasowych z /tmp",
        "🧹 Smart Cleanup (TMP/LOG/CACHE)": "Bezpieczne czyszczenie zbędnych archiwów, crashlogów i logów tymczasowych oraz odświeżenie cache RAM.\nPomaga odzyskać miejsce bez naruszania ustawień użytkownika.",
        "🧹 Wyczyść Pamięć RAM": "Ręczne czyszczenie pamięci RAM",
        "🔑 Kasuj hasło FTP": "Usuwa hasło użytkownika root (FTP/SSH).\nPo wykonaniu logowanie odbywa się bez hasła (jeśli obraz na to pozwala).",
        "🔑 Ustaw Hasło FTP": "Ustawia nowe hasło dla użytkownika root (FTP/SSH).\nZwiększa bezpieczeństwo dostępu do tunera z sieci.",
    },
    "EN": {
        # Channel Lists
        "📺 Channel Lists": "Manage channel lists: install, update and restore.\nIncludes IPTV list import (M3U) and safe rollback to the previous state.",
        "📡 Paweł Pawełek HB 13E (04.01.2026)": "Official channel list for HotBird 13E.\nInstalls the bouquets and refreshes the Enigma2 channel lists automatically.",
        "📺 XStreamity - Installer": "Installs XStreamity (IPTV).\nSupports M3U and Xtream Codes; launch it from the Plugins menu after install.",
        "📺 IPTV Dream - Installer": "Installs IPTV Dream (advanced IPTV player).\nIf needed, install IPTV dependencies from the dedicated dependencies entry.",
        "🩺 E2 Doctor - Installer (Python 3)": "Installs E2 Doctor from the author’s official repository.\nThe plugin provides receiver diagnostics and safe repairs; this entry is available on Python 3 only.",
        "📦 IPTV Configuration - dependencies": "Installs required IPTV packages/libraries.\nRecommended to run before installing IPTV players.",

        # Softcam & Plugins
        "🔑 Softcam & Plugins": "CAM/tools and plugin installers section.\nSelect an item to install, update or run the selected function.",
        "🔄 Restart Oscam": "Restarts the Oscam service (if available on your image).\nUseful after config changes or when the emulator becomes unresponsive.",
        "🧹 Clear Oscam Password": "Clears the Oscam WebIF password (if configured).\nHelps regain panel access without reinstalling.",
        "⚙️ oscam.dvbapi - clear file": "Clears/truncates the oscam.dvbapi file in Oscam config directories.\nUseful if the file contains wrong entries or you want a clean start.",
        "⚙️ oscam.dvbapi - Poland update": "Replaces oscam.dvbapi with the bundled Poland profile from AIO Panel.\nCreates a backup of the previous file and tries to refresh Softcam/Oscam afterwards.",
        "📥 Softcam - Installer": "Runs the official Softcam feed command: wget -O - -q http://updates.mynonpublic.com/oea/feed | bash.\nThen refreshes OPKG and enables OSCam installation.",
        "📥 OSCam-Emu - Install and activate": "Prefers OSCam-Emu from the feed, installs or repairs the package, selects it as the active softcam and verifies that the process is actually running.\nDiagnostic log: /tmp/aio_oscam_install.log.",
        "📥 NCam 15.6 (Installer)": "Installs NCam 15.6 via feed/installer.\nGUI restart recommended; then select the emulator in Softcam settings.",
        "📥 NCam (Feed - latest)": "Installs the latest NCam from your system feed (opkg).\nGUI restart recommended; then select the emulator in Softcam settings.",
        "⚙️ ServiceApp - Installer": "Installs ServiceApp (alternative playback engine) for improved IPTV/stream handling.\nMay require Enigma2 restart after installation.",
        "🛠 AJPanel - Installer": "Installs AJPanel – a set of service/administration tools.\nUseful for quick maintenance and diagnostics.",
        "▶️ E2iPlayer Master - Install/Update": "Installs or updates E2iPlayer (Master).\nProvides access to multiple streaming/VOD sources and media tools.",
        "📅 EPG Import - Installer": "Installs EPGImport for automatic EPG data import.\nAfter install, set sources and schedule periodic updates.",
        "📻 NeoRadio Online - Installer": "Installs NeoRadio Online from the latest GitHub package.\nAfter installation it restarts the GUI so the plugin appears immediately.",
        "📺 Bouquet Maker Xtream - Installer": "Installs Bouquet Maker Xtream 1.76-20260510 from the GitHub archive.\nAfter copying files it restarts Enigma2 so the plugin appears in the menu.",
        "🔄 S4aUpdater - Installer": "Installs S4aUpdater to keep selected add-ons up to date.\nReduces manual package installs/updates.",
        "🔄 MyUpdater v5.1 - Installer": "Installs MyUpdater v5.1 using the official installer script.\nHelps keep selected add-ons updated without manual package downloads.",
        "📺 JediMakerXtream - Installer": "Installs JediMakerXtream to build IPTV bouquets from Xtream accounts.\nAdd your credentials and generate bouquets after installation.",
        "▶️ YouTube - Installer": "Installs the YouTube plugin for Enigma2.\nRequired dependencies vary by image.",
        "📦 J00zeks Feed (Repo Installer)": "Adds the J00zek feed repository to your system.\nAfterwards, install his plugins via the Plugin Manager.",
        "📺 E2Kodi v2 - Installer (j00zek)": "Installs E2Kodi v2 (j00zek build).\nLets you run Kodi on Enigma2; dependencies vary by image.",
        "🖼️ Picon Updater - Installer (Picons)": "Installs a picon update utility.\nHelps download and refresh channel icons on the receiver.",
        "📺 TV Garden - Installer": "Installs TV Garden using the official Belfagor2005 script.\nAfter the console closes, AIO Panel offers a full receiver reboot for a cleaner first start.",
        "🔎 Simple ZOOM Panel - Installer": "Installs Simple ZOOM Panel using the official Belfagor2005 script.\nAfter the console closes, AIO Panel offers a full receiver reboot for a cleaner first start.",

        # System Tools
        "⚙️ System Tools": "Advanced system administration tools",
        "✨ Super Setup Wizard (First Installation)": "First time tuner setup assistant",
        ">>> Super Setup Wizard (First Installation)": "Automatic first-time receiver setup.\n\nRuns in order:\n- install channel list (Polska 13E AIO Panel)\n- install Softcam support\n- install OSCam-Emu, select it as the active softcam and start it\n- download picons (Transparent)\nFinally reloads the channel list. Restart the GUI manually only if required.",
        "🗑️ Uninstallation Manager": "Uninstall packages from system",
        "📡 Update satellites.xml": "Downloads and updates satellites.xml in your system.\nRecommended after changes: restart Enigma2 for full effect.",
        "🖼️ Download Picons (Transparent)": "Downloads a transparent picon set covering 13E, 19.2E and IPTV, then asks for the target folder before installation.\nYou can keep the default path or choose an external device; GUI restart or a full reboot is recommended after larger changes.",
        "📊 System Monitor": "View CPU, RAM, temperature usage",
        "📄 Log Viewer": "Browse system and Enigma2 logs",
        "⏰ Cron Manager": "Manage scheduled tasks",
        "🔌 Service Manager": "Manage system services (SSH, FTP, etc.)",
        "ℹ️ System Information": "Detailed hardware and software info",
        "🔄 Update oscam.srvid/srvid2": "Update channel identifier list",
        "🔑 Update SoftCam.Key (Online)": "Downloads and updates SoftCam.Key (Online) to common key/config locations.\nRestarts the emulator (if running).",
        "🌐 Feed / Repository Manager": "Opkg repository manager. Lets you inspect active feeds, test feed connectivity, clear package-list cache and refresh repositories.",
        "🛠 Post-Install Repair Mode": "Runs a post-install repair toolkit after a failed install/update. Available modules: permissions, Softcam, EPG, picons, ServiceApp and Streamlink, plus a full repair mode.",
        "💾 Backup Channel List": "Creates a complete channel-list backup: lamedb/lamedb5, bouquets.tv/radio, all TV/Radio userbouquets and helper files.\nThe backup is saved to aio_backups on HDD/USB.",
        "💾 Backup Oscam Config": "Backup Oscam configuration",
        "♻️ Restore Channel List": "Restores the complete channel-list backup from aio_channels_backup.tar.gz.\nTo restore bouquets reliably it stops Enigma2, clears old list files and starts the GUI again.",
        "♻️ Restore Oscam Config": "Restore Oscam config from backup",

        # Info & Diagnostics
        "ℹ️ Info & Diagnostics": "Plugin info and diagnostic tools",
        "ℹ️ About AIO Panel": "Version, license and author info",
        "🔄 Update Plugin": "Check and install AIO Panel updates",
        "🔔 AIO update available": "AIO Panel update notification. Open the update item in Info & Updates to view the changelog and choose YES/NO.",
        "⭐ AIO Quick Start / Recommended": "New welcome section with recommended actions and shortcuts to the most useful AIO Panel functions.",
        "🧪 System compatibility check": "Builds a local compatibility report: Python, system tools, CA certificates, flash space and core AIO dependencies.",
        "💡 AIO tip of the day": "Shows a practical daily tip for using AIO Panel and keeping the receiver in good shape.",
        "📜 Local changelog": "Opens the bundled local changelog – useful when GitHub is temporarily unreachable.",
        "🌐 Network Diagnostics": "Internet speed and connection test",
        "💾 Free Space (disk/flash)": "Memory usage information",
        "⏱️ Auto RAM Cleaner (Setup)": "Automatic RAM cleaning",
        "🧹 Clear Temporary Cache": "Remove temporary files from /tmp",
        "🧹 Smart Cleanup (TMP/LOG/CACHE)": "Safely removes leftover archives, crashlogs and temporary logs, then refreshes RAM cache.\nHelps recover space without touching user settings.",
        "🧹 Clear RAM Cache": "Manual RAM cache clearing",
        "🔑 Clear FTP Password": "Removes the root password (FTP/SSH).\nAfterwards, login may be passwordless (depends on image security settings).",
        "🔑 Set FTP Password": "Sets a new password for the root user (FTP/SSH).\nImproves security for network access to the receiver.",
    }
}
# === KONIEC OPISÓW FUNKCJI ===

# === NOWA KLASA WYBORU Z OPISEM (DLA WIZARDA) ===
class SuperWizardChoiceScreen(Screen):
    skin = _super_wizard_choice_skin()

    def __init__(self, session, options, title="Wybierz opcję", description_map=None):
        Screen.__init__(self, session)
        self.session = session
        self.setTitle(title)
        
        self.options = options
        self.description_map = description_map or {}
        
        self["list"] = MenuList(self.options)
        self["description"] = Label("Wybierz opcję...")
        self["actions"] = Label("OK - Wybierz | EXIT - Anuluj")
        
        self["my_actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "ok": self.ok_pressed,
            "cancel": self.cancel_pressed,
            "up": self.move_up,
            "down": self.move_down
        }, -1)
        
        self.onShown.append(self.update_description)

    def move_up(self):
        self["list"].up()
        self.update_description()

    def move_down(self):
        self["list"].down()
        self.update_description()

    def update_description(self):
        cur = self["list"].getCurrent()
        if cur:
            # cur = ("Label", "key")
            key = cur[1]
            desc = self.description_map.get(key, "")
            self["description"].setText(desc)

    def ok_pressed(self):
        cur = self["list"].getCurrent()
        if cur:
            self.close(cur)
    
    def cancel_pressed(self):
        self.close(None)



class PanelAIO(Screen):
    # Modern Dashboard UI v9.5 (adaptive HD/FHD layout)
    skin = _panel_main_skin()

    def __init__(self, session, fetched_data):
        Screen.__init__(self, session)
        # Force our own internal skin name. Some external skins define a generic
        # screen named "Panel"; without this, the dashboard can open but remain invisible.
        self.skinName = getattr(self, "modern_skin_name", ["PanelAIO"])
        self.setTitle("Panel AIO " + VER)
        self.sess = session
        self.lang = 'PL'
        try:
            saved_lang = config.plugins.panelaio.language.value if config is not None and hasattr(config.plugins.panelaio, 'language') else 'auto'
            if saved_lang in ('PL', 'EN'):
                self.lang = saved_lang
        except Exception:
            pass
        
        # Logika detekcji obrazu
        self.image_type = "unknown"
        if fileExists("/etc/issue"):
            try:
                with open("/etc/issue", "r") as f:
                    issue_content = f.read()
                if "Hyperion" in issue_content:
                    self.image_type = "hyperion"
            except Exception: pass
        if self.image_type == "unknown" and fileExists("/etc/image-version"):
            try:
                with open("/etc/image-version", "r") as f:
                    img_info = f.read().lower()
                if "openatv" in img_info: self.image_type = "openatv"
                elif "openpli" in img_info: self.image_type = "openpli"
            except Exception: pass
        if self.image_type == "unknown" and fileExists("/etc/vtiversion.info"):
            self.image_type = "vti"

        self.fetched_data_cache = fetched_data
        self.update_info = None
        self.update_prompt_shown = False
        
        # Tabs (left sidebar) are built dynamically from menu sections (separators).
        # This gives each subcategory its own tab (e.g. Softcamy / Wtyczki Online / Backup & Restore ...).
        self.active_tab = 0
        self.tabs = []  # list of (title, items)

        self["qr_code_small"] = Pixmap()
        self["pp_logo"] = Pixmap()
        self["support_label"] = Label(TRANSLATIONS[self.lang]["support_text"])
        self["title_label"] = Label("AIO Panel " + VER)
        self["tabs_display"] = Label("") 
        self["menu"] = MenuList([])
        self["sidebar"] = MenuList([])
        self["health"] = Label("")
        self["update_status"] = Label("")
        self._focus = "menu"
        self._prev_cpu = None

        # selection callbacks
        try:
            self["sidebar"].onSelectionChanged.append(self._on_sidebar_changed)
        except Exception:
            pass
        try:
            self["menu"].onSelectionChanged.append(self.update_function_description)
        except Exception:
            pass

        # health timer
        self._closed = False
        self._health_timer = eTimer()
        try:
            self._health_timer_conn = self._health_timer.timeout.connect(self._update_health)
        except Exception:
            self._health_timer.callback.append(self._update_health)
        self.onShown.append(self._start_health_timer)
        self.onClose.append(self._stop_health_timer)
        self.onLayoutFinish.append(self._apply_focus)
        self["function_description"] = Label("") # Tooltip z opisem funkcji
        self["legend"] = Label(" ") 
        self["footer"] = Label(FOOT)
        self["act"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "ChannelUpDownActions", "ChannelSelectBaseActions", "NumberActions", "HelpActions", "InfoActions"], {
            "ok": self.ok_pressed,
            "cancel": self.close,
            "red": lambda: self.set_language('PL'),
            "green": lambda: self.set_language('EN'),
            "yellow": self.restart_gui,
            "blue": self.check_for_updates_manual,
            "info": self.open_support,
            "left": self.focus_sidebar,
            "right": self.focus_menu,
            "up": self.menu_up,
            "down": self.menu_down,
            # extra navigation / compatibility
            "channelUp": self.next_tab,
            "channelDown": self.prev_tab,
            "nextBouquet": self.next_tab,
            "prevBouquet": self.prev_tab,
            "displayHelp": self.open_support,
            "showEventInfo": self.open_support,
            "1": lambda: self.switch_tab(0),
            "2": lambda: self.switch_tab(1),
            "3": lambda: self.switch_tab(2),
            "4": lambda: self.switch_tab(3)
        }, -1)
        
        self.onShown.append(self.post_initial_setup)
        self.onExecBegin.append(self._on_exec_begin)
        self.set_language(self.lang) 

    # --- FUNKCJE ZAKŁADEK ---
    def next_tab(self):
        if not self.tabs:
            return
        new_tab_index = (self.active_tab + 1) % len(self.tabs)
        self.switch_tab(new_tab_index)

    def prev_tab(self):
        if not self.tabs:
            return
        new_tab_index = (self.active_tab - 1) % len(self.tabs)
        self.switch_tab(new_tab_index)

    def switch_tab(self, tab_index):
        if not self.tabs:
            self.active_tab = 0
            self["menu"].setList([])
            self["function_description"].setText("")
            return

        # clamp
        if tab_index < 0:
            tab_index = 0
        if tab_index >= len(self.tabs):
            tab_index = len(self.tabs) - 1

        self.active_tab = tab_index
        try:
            self["sidebar"].setIndex(self.active_tab)
        except Exception:
            pass

        # Hide legacy tabs display (kept for compatibility)
        try:
            self["tabs_display"].setText("")
        except Exception:
            pass

        items = self.tabs[self.active_tab][1]
        self["menu"].setList([ensure_str(item[0]) for item in items] if items else [])
        self.update_function_description()
        self._apply_focus()
    def update_function_description(self):
        """Aktualizuje opis funkcji na podstawie zaznaczonego elementu"""
        try:
            data_list = self.tabs[self.active_tab][1] if self.tabs and self.active_tab < len(self.tabs) else []
            if not data_list:
                self["function_description"].setText("")
                return

            selected_index = self["menu"].getSelectionIndex()
            if selected_index is None or selected_index >= len(data_list):
                self["function_description"].setText("")
                return

            item = data_list[selected_index]
            if not item or len(item) < 1:
                self["function_description"].setText("")
                return

            # Pobierz nazwę funkcji
            func_name = str(item[0])

            # Sprawdź czy to separator
            if len(item) > 1 and item[1] == "SEPARATOR":
                self["function_description"].setText("")
                return

            # Pobierz opis z słownika
            descriptions = FUNCTION_DESCRIPTIONS.get(self.lang, FUNCTION_DESCRIPTIONS["PL"])
            description = descriptions.get(func_name, "")

            # Jeśli nie ma dokładnego dopasowania, spróbuj znaleźć podobny
            if not description:
                # Spróbuj dopasować po początku stringa (bez emoji)
                try:
                    # Dla Py3 emoji to znaki unicode
                    clean_name = func_name
                    # Prosta pętla czyszcząca
                    for em in ['📺','📡','🔑','⚙️','ℹ️','🔄','🧹','💾','♻️','🗑️','📊','📄','⏰','🔌','✨','🌐','⏱️','🖼️','🛠','▶️','📅','📦']:
                        if IS_PY3:
                             clean_name = clean_name.replace(em, '')
                        else:
                             # W Py2 emoji to bajty, trudniej usuwać bez biblioteki regex/emoji
                             pass 
                    description = descriptions.get(clean_name.strip(), "")
                except Exception:
                    pass

            self["function_description"].setText(description)

        except Exception as e:
            # W przypadku błędu po prostu wyczyść opis
            self["function_description"].setText("")

    def menu_up(self):
        """Nawigacja UP zgodna z focusem (sidebar/content)."""
        if getattr(self, "_focus", "menu") == "sidebar":
            try:
                self["sidebar"].up()
            except Exception:
                pass
            self._on_sidebar_changed()
            return
        try:
            self["menu"].up()
        except Exception:
            pass
        self.update_function_description()
    def menu_down(self):
        """Nawigacja DOWN zgodna z focusem (sidebar/content)."""
        if getattr(self, "_focus", "menu") == "sidebar":
            try:
                self["sidebar"].down()
            except Exception:
                pass
            self._on_sidebar_changed()
            return
        try:
            self["menu"].down()
        except Exception:
            pass
        self.update_function_description()
    def set_language(self, lang):
        self.lang = lang if lang in ('PL', 'EN') else 'PL'
        try:
            if config is not None and hasattr(config.plugins.panelaio, 'language'):
                config.plugins.panelaio.language.value = self.lang
                config.plugins.panelaio.language.save()
                if configfile is not None: configfile.save()
        except Exception as exc:
            print('[AIO Panel] language save:', exc)
        self.set_lang_headers_and_legends()
        
        try:
            repo_lists = self.fetched_data_cache.get("repo_lists", [])
            s4a_lists_full = self.fetched_data_cache.get("s4a_lists_full", [])
            best_oscam_version = self.fetched_data_cache.get("best_oscam_version", "Error")
            local_oscam_version = self.fetched_data_cache.get("local_oscam_version", "Online")

            if not repo_lists:
                repo_lists = [(TRANSLATIONS[lang]["loading_error_text"] + " (REPO)", "SEPARATOR")]
            
            # v14.0.0: repo + wszystkie datowane listy S4a z ostatnich 12 miesięcy;
            # Bzyk83 jest wykluczony globalnie, a kolejność pozostaje datowa.
            final_channel_lists = _prepare_channel_lists_v1201(repo_lists, s4a_lists_full)
            
            softcam_menu = list(SOFTCAM_AND_PLUGINS_PL if lang == 'PL' else SOFTCAM_AND_PLUGINS_EN)
            tools_menu = list(SYSTEM_TOOLS_PL if lang == 'PL' else SYSTEM_TOOLS_EN)
            diag_menu = list(DIAGNOSTICS_PL if lang == 'PL' else DIAGNOSTICS_EN)
            if self.update_info:
                try:
                    up_ver = ensure_unicode(self.update_info.get("version", "")).strip()
                    label = TRANSLATIONS[lang]["update_menu_label"].format(ver=up_ver)
                    insert_at = 1 if diag_menu and diag_menu[0][1] == "SEPARATOR" else 0
                    diag_menu.insert(insert_at, (label, "CMD:SHOW_PENDING_AIO_UPDATE"))
                except Exception:
                    pass
            
            # --- FILTROWANIE DLA PYTHON 2 (Kompatybilność) ---
            if IS_PY2:
                 softcam_filtered = []
                 for item in softcam_menu:
                      name, cmd = item
                      # Blokuj wtyczki, które działają tylko na Py3 lub są zbyt ciężkie dla starych boxów
                      if "E2Kodi" in name or cmd == "CMD:INSTALL_E2KODI": continue
                      if "XStreamity" in name: continue # Wersje Py2 rzadko wspierane
                      if "E2 Doctor" in name: continue # E2 Doctor wymaga Python 3
                      softcam_filtered.append(item)
                 softcam_menu = softcam_filtered

            # Filtrowanie dla Hyperion/VTi
            if self.image_type in ["hyperion", "vti"]:
                emu_actions_to_block = ["CMD:RESTART_OSCAM", "CMD:CLEAR_OSCAM_PASS", "CMD:MANAGE_DVBAPI", "CMD:UPDATE_DVBAPI_POLAND", "CMD:INSTALL_SOFTCAM_SCRIPT", "CMD:INSTALL_BEST_OSCAM", "CMD:INSTALL_LEVI45_OSCAM"]
                softcam_menu_filtered = []
                for (name, action) in softcam_menu:
                    if action not in emu_actions_to_block: softcam_menu_filtered.append((name, action))
                softcam_menu = softcam_menu_filtered
                
                tools_menu_filtered = []
                for (name, action) in tools_menu:
                    if action != "CMD:SUPER_SETUP_WIZARD": tools_menu_filtered.append((name, action))
                tools_menu = tools_menu_filtered
            
            for i, (name, action) in enumerate(softcam_menu):
                if action == "CMD:INSTALL_BEST_OSCAM":
                    oscam_text = "📥 OSCam-Emu - {}" if lang == 'PL' else "📥 OSCam-Emu - {}"
                    softcam_menu[i] = (oscam_text.format(best_oscam_version), action)
                elif action == "CMD:INSTALL_LEVI45_OSCAM":
                    levi_ver = local_oscam_version or "Online"
                    softcam_menu[i] = ("📥 Oscam Levi45 - {}".format(levi_ver), action)
            
            for i, (name, action) in enumerate(tools_menu):
                if action == "CMD:SUPER_SETUP_WIZARD":
                    tools_menu[i] = (TRANSLATIONS[lang]["sk_wizard_title"], action)
                elif action == "CMD:TOGGLE_MENU_VISIBILITY":
                    enabled = _get_show_in_menu_setting(True)
                    state = "ON" if enabled else "OFF"
                    if lang == 'PL':
                        tools_menu[i] = ("👁️ Widoczność w menu tunera: %s" % state, action)
                    else:
                        tools_menu[i] = ("👁️ Show in receiver menu: %s" % state, action)

            # Build sidebar tabs from subcategories (SEPARATOR sections)
            tabs = []
            # 1) Channel lists (single tab)
            tabs.append((COL_TITLES[lang][0], final_channel_lists))

            # 2) Softcam & Plugins (split)
            for sec_title, sec_items in self._split_sections(softcam_menu, COL_TITLES[lang][1]):
                tabs.append((sec_title, sec_items))

            # 3) System tools (split)
            for sec_title, sec_items in self._split_sections(tools_menu, COL_TITLES[lang][2]):
                tabs.append((sec_title, sec_items))

            # 3b) Skins / Skórki (single tab)
            skins_menu = list(SKINS_PL if lang == 'PL' else SKINS_EN)
            for sec_title, sec_items in self._split_sections(skins_menu, 'Skins / Skórki' if lang == 'PL' else 'Skins'):
                tabs.append((sec_title, sec_items))

            # 4) Info/Diagnostics (split)
            for sec_title, sec_items in self._split_sections(diag_menu, COL_TITLES[lang][3]):
                tabs.append((sec_title, sec_items))

            self._set_sidebar_tabs(tabs)
            self.switch_tab(self.active_tab)
            
        except Exception as e:
            print("[AIO Panel] Błąd danych:", e)
            self._set_sidebar_tabs([(COL_TITLES[self.lang][0], [(TRANSLATIONS[self.lang]["loading_error_text"], "SEPARATOR")])])
            self.switch_tab(0)
            self.update_function_description()

    def set_lang_headers_and_legends(self):
        self["legend"].setText(LEGEND_PL_COLOR if self.lang == 'PL' else LEGEND_EN_COLOR)
        self["support_label"].setText(TRANSLATIONS[self.lang]["support_text"])
        # Sidebar tabs are built dynamically in set_language(); here we only update labels.
        try:
            self["footer"].setText(FOOT)
        except Exception:
            pass


    # --- Modern Dashboard helpers (focus/sidebar/health/QR) ---

    def open_support(self):
        try:
            self.sess.open(AIOSupportScreen)
        except Exception:
            pass

    def open_aio_quickstart(self):
        lang = self.lang
        options = [
            (("🪄 1) Sprawdź aktualizacje i changelog" if lang == "PL" else "🪄 1) Check updates and changelog"), "updates"),
            (("📊 2) Monitor systemowy" if lang == "PL" else "📊 2) System monitor"), "sysmon"),
            (("🌐 3) Diagnostyka sieci" if lang == "PL" else "🌐 3) Network diagnostics"), "netdiag"),
            (("🌐 4) Menedżer feedów" if lang == "PL" else "🌐 4) Feed manager"), "feeds"),
            (("🛠 5) Tryb naprawy" if lang == "PL" else "🛠 5) Post-install repair"), "repair"),
            (("💡 6) Tip dnia AIO" if lang == "PL" else "💡 6) AIO tip of the day"), "tip"),
            (("📜 7) Lokalny changelog" if lang == "PL" else "📜 7) Local changelog"), "changelog"),
            (("[X] Powrót" if lang == "PL" else "[X] Back"), "cancel")
        ]
        desc_map = {
            "updates": ("Szybkie wejście do informacji o wersji i aktualizacji wtyczki." if lang == "PL" else "Quick access to plugin version info and update workflow."),
            "sysmon": ("Podgląd CPU, RAM, temperatury i dysków." if lang == "PL" else "CPU, RAM, temperature and disk overview."),
            "netdiag": ("Test połączenia, DNS, ping oraz transfer." if lang == "PL" else "Connectivity, DNS, ping and transfer test."),
            "feeds": ("Zarządzanie repozytoriami opkg i test feedów." if lang == "PL" else "Manage opkg repositories and feed connectivity."),
            "repair": ("Naprawa typowych problemów po instalacji dodatków." if lang == "PL" else "Repair common issues after plugin/package installs."),
            "tip": ("Krótka praktyczna wskazówka dla użytkownika AIO Panel." if lang == "PL" else "A short practical tip for AIO Panel users."),
            "changelog": ("Lokalna lista zmian dostępna nawet offline." if lang == "PL" else "Bundled changelog available even offline."),
            "cancel": ("Powrót do panelu głównego." if lang == "PL" else "Return to the main panel.")
        }
        title = ("⭐ AIO Szybki Start" if lang == "PL" else "⭐ AIO Quick Start")
        py_mode = "Py3" if IS_PY3 else "Py2"
        title = "{} | {} | {}".format(title, self.image_type, py_mode)
        self.sess.openWithCallback(self._aio_quickstart_selected, SuperWizardChoiceScreen, options=options, title=title, description_map=desc_map)

    def _aio_quickstart_selected(self, choice):
        if not choice:
            return
        key = choice[1]
        if key == "cancel":
            return
        elif key == "updates":
            self.show_info_screen()
        elif key == "sysmon":
            self.open_system_monitor()
        elif key == "netdiag":
            self.run_network_diagnostics()
        elif key == "feeds":
            self.open_feed_manager()
        elif key == "repair":
            self.open_postinstall_repair()
        elif key == "tip":
            self.show_aio_tip()
        elif key == "changelog":
            self.show_local_changelog()

    def show_aio_tip(self):
        tips = _get_aio_tips(self.lang)
        idx = _pick_tip_index(len(tips))
        self.sess.open(AIOTipPopupScreen, self.lang, tips, idx)

    def show_local_changelog(self):
        content = _read_text_file(os.path.join(PLUGIN_PATH, "changelog.txt"), "Brak pliku changelog.txt")
        title = "Lokalny changelog AIO Panel" if self.lang == "PL" else "Local AIO Panel changelog"
        self.sess.open(AIOTextViewerScreen, title, content, "▲/▼ Scroll  OK/EXIT=Back")

    def open_compatibility_check(self):
        title = "Test zgodności systemu" if self.lang == "PL" else "System compatibility check"
        report = _build_compat_report(self.lang, self.image_type)
        self.sess.open(AIOTextViewerScreen, title, report, "▲/▼ Scroll  OK/EXIT=Back")

    def _on_exec_begin(self):
        """Restore focus/highlight when returning from child screens."""
        try:
            self._apply_focus()
        except Exception:
            pass
        try:
            self.update_function_description()
        except Exception:
            pass

    def focus_sidebar(self):
        self._focus = "sidebar"
        self._apply_focus()

    def focus_menu(self):
        self._focus = "menu"
        self._apply_focus()

    def _set_selection_enable(self, widget, enable):
        """Compatibility: enable/disable selection highlight across images."""
        val = 1 if enable else 0
        for obj in (getattr(widget, "instance", None), getattr(widget, "l", None), widget):
            if obj is None:
                continue
            for meth in ("setSelectionEnable", "setSelectionEnabled"):
                try:
                    fn = getattr(obj, meth, None)
                    if fn:
                        fn(val)
                        return True
                except Exception:
                    pass
        return False

    def _apply_focus(self):
        """Ensure only the active list shows selection highlight."""
        try:
            if getattr(self, "_focus", "menu") == "sidebar":
                self._set_selection_enable(self["sidebar"], True)
                self._set_selection_enable(self["menu"], False)
            else:
                self._set_selection_enable(self["menu"], True)
                self._set_selection_enable(self["sidebar"], False)
        except Exception:
            pass

    def ok_pressed(self):
        # OK on sidebar => go to content; OK on content => execute
        if getattr(self, "_focus", "menu") == "sidebar":
            self.focus_menu()
            return
        return self.run_with_confirmation()


    def _get_list_index(self, widget):
        """Compatibility helper: returns current selection index for MenuList across images."""
        for m in ("getSelectionIndex", "getSelectedIndex"):
            try:
                fn = getattr(widget, m, None)
                if fn:
                    i = fn()
                    if i is not None:
                        return i
            except Exception:
                pass
        try:
            return widget.l.getCurrentSelectionIndex()
        except Exception:
            return 0

    
    def _format_tab_title(self, title):
        """Unified sidebar tab rendering."""
        try:
            t = self._clean_section_title(title)
        except Exception:
            t = ensure_unicode(title)
        t = t.strip()
        # Make every tab look like a section header
        return ensure_str("--- %s ---" % ensure_unicode(t))

    def _strip_color_codes(self, s):
        try:
            txt = ensure_unicode(s)
            return re.sub(u"\\\\c[0-9A-Fa-f]{8}", u"", txt)
        except Exception:
            try:
                return re.sub(r"\\c[0-9A-Fa-f]{8}", "", s)
            except Exception:
                return s

    def _clean_section_title(self, raw_title):
        r"""Convert separator titles like '\c00FFD200--- Softcamy ---\c00ffffff' into 'Softcamy'."""
        t = self._strip_color_codes(ensure_unicode(raw_title))
        t = t.replace("—", "-")
        # remove leading/trailing dashes and whitespace
        t = t.strip().strip("-").strip()
        # common pattern: '--- Something ---'
        t = re.sub(r"^[- ]+", "", t)
        t = re.sub(r"[- ]+$", "", t)
        return t.strip()

    def _split_sections(self, items, fallback_title):
        """Split a flat menu (with SEPARATOR rows) into sections.

        Returns list of (section_title, section_items) where section_items contain only actionable items.
        """
        sections = []
        current_title = None
        current_items = []
        for entry in items:
            try:
                name, action = entry
            except Exception:
                continue
            if action == "SEPARATOR":
                # flush previous
                if current_title is not None and current_items:
                    sections.append((current_title, current_items))
                current_title = self._clean_section_title(name)
                if not current_title:
                    current_title = fallback_title
                current_items = []
                continue
            # normal row
            if current_title is None:
                current_title = fallback_title
            current_items.append((name, action))

        if current_title is not None and current_items:
            sections.append((current_title, current_items))
        return sections

    def _set_sidebar_tabs(self, tabs):
        """Apply tabs to the sidebar list."""
        self.tabs = tabs
        titles = [ensure_str(self._format_tab_title(t[0])) for t in tabs] if tabs else []
        try:
            self["sidebar"].setList(titles)
        except Exception:
            self["sidebar"].setList([])
        # keep active_tab in range
        if not self.tabs:
            self.active_tab = 0
            return
        if self.active_tab >= len(self.tabs):
            self.active_tab = 0
        try:
            self["sidebar"].setIndex(self.active_tab)
        except Exception:
            pass

    def _on_sidebar_changed(self):
        idx = self._get_list_index(self["sidebar"])
        if idx is None:
            return
        if idx != getattr(self, "active_tab", 0):
            self.switch_tab(idx)


    def _stop_health_timer(self):
        self._closed = True
        try: self._health_timer.stop()
        except Exception: pass

    def _start_health_timer(self):
        if self._closed: return
        self._update_health()
        try:
            self._health_timer.start(2000, True)
        except Exception:
            pass

    def _read_cpu_percent(self):
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
            parts = line.split()
            if not parts or parts[0] != "cpu":
                return None
            nums = list(map(int, parts[1:8]))
            total = sum(nums)
            idle = nums[3] + nums[4]  # idle + iowait
            if self._prev_cpu is None:
                self._prev_cpu = (total, idle)
                return 0.0
            prev_total, prev_idle = self._prev_cpu
            dt = total - prev_total
            di = idle - prev_idle
            self._prev_cpu = (total, idle)
            if dt <= 0:
                return 0.0
            used = (dt - di) * 100.0 / float(dt)
            return max(0.0, min(100.0, used))
        except Exception:
            return None

    def _read_mem_pct(self):
        try:
            mem = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    mem[k.strip()] = int(v.strip().split()[0])
            total = mem.get("MemTotal", 0)
            avail = mem.get("MemAvailable", mem.get("MemFree", 0))
            used = max(0, total - avail)
            pct = (used * 100.0 / float(total)) if total else 0.0
            return pct
        except Exception:
            return None

    def _local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1.0)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None

    def _update_health(self):
        try:
            cpu = self._read_cpu_percent()
            mem = self._read_mem_pct()
            ip = self._local_ip()
            net = "OK" if ip else "N/A"
            cpu_s = "N/A" if cpu is None else "%d%%" % int(cpu)
            mem_s = "N/A" if mem is None else "%d%%" % int(mem)
            self["health"].setText("CPU: %s | RAM: %s | NET: %s" % (cpu_s, mem_s, net))
        except Exception:
            pass
        try:
            if not self._closed:
                self._health_timer.start(2000, True)
        except Exception:
            pass

    def run_with_confirmation(self):
        try:
            idx = self._get_list_index(self["menu"])
            items = self.tabs[self.active_tab][1] if self.tabs and self.active_tab < len(self.tabs) else []
            name, action = items[idx]
        except Exception:
            return 
        if action == "SEPARATOR": return 

        actions_no_confirm = [
            "CMD:SHOW_AIO_INFO", "CMD:NETWORK_DIAGNOSTICS", "CMD:FREE_SPACE_DISPLAY", 
            "CMD:UNINSTALL_MANAGER", "CMD:MANAGE_DVBAPI", "CMD:CHECK_FOR_UPDATES", 
            "CMD:SUPER_SETUP_WIZARD", "CMD:UPDATE_SATELLITES_XML", "CMD:INSTALL_SERVICEAPP", "CMD:IPTV_DEPS", 
            "CMD:INSTALL_E2KODI", "CMD:INSTALL_J00ZEK_REPO",
            "CMD:INSTALL_SOFTCAM_SCRIPT", "CMD:INSTALL_IPTV_DREAM", "CMD:SETUP_AUTO_RAM",
            "CMD:FEED_MANAGER", "CMD:POSTINSTALL_REPAIR", "CMD:TOGGLE_MENU_VISIBILITY", "CMD:SHOW_PENDING_AIO_UPDATE"
        ]
        
        if self.image_type in ["hyperion", "vti"] and action == "CMD:MANAGE_DVBAPI":
             self.sess.openWithCallback(lambda ret: self.execute_action(name, action) if ret else None, MessageBox, "UWAGA (Hyperion/VTi): Opcja może nie działać.\nKontynuować?", type=MessageBox.TYPE_YESNO); return

        if any(action.startswith(prefix) for prefix in actions_no_confirm):
            self.execute_action(name, action)
        else:
            self.sess.openWithCallback(lambda ret: self.execute_action(name, action) if ret else None, MessageBox, "Czy wykonać akcję:\n'{}'?".format(name), type=MessageBox.TYPE_YESNO)

    def clear_ram_memory(self):
        gc.collect()
        show_message_compat(self.sess, ('Uruchomiono bezpieczne porządkowanie pamięci Pythona. Cache systemu Linux nie został destrukcyjnie opróżniony.' if self.lang == 'PL' else 'Safe Python memory cleanup was run. The Linux filesystem cache was not destructively dropped.'), MessageBox.TYPE_INFO, timeout=8)

    def clear_tmp_cache(self):
        try:
            removed = _cleanup_owned_tmp(PLUGIN_TMP_PATH, 0)
            gc.collect()
            show_message_compat(self.sess, ('Usunięto pliki robocze należące do AIO Panel: %s.' % removed if self.lang == 'PL' else 'Removed AIO Panel temporary items: %s.' % removed), MessageBox.TYPE_INFO)
        except Exception as exc:
            show_message_compat(self.sess, 'Błąd: {}'.format(exc), MessageBox.TYPE_ERROR)

    def show_auto_ram_menu(self):
        current = "off"
        try:
            if config is not None and hasattr(config.plugins, "panelaio") and hasattr(config.plugins.panelaio, "auto_ram_interval"):
                current = config.plugins.panelaio.auto_ram_interval.value
        except Exception:
            pass
        title = "Auto RAM Cleaner (aktualnie: {} min)".format(current) if self.lang == 'PL' else "Auto RAM Cleaner (current: {} min)".format(current)
        self.sess.openWithCallback(
            self.set_auto_ram_timer,
            ChoiceBox,
            title=title,
            list=[("Wyłącz", "off"), ("Co 10 min", "10"), ("Co 30 min", "30"), ("Co 60 min", "60")]
        )

    def set_auto_ram_timer(self, choice):
        global g_auto_ram_active
        if not choice:
            return
        value = choice[1]

        # Persist setting
        try:
            if config is not None and hasattr(config.plugins, "panelaio") and hasattr(config.plugins.panelaio, "auto_ram_interval"):
                config.plugins.panelaio.auto_ram_interval.value = value
                config.plugins.panelaio.auto_ram_interval.save()
                if configfile:
                    configfile.save()
        except Exception as e:
            print("[AIO Panel] Auto RAM save error:", e)

        if value == "off":
            g_auto_ram_timer.stop()
            g_auto_ram_active = False
            show_message_compat(self.sess, "Auto RAM Cleaner WYŁĄCZONY." if self.lang == 'PL' else "Auto RAM Cleaner DISABLED.", MessageBox.TYPE_INFO)
        else:
            try:
                minutes = int(value)
                g_auto_ram_timer.start(minutes * 60000, False)
                g_auto_ram_active = True
                msg = "Auto RAM Cleaner WŁĄCZONY ({} min).".format(minutes) if self.lang == 'PL' else "Auto RAM Cleaner ENABLED ({} min).".format(minutes)
                show_message_compat(self.sess, msg, MessageBox.TYPE_INFO)
            except Exception as e:
                print("[AIO Panel] Auto RAM start error:", e)
                show_message_compat(self.sess, "Błąd ustawień Auto RAM Cleaner." if self.lang == 'PL' else "Auto RAM Cleaner configuration error.", MessageBox.TYPE_ERROR)


    def show_info_screen(self):
        self.session.open(AIOInfoScreen)

    def post_initial_setup(self):
        reactor.callLater(1, self.check_for_updates_on_start)
        reactor.callLater(0.5, self.update_function_description)

    def check_for_updates_on_start(self):
        Thread(target=self.perform_update_check_silent).start()

    def perform_update_check_silent(self):
        # Silent mode: do not open a modal window. Show a small bottom-left status instead.
        self._check_update(silent=True)

    def check_for_updates_manual(self):
        self.session.openWithCallback(self._manual_update_callback, MessageBox, "Sprawdzanie dostępności aktualizacji..." if self.lang == 'PL' else "Checking for updates...", type=MessageBox.TYPE_INFO, timeout=3)
        self._check_update(silent=False)

    def _manual_update_callback(self, result):
        pass

    def _fetch_remote_changelog(self):
        changelog_url = "https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/changelog.txt"
        text = _fetch_text_url(changelog_url, timeout=10, tries=2)
        text = ensure_unicode(text).strip()
        if not text:
            return TRANSLATIONS[self.lang].get("update_changelog_unavailable", "Changelog unavailable.")
        # Keep dialog readable on HD skins.
        if len(text) > 2500:
            text = text[:2500].rstrip() + "\n..."
        return text

    def _set_update_available_ui(self, remote_ver_str, changelog_text):
        self.update_info = {"version": ensure_unicode(remote_ver_str), "changelog": ensure_unicode(changelog_text)}
        try:
            self["update_status"].setText(TRANSLATIONS[self.lang]["update_status_label"])
        except Exception:
            pass
        try:
            self.set_language(self.lang)
        except Exception as e:
            print("[AIO Panel] Update UI refresh error:", e)

    def show_detected_update_prompt(self):
        if not self.update_info:
            self.check_for_updates_manual()
            return
        remote_ver_str = ensure_unicode(self.update_info.get("version", ""))
        changelog_text = ensure_unicode(self.update_info.get("changelog", "")) or self._fetch_remote_changelog()
        msg = TRANSLATIONS[self.lang]["update_available_msg"].format(
            latest_ver=remote_ver_str,
            current_ver=VER,
            changelog=changelog_text
        )
        self.sess.openWithCallback(self._do_update_action, MessageBox, msg, MessageBox.TYPE_YESNO)

    def _check_update(self, silent=False):
        version_url = "https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/version.txt"
        tmp_ver_path = "/tmp/aio_version.txt"

        try:
            if not _download_url_to_file(version_url, tmp_ver_path, timeout=10, tries=3, allow_insecure_fallback=True):
                if not silent:
                    reactor.callFromThread(show_message_compat, self.sess, TRANSLATIONS[self.lang]["update_check_error"], MessageBox.TYPE_ERROR)
                return

            with io.open(tmp_ver_path, 'r', encoding='utf-8', errors='ignore') as f:
                remote_ver_str = f.read().strip()

            local_ver = _version_to_tuple(VER)
            remote_ver = _version_to_tuple(remote_ver_str)

            if remote_ver > local_ver:
                changelog_text = self._fetch_remote_changelog()
                if silent:
                    reactor.callFromThread(self._set_update_available_ui, remote_ver_str, changelog_text)
                else:
                    self.update_info = {"version": ensure_unicode(remote_ver_str), "changelog": ensure_unicode(changelog_text)}
                    reactor.callFromThread(self.show_detected_update_prompt)
            else:
                self.update_info = None
                try:
                    reactor.callFromThread(self["update_status"].setText, "")
                except Exception:
                    pass
                if not silent:
                    reactor.callFromThread(show_message_compat, self.sess, TRANSLATIONS[self.lang]["already_latest"].format(ver=VER), MessageBox.TYPE_INFO)

        except Exception as e:
            print("[AIO Panel] Update check error:", e)
            if not silent:
                reactor.callFromThread(show_message_compat, self.sess, TRANSLATIONS[self.lang]["update_generic_error"], MessageBox.TYPE_ERROR)

    def _do_update_action(self, confirmed):
        if not confirmed:
            return
        url = 'https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh'
        status = os.path.join(PLUGIN_TMP_PATH, 'aio_self_update_%s.status' % int(time.time() * 1000))
        command = '/bin/sh %s %s %s /bin/sh' % tuple(_safe_shell_arg(x) for x in (os.path.join(PLUGIN_PATH, 'run_remote_script_safe.sh'), url, status))
        def finished(result):
            if result and result.get('success'):
                self.update_info = None
                show_message_compat(self.sess, ('Aktualizacja została zainstalowana. Sprawdź system i wykonaj restart GUI ręcznie.' if self.lang == 'PL' else 'The update was installed. Check the system and restart the GUI manually.'), MessageBox.TYPE_INFO, timeout=10)
            else:
                show_message_compat(self.sess, ('Aktualizacja nie powiodła się. Log: /tmp/aio_remote_script.log' if self.lang == 'PL' else 'Update failed. Log: /tmp/aio_remote_script.log'), MessageBox.TYPE_ERROR, timeout=14)
        run_command_in_background(self.sess, 'Aktualizacja AIO Panel', [command], callback_on_finish=finished)

    def _get_picon_target_candidates(self):
        mounts = []
        seen = set()
        candidates = ["/media", "/mnt", "/autofs"]
        try:
            if os.path.exists('/proc/mounts'):
                with open('/proc/mounts', 'r') as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) < 2:
                            continue
                        mnt = parts[1]
                        if mnt.startswith('/media/') or mnt.startswith('/mnt/') or mnt.startswith('/autofs/'):
                            if os.path.isdir(mnt) and mnt not in seen:
                                seen.add(mnt)
                                mounts.append(mnt)
        except Exception:
            pass

        for base in candidates:
            try:
                if not os.path.isdir(base):
                    continue
                for entry in sorted(os.listdir(base)):
                    mnt = os.path.join(base, entry)
                    if os.path.isdir(mnt) and mnt not in seen:
                        seen.add(mnt)
                        mounts.append(mnt)
            except Exception:
                pass

        return mounts

    def _prompt_custom_picon_path(self, title, url):
        default_path = '/media/hdd/picon'
        prompt = 'Podaj katalog docelowy dla piconów' if self.lang == 'PL' else 'Enter target folder for picons'
        self.sess.openWithCallback(lambda value: self._on_custom_picon_path(title, url, value), InputBox, title=prompt, text=default_path)

    def _on_custom_picon_path(self, title, url, value):
        if not value:
            return
        picon_path = value.strip()
        if not picon_path:
            return
        install_archive(self.sess, title, url, callback_on_finish=self.reload_settings_python, picon_path=picon_path)

    def _prompt_picon_target(self, title, url):
        default_path = '/usr/share/enigma2/picon'
        choices = []
        if self.lang == 'PL':
            choices.append(('Domyślnie: {}'.format(default_path), default_path))
        else:
            choices.append(('Default: {}'.format(default_path), default_path))

        for mount in self._get_picon_target_candidates():
            target = os.path.join(mount, 'picon')
            label = 'Urządzenie zewnętrzne: {}'.format(target) if self.lang == 'PL' else 'External device: {}'.format(target)
            choices.append((label, target))

        choices.append(('Wskaż własną ścieżkę...', '__custom__') if self.lang == 'PL' else ('Choose custom path...', '__custom__'))
        title_txt = 'Wybierz miejsce instalacji piconów' if self.lang == 'PL' else 'Choose picon installation location'
        self.sess.openWithCallback(lambda choice: self._on_picon_target_selected(title, url, choice), ChoiceBox, title=title_txt, list=choices)

    def _on_picon_target_selected(self, title, url, choice):
        if not choice:
            return
        target = choice[1]
        if target == '__custom__':
            self._prompt_custom_picon_path(title, url)
            return
        install_archive(self.sess, title, url, callback_on_finish=self.reload_settings_python, picon_path=target)

    def _safe_legacy_action_command(self, title, raw):
        """Translate legacy menu commands to audited local installers; never run raw shell."""
        raw = ensure_unicode(raw).strip()
        status = os.path.join(PLUGIN_TMP_PATH, 'legacy_action_%s_%s.status' % (os.getpid(), int(time.time() * 1000)))
        # Fixed plugin archive installer.
        if 'Bouquet_Maker_Xtream/archive/refs/tags/1.76-20260510.tar.gz' in raw:
            script = os.path.join(PLUGIN_PATH, 'install_plugin_archive_safe.sh')
            url = 'https://github.com/kiddac/Bouquet_Maker_Xtream/archive/refs/tags/1.76-20260510.tar.gz'
            source = 'Bouquet_Maker_Xtream-1.76-20260510/BouquetMakerXtream/usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream'
            target = '/usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream'
            return '/bin/sh %s %s %s %s plugin.py %s' % tuple(_safe_shell_arg(x) for x in (script, url, source, target, status))

        # Direct IPK URL is installed only after package metadata validation.
        ipk_match = re.search(r'(https://[^\s"\']+\.ipk(?:\?[^\s"\']*)?)', raw, re.I)
        if ipk_match:
            url = ipk_match.group(1)
            if not _is_https_allowed(url):
                return None
            expected = '^enigma2-plugin-(extensions|systemplugins)-[A-Za-z0-9.+_-]+$'
            if 'neoradio' in url.lower():
                expected = '^(enigma2-plugin-extensions-neoradio(?:online|-online)?|neoradio)$'
            elif 'youtube' in url.lower():
                expected = '^enigma2-plugin-extensions-youtube(?:_[A-Za-z0-9.+-]+)?$'
            return '/bin/sh %s %s %s %s' % tuple(_safe_shell_arg(x) for x in (os.path.join(PLUGIN_PATH, 'safe_ipk_install.sh'), url, expected, status))

        # Downloaded scripts are never piped directly to a shell.
        url_match = re.search(r'(https://[^\s"\']+)', raw, re.I)
        if url_match and ('| /bin/sh' in raw or '| sh' in raw or '| /bin/bash' in raw or '| bash' in raw):
            url = url_match.group(1).rstrip(');')
            if not _is_https_allowed(url):
                return None
            shell_bin = '/bin/bash' if ('bash' in raw and os.path.exists('/bin/bash')) else '/bin/sh'
            extra = ''
            if re.search(r'\bbash\s+-s\s+install\b', raw):
                extra = ' install'
            return '/bin/sh %s %s %s %s%s' % (
                _safe_shell_arg(os.path.join(PLUGIN_PATH, 'run_remote_script_safe.sh')),
                _safe_shell_arg(url), _safe_shell_arg(status), _safe_shell_arg(shell_bin), extra)

        # Strict OPKG allowlist: package identifiers only, no substitutions/redirections.
        compact = re.sub(r'\s+', ' ', raw).strip()
        if re.match(r'^opkg update\s*&&\s*opkg install\s+[A-Za-z0-9_.+@ -]+$', compact):
            packages = compact.split('opkg install', 1)[1].strip().split()
            if packages and all(_validate_identifier(pkg) for pkg in packages):
                return 'opkg update && opkg install ' + ' '.join(_safe_shell_arg(pkg) for pkg in packages)
        if compact.startswith('opkg update') and 'estalker' in compact.lower():
            return "opkg update && (opkg install enigma2-plugin-extensions-estalker || opkg install enigma2-plugin-extensions-e-stralker || opkg install enigma2-plugin-extensions-e-stalker)"
        return None

    def _show_action_result(self, result):
        if result and result.get('success'):
            msg = ('Operacja zakończona poprawnie. Restart GUI wykonaj ręcznie tylko wtedy, gdy jest wymagany.'
                   if self.lang == 'PL' else
                   'Operation completed successfully. Restart the GUI manually only when required.')
            show_message_compat(self.sess, msg, timeout=8)
        else:
            detail = ''
            if result:
                detail = ensure_unicode(result.get('error') or result.get('stderr') or result.get('output') or '').strip()
            msg = ('Operacja nie powiodła się.' if self.lang == 'PL' else 'Operation failed.')
            if detail:
                msg += '\n\n' + detail[-900:]
            show_message_compat(self.sess, msg, MessageBox.TYPE_ERROR, timeout=14)

    def _run_safe_legacy_action(self, title, raw):
        command = self._safe_legacy_action_command(title, raw)
        if not command:
            msg = ('Ta pozycja została zablokowana, ponieważ źródło używa HTTP albo komenda nie spełnia zasad bezpieczeństwa.'
                   if self.lang == 'PL' else
                   'This item was blocked because its source uses HTTP or the command does not meet the safety policy.')
            show_message_compat(self.sess, msg, MessageBox.TYPE_ERROR, timeout=14)
            return
        def done(result):
            if result and result.get('success'):
                show_message_compat(self.sess, ('Operacja zakończona poprawnie. Restart wykonaj ręcznie, jeśli jest wymagany.' if self.lang == 'PL' else 'Operation completed successfully. Restart manually if required.'), timeout=7)
            else:
                show_message_compat(self.sess, ('Operacja nie powiodła się. Sprawdź log instalatora w /tmp.' if self.lang == 'PL' else 'Operation failed. Check the installer log in /tmp.'), MessageBox.TYPE_ERROR, timeout=12)
        run_command_in_background(self.sess, title, [command], callback_on_finish=done)

    # --- GŁÓWNY WYKONAWCA AKCJI ---
    def execute_action(self, name, action):
        title = name
        if action.startswith('picons:'):
            self._prompt_picon_target(title, action.split(':', 1)[1])
        elif action.startswith('s4archive:'):
            install_archive(self.sess, title, action.split(':', 1)[1], callback_on_finish=self.reload_settings_python, action_type='channels_s4a')
        elif action.startswith('archive:'):
            install_archive(self.sess, title, action.split(':', 1)[1], callback_on_finish=self.reload_settings_python, action_type='channels')
        elif action.startswith('m3u_json:'):
            try:
                url, bid, bname = _decode_action_payload(action.split(':', 1)[1], 'm3u')
            except Exception as e:
                show_message_compat(self.sess, 'Nieprawidłowa definicja M3U: %s' % e, MessageBox.TYPE_ERROR)
                return
            self.install_m3u_as_bouquet(title, url, bid, bname)
        elif action.startswith('bouquet_json:'):
            try:
                url, bid, bname = _decode_action_payload(action.split(':', 1)[1], 'bouquet')
            except Exception as e:
                show_message_compat(self.sess, 'Nieprawidłowa definicja bukietu: %s' % e, MessageBox.TYPE_ERROR)
                return
            self.install_bouquet_reference(title, url, bid, bname)
        elif action.startswith('m3u:'):
            # Backward compatibility for cached legacy menu entries.
            try:
                url, bid, bname = action.split(':', 1)[1].rsplit(':', 2)
            except Exception:
                show_message_compat(self.sess, 'Nieprawidłowa definicja M3U.', MessageBox.TYPE_ERROR)
                return
            self.install_m3u_as_bouquet(title, url, bid, bname)
        elif action.startswith('bouquet:'):
            try:
                url, bid, bname = action.split(':', 1)[1].rsplit(':', 2)
            except Exception:
                show_message_compat(self.sess, 'Nieprawidłowa definicja bukietu.', MessageBox.TYPE_ERROR)
                return
            self.install_bouquet_reference(title, url, bid, bname)
        elif action.startswith('opkg:'):
            package_spec = action.split(':', 1)[1].strip()
            packages = [item for item in package_spec.replace(',', ' ').split() if item]
            if not packages or not all(_validate_identifier(item) for item in packages):
                show_message_compat(self.sess, 'Nieprawidłowa nazwa pakietu OPKG.', MessageBox.TYPE_ERROR)
                return
            command = 'opkg update && opkg install ' + ' '.join(_safe_shell_arg(item) for item in packages)
            run_command_in_background(self.sess, title, [command], callback_on_finish=lambda result: self._show_action_result(result))
        elif action.startswith('remote_script_bash:') or action.startswith('remote_script:'):
            use_bash = action.startswith('remote_script_bash:')
            spec = action.split(':', 1)[1]
            parts = spec.split('|', 1)
            url = parts[0].strip()
            script_arg = parts[1].strip() if len(parts) > 1 else ''
            if not _is_https_allowed(url) or (script_arg and not _validate_identifier(script_arg)):
                show_message_compat(self.sess, 'Nieprawidłowe lub niezaufane źródło instalatora.', MessageBox.TYPE_ERROR)
                return
            status = os.path.join(PLUGIN_TMP_PATH, 'remote_action_%s_%s.status' % (os.getpid(), int(time.time() * 1000)))
            shell_bin = '/bin/bash' if use_bash and os.path.exists('/bin/bash') else '/bin/sh'
            command = '/bin/sh %s %s %s %s%s' % (
                _safe_shell_arg(os.path.join(PLUGIN_PATH, 'run_remote_script_safe.sh')),
                _safe_shell_arg(url), _safe_shell_arg(status), _safe_shell_arg(shell_bin),
                (' ' + _safe_shell_arg(script_arg)) if script_arg else '')
            run_command_in_background(self.sess, title, [command], callback_on_finish=lambda result: self._show_action_result(result))
        elif action.startswith('safe_ipk:'):
            spec = action.split(':', 1)[1]
            parts = spec.split('|', 1)
            url = parts[0].strip()
            expected = parts[1].strip() if len(parts) > 1 else '^enigma2-plugin-(extensions|systemplugins)-[A-Za-z0-9.+_-]+$'
            if not _is_https_allowed(url):
                show_message_compat(self.sess, 'Nieprawidłowe źródło IPK.', MessageBox.TYPE_ERROR)
                return
            status = os.path.join(PLUGIN_TMP_PATH, 'ipk_action_%s_%s.status' % (os.getpid(), int(time.time() * 1000)))
            command = '/bin/sh %s %s %s %s' % tuple(_safe_shell_arg(x) for x in (os.path.join(PLUGIN_PATH, 'safe_ipk_install.sh'), url, expected, status))
            run_command_in_background(self.sess, title, [command], callback_on_finish=lambda result: self._show_action_result(result))
        elif action.startswith('bash_raw:'):
            # Compatibility only for old cached menu data; raw shell is translated through a strict allowlist.
            self._run_safe_legacy_action(title, action.split(':', 1)[1])
        elif action.startswith('blocked:'):
            show_message_compat(self.sess, action.split(':', 1)[1], MessageBox.TYPE_ERROR, timeout=12)
        elif action.startswith('CMD:'):
            key = action.split(':', 1)[1]
            if key == 'SUPER_SETUP_WIZARD': self.run_super_setup_wizard()
            elif key == 'CHECK_FOR_UPDATES': self.check_for_updates_manual()
            elif key == 'SHOW_PENDING_AIO_UPDATE': self.show_detected_update_prompt()
            elif key == 'UPDATE_SATELLITES_XML': run_command_in_background(self.sess, title, ['/bin/sh ' + _safe_shell_arg(os.path.join(PLUGIN_PATH, 'update_satellites_xml.sh'))], callback_on_finish=self.reload_settings_python)
            elif key == 'INSTALL_SERVICEAPP': run_command_in_background(self.sess, title, ['opkg update && opkg install enigma2-plugin-systemplugins-serviceapp exteplayer3 gstplayer && opkg install uchardet --force-reinstall'])
            elif key == 'IPTV_DEPS': self.install_iptv_deps()
            elif key == 'INSTALL_BEST_OSCAM': self.install_best_oscam()
            elif key == 'INSTALL_LEVI45_OSCAM': self.install_levi45_oscam()
            elif key == 'INSTALL_SOFTCAM_SCRIPT': self.install_softcam_script()
            elif key == 'INSTALL_NCAM_FEED': self.install_ncam_feed()
            elif key == 'INSTALL_IPTV_DREAM': self.install_iptv_dream_simplified()
            elif key == 'MANAGE_DVBAPI': self.manage_dvbapi()
            elif key == 'UPDATE_DVBAPI_POLAND': self.update_oscam_dvbapi_poland()
            elif key == 'UNINSTALL_MANAGER': self.show_uninstall_manager()
            elif key == 'PLUGIN_UPDATE_MANAGER': self.show_plugin_update_manager()
            elif key == 'CLEAR_OSCAM_PASS': self.clear_oscam_password()
            elif key == 'CLEAR_FTP_PASS': run_command_in_background(self.sess, title, ['passwd -d root'])
            elif key == 'SET_SYSTEM_PASSWORD': self.set_system_password()
            elif key == 'RESTART_OSCAM': self.restart_oscam()
            elif key == 'SETUP_AUTO_RAM': self.show_auto_ram_menu()
            elif key == 'TOGGLE_MENU_VISIBILITY': self.toggle_menu_visibility()
            elif key == 'CLEAR_TMP_CACHE': self.clear_tmp_cache()
            elif key == 'CLEAR_RAM_CACHE': self.clear_ram_memory()
            elif key == 'INSTALL_E2KODI': install_e2kodi(self.sess)
            elif key == 'INSTALL_J00ZEK_REPO': self.install_j00zek_repo()
            elif key == 'SHOW_AIO_INFO': self.show_info_screen()
            elif key == 'BACKUP_LIST': self.backup_lists()
            elif key == 'BACKUP_OSCAM': self.backup_oscam()
            elif key == 'FEED_MANAGER': self.open_feed_manager()
            elif key == 'POSTINSTALL_REPAIR': self.open_postinstall_repair()
            elif key == 'RESTORE_LIST': self.restore_lists()
            elif key == 'RESTORE_OSCAM': self.restore_oscam()
            elif key == 'SYSTEM_MONITOR': self.open_system_monitor()
            elif key == 'LOG_VIEWER': self.open_log_viewer()
            elif key == 'CRON_MANAGER': self.open_cron_manager()
            elif key == 'SERVICE_MANAGER': self.open_service_manager()
            elif key == 'SYSTEM_INFO': self.open_system_info()
            elif key == 'NETWORK_DIAGNOSTICS': self.run_network_diagnostics()
            elif key == 'FREE_SPACE_DISPLAY': console_screen_open(self.sess, 'Wolne miejsce', ['df -h'], close_on_finish=False)
            elif key == 'SMART_CLEANUP': self.smart_cleanup()
            elif key == 'BROKEN_PLUGIN_CLEANER': self.clean_broken_plugins()
            elif key == 'AIO_QUICKSTART': self.open_aio_quickstart()
            elif key == 'COMPATIBILITY_CHECK': self.open_compatibility_check()
            elif key == 'SHOW_AIO_TIP': self.show_aio_tip()
            elif key == 'LOCAL_CHANGELOG': self.show_local_changelog()
            elif key == 'UPDATE_SRVID': self.update_oscam_srvid_files()
            elif key == 'INSTALL_SOFTCAMKEY_ONLINE': self.install_softcam_key_online()
            elif key == 'INSTALL_BMX_SAFE':
                status = os.path.join(PLUGIN_TMP_PATH, 'bmx_install_%s.status' % os.getpid())
                command = '/bin/sh %s %s %s %s plugin.py %s' % tuple(_safe_shell_arg(x) for x in (
                    os.path.join(PLUGIN_PATH, 'install_plugin_archive_safe.sh'),
                    'https://github.com/kiddac/Bouquet_Maker_Xtream/archive/refs/tags/1.76-20260510.tar.gz',
                    'Bouquet_Maker_Xtream-1.76-20260510/BouquetMakerXtream/usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream',
                    '/usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream', status))
                run_command_in_background(self.sess, title, [command], callback_on_finish=lambda result: self._show_action_result(result))
            elif key == 'INSTALL_ESTALKER_SAFE':
                command = 'opkg update && (opkg install enigma2-plugin-extensions-estalker || opkg install enigma2-plugin-extensions-e-stralker || opkg install enigma2-plugin-extensions-e-stalker)'
                run_command_in_background(self.sess, title, [command], callback_on_finish=lambda result: self._show_action_result(result))

    # --- FUNKCJE INSTALACYJNE I POMOCNICZE ---
    
    # NAPRAWIONY SUPER KONFIGURATOR Z OPISEM
    def run_super_setup_wizard(self):
        lang = self.lang
        options = [
            (TRANSLATIONS[lang]['sk_option_deps'], 'deps_only'),
            (TRANSLATIONS[lang]['sk_option_basic_no_picons'], 'install_basic_no_picons'),
            (TRANSLATIONS[lang]['sk_option_full_picons'], 'install_with_picons'),
            (TRANSLATIONS[lang]['sk_option_cancel'], 'cancel')
        ]
        desc_map = {
            'deps_only': ('Instaluje wyłącznie brakujące zależności. Nie zmienia list, piconów ani softcamu.' if lang == 'PL' else 'Installs missing dependencies only. It does not change lists, picons or softcam.'),
            'install_basic_no_picons': ('Bezpiecznie instaluje listę Polska 13E AIO Panel, feed Softcam i OSCam-Emu. Każdy krok jest sprawdzany; bez automatycznego restartu.' if lang == 'PL' else 'Safely installs Polska 13E AIO Panel, the Softcam feed and OSCam-Emu. Every step is verified; no automatic restart.'),
            'install_with_picons': ('Pełna konfiguracja jak START oraz picony do wybranego katalogu. Wymaga wolnego miejsca; bez automatycznego restartu.' if lang == 'PL' else 'Full START configuration plus picons in a selected folder. Requires free space; no automatic restart.'),
            'cancel': ('Powrót do menu.' if lang == 'PL' else 'Return to menu.')
        }
        self.sess.openWithCallback(self._super_wizard_selected, SuperWizardChoiceScreen, options=options, title=TRANSLATIONS[lang]['sk_choice_title'], description_map=desc_map)

    def _super_wizard_selected(self, choice):
        if not choice or choice[1] == 'cancel':
            return
        key = choice[1]
        if key == 'install_with_picons':
            choices = []
            default = '/usr/share/enigma2/picon'
            choices.append((('Pamięć wewnętrzna: ' if self.lang == 'PL' else 'Internal flash: ') + default, default))
            for mount in self._get_picon_target_candidates():
                target = os.path.join(mount, 'picon')
                choices.append((('Nośnik zewnętrzny: ' if self.lang == 'PL' else 'External device: ') + target, target))
            choices.append((('Wskaż własną ścieżkę...' if self.lang == 'PL' else 'Choose a custom path...'), '__custom__'))
            self.sess.openWithCallback(lambda selected: self._start_super_wizard(key, selected), ChoiceBox, title=('Wybierz katalog piconów' if self.lang == 'PL' else 'Choose the picon folder'), list=choices)
        else:
            self._start_super_wizard(key, None)

    def _start_super_wizard(self, key, picon_choice):
        if picon_choice and picon_choice[1] == '__custom__':
            self.sess.openWithCallback(lambda value: self._start_super_wizard_custom(key, value), InputBox, title=('Podaj katalog piconów' if self.lang == 'PL' else 'Enter picon folder'), text='/media/hdd/picon')
            return
        picon_path = picon_choice[1] if picon_choice else '/usr/share/enigma2/picon'
        steps = {'deps_only': ['deps'], 'install_basic_no_picons': ['deps', 'channel_list', 'install_softcam', 'install_oscam', 'reload_settings'], 'install_with_picons': ['deps', 'channel_list', 'install_softcam', 'install_oscam', 'picons', 'reload_settings']}.get(key, [])
        if not steps:
            return
        channel_url = 'https://github.com/OliOli2013/PanelAIO-Lists/raw/main/archives/Polska_13E_AIO_Panel.zip'
        try:
            for item in self.fetched_data_cache.get('repo_lists', []):
                if not (isinstance(item, (list, tuple)) and len(item) >= 2):
                    continue
                action = ensure_unicode(item[1])
                if not action.startswith('archive:'):
                    continue
                item_url = action.split(':', 1)[1]
                normalized = re.sub(r'[^a-z0-9]+', ' ', ensure_unicode(item[0]).replace(u'📡 ', '').lower()).strip()
                if normalized == 'polska 13e aio panel' or 'Polska_13E_AIO_Panel.zip' in item_url:
                    channel_url = item_url
                    break
        except Exception:
            pass
        self.sess.open(WizardProgressScreen, steps=steps, channel_list_url=channel_url, channel_list_name='Polska 13E AIO Panel', picon_url='https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip', picon_path=picon_path, lang=self.lang)

    def _start_super_wizard_custom(self, key, value):
        value = ensure_unicode(value).strip()
        allowed = value.startswith('/usr/share/enigma2/picon') or re.match(r'^/media/[A-Za-z0-9_.-]+/picon(?:/.*)?$', value)
        if not value or not allowed:
            show_message_compat(self.sess, ('Niedozwolony katalog piconów.' if self.lang == 'PL' else 'The picon folder is not allowed.'), MessageBox.TYPE_ERROR)
            return
        self._start_super_wizard(key, ('custom', value))

    def toggle_menu_visibility(self):
        # Toggle visibility of AIO Panel entry in receiver main/system menu (WHERE_MENU)
        try:
            current = _get_show_in_menu_setting(True)
            new_value = not current
            if not _set_show_in_menu_setting(new_value):
                show_message_compat(self.sess, 'Błąd zapisu ustawień widoczności menu.', MessageBox.TYPE_ERROR)
                return
            state_pl = 'WŁĄCZONE' if new_value else 'WYŁĄCZONE'
            state_en = 'ENABLED' if new_value else 'DISABLED'
            try:
                self.set_language(self.lang)
            except Exception:
                pass
            msg = ('Widoczność w menu tunera: %s\n\nPozycja w menu głównym/systemowym zmieni się po ponownym otwarciu menu. Jeśli obraz trzyma stare menu w pamięci, zrób Restart GUI.' % state_pl)
            if self.lang != 'PL':
                msg = ('Receiver menu visibility: %s\n\nThe main/system menu entry changes after reopening the menu. If your image caches the menu, restart GUI.' % state_en)
            show_message_compat(
                self.sess,
                msg,
                MessageBox.TYPE_INFO,
                timeout=8
            )
        except Exception as e:
            print('[AIO Panel] toggle_menu_visibility error:', e)
            show_message_compat(self.sess, 'Błąd zapisu ustawień.', MessageBox.TYPE_ERROR)

    def install_j00zek_repo(self):
        cmd = """echo "src/gz opkg-j00zka https://j00zek.github.io/eeRepo" > /etc/opkg/opkg-j00zka.conf && opkg update"""
        run_command_in_background(self.sess, "J00Zek Repo", [cmd])

    def install_m3u_as_bouquet(self, title, url, bouquet_id, bouquet_name):
        if not _is_https_allowed(url) or not re.match(r'^userbouquet\.[A-Za-z0-9_.-]+\.tv$', ensure_unicode(bouquet_id)):
            show_message_compat(self.sess, 'Nieprawidłowy URL HTTPS lub identyfikator bukietu.', MessageBox.TYPE_ERROR)
            return
        work = _unique_tmp_dir('m3u-')
        tmp_path = os.path.join(work, 'source.m3u')
        def downloaded(result):
            if not result or not result.get('success'):
                shutil.rmtree(work, ignore_errors=True)
                show_message_compat(self.sess, 'Nie udało się pobrać listy M3U.', MessageBox.TYPE_ERROR)
                return
            thread = Thread(target=self._parse_m3u_thread, args=(tmp_path, bouquet_id, bouquet_name, work))
            try: thread.setDaemon(True)
            except Exception: pass
            thread.start()
        run_command_in_background(self.sess, title, [_download_shell_command(url, tmp_path, 'file')], callback_on_finish=downloaded)

    def _parse_m3u_thread(self, tmp_path, bid, bname, work=None):
        result = {'success': False, 'stderr': ''}
        try:
            if not os.path.isfile(tmp_path) or os.path.getsize(tmp_path) <= 0:
                raise ValueError('Pusty plik M3U')
            entries = ['#NAME {}\n'.format(_sanitize_service_name(bname, 'IPTV'))]
            current_name = 'Kanał IPTV'
            with io.open(tmp_path, 'r', encoding='utf-8-sig', errors='ignore') as handle:
                for raw in handle:
                    line = ensure_unicode(raw).strip()
                    if line.upper().startswith('#EXTINF:'):
                        current_name = _sanitize_service_name(line.split(',', 1)[1] if ',' in line else 'Kanał IPTV')
                    elif re.match(r'^https?://', line, re.I):
                        if not line.lower().startswith('https://'):
                            continue
                        entries.append('#SERVICE 4097:0:1:0:0:0:0:0:0:0:{}:{}\n'.format(_encode_service_url(line), current_name))
                        entries.append('#DESCRIPTION {}\n'.format(current_name))
                        current_name = 'Kanał IPTV'
            if len(entries) <= 1:
                raise ValueError('Brak prawidłowych strumieni HTTPS w M3U')
            staged = os.path.join(work or PLUGIN_TMP_PATH, bid + '.new')
            with io.open(staged, 'w', encoding='utf-8') as handle:
                handle.writelines(entries)
                handle.flush()
                try: os.fsync(handle.fileno())
                except Exception: pass
            result = {'success': True, 'staged': staged, 'count': len(entries) - 1, 'work': work}
        except Exception as exc:
            result = {'success': False, 'stderr': ensure_unicode(exc), 'work': work}
        reactor.callFromThread(self._install_parsed_bouquet, result, bid)

    def _install_parsed_bouquet(self, result, bid):
        work = (result or {}).get('work')
        try:
            if not result or not result.get('success'):
                raise ValueError((result or {}).get('stderr') or 'Błąd parsowania M3U')
            target = os.path.join('/etc/enigma2', bid)
            bouquets = '/etc/enigma2/bouquets.tv'
            stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            if os.path.isfile(target):
                shutil.copy2(target, target + '.aio-bak-' + stamp)
            os.rename(result['staged'], target)
            current = _read_text_file(bouquets, '#NAME Bouquets (TV)\n')
            reference = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "{}" ORDER BY bouquet\n'.format(bid)
            if reference not in current:
                _atomic_write(bouquets, current.rstrip('\n') + '\n' + reference)
            self.reload_settings_python()
            show_message_compat(self.sess, 'Dodano kanały IPTV: %s' % result.get('count', '?'), timeout=6)
        except Exception as exc:
            show_message_compat(self.sess, 'Import M3U nie powiódł się:\n%s' % exc, MessageBox.TYPE_ERROR, timeout=12)
        finally:
            if work:
                shutil.rmtree(work, ignore_errors=True)

    def install_bouquet_reference(self, title, url, bid, bname):
        if not _is_https_allowed(url) or not re.match(r'^userbouquet\.[A-Za-z0-9_.-]+\.tv$', ensure_unicode(bid)):
            show_message_compat(self.sess, 'Nieprawidłowy URL HTTPS lub identyfikator bukietu.', MessageBox.TYPE_ERROR)
            return
        work = _unique_tmp_dir('bouquet-')
        staged = os.path.join(work, bid)
        def finished(result):
            try:
                if not result or not result.get('success') or not os.path.isfile(staged):
                    raise ValueError('Pobieranie bukietu nie powiodło się')
                data = _read_text_file(staged, '')
                if '#SERVICE' not in data and '#NAME' not in data:
                    raise ValueError('Pobrany plik nie jest bukietem Enigma2')
                target = os.path.join('/etc/enigma2', bid)
                stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                if os.path.isfile(target): shutil.copy2(target, target + '.aio-bak-' + stamp)
                os.rename(staged, target)
                bfile = '/etc/enigma2/bouquets.tv'
                current = _read_text_file(bfile, '#NAME Bouquets (TV)\n')
                ref = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "{}" ORDER BY bouquet\n'.format(bid)
                if ref not in current: _atomic_write(bfile, current.rstrip('\n') + '\n' + ref)
                self.reload_settings_python()
            except Exception as exc:
                show_message_compat(self.sess, 'Instalacja bukietu nie powiodła się:\n%s' % exc, MessageBox.TYPE_ERROR)
            finally:
                shutil.rmtree(work, ignore_errors=True)
        run_command_in_background(self.sess, title, [_download_shell_command(url, staged, 'file')], callback_on_finish=finished)

    # --- NOWA, NAPRAWIONA FUNKCJA SRVID (Źródło: Aktualne repozytoria) ---
    def update_oscam_srvid_files(self):
        srvid = ['https://raw.githubusercontent.com/openmb/open-pli-core/master/meta-openpli/recipes-openpli/enigma2-softcams/enigma2-plugin-softcams-oscam/oscam.srvid', 'https://raw.githubusercontent.com/bmihovski/Oscam-Services-Bulcrypt/master/oscam.srvid']
        srvid2 = ['https://raw.githubusercontent.com/openmb/open-pli-core/master/meta-openpli/recipes-openpli/enigma2-softcams/enigma2-plugin-softcams-oscam/oscam.srvid2']
        script = os.path.join(PLUGIN_PATH, 'update_oscam_data_safe.sh')
        status1 = os.path.join(PLUGIN_TMP_PATH, 'srvid_%s.status' % int(time.time() * 1000))
        status2 = os.path.join(PLUGIN_TMP_PATH, 'srvid2_%s.status' % int(time.time() * 1000))
        cmd1 = '/bin/sh %s srvid %s %s' % (_safe_shell_arg(script), _safe_shell_arg(status1), ' '.join(_safe_shell_arg(x) for x in srvid))
        cmd2 = '/bin/sh %s srvid2 %s %s' % (_safe_shell_arg(script), _safe_shell_arg(status2), ' '.join(_safe_shell_arg(x) for x in srvid2))
        run_command_in_background(self.sess, 'Aktualizacja oscam.srvid/srvid2', [cmd1, cmd2])
    def install_softcam_key_online(self):
        urls = ['https://raw.githubusercontent.com/oscam-emu/oscam-patched-old/master/Distribution/doc/example/SoftCam.Key', 'https://raw.githubusercontent.com/oscam-emu/oscam-emu/master/Distribution/doc/example/SoftCam.Key']
        script = os.path.join(PLUGIN_PATH, 'update_oscam_data_safe.sh')
        status = os.path.join(PLUGIN_TMP_PATH, 'softcamkey_%s.status' % int(time.time() * 1000))
        cmd = '/bin/sh %s softcamkey %s %s' % (_safe_shell_arg(script), _safe_shell_arg(status), ' '.join(_safe_shell_arg(x) for x in urls))
        run_command_in_background(self.sess, 'Aktualizacja SoftCam.Key', [cmd])



    def open_feed_manager(self):
        if self.lang == 'PL':
            choices = [
                ("🧪 Test działania feedów", "test"),
                ("📄 Pokaż aktywne repozytoria", "list"),
                ("♻️ Wyczyść cache opkg i odśwież feedy", "refresh"),
                ("💾 Backup plików repozytoriów", "backup"),
                ("📦 Dodaj / przeinstaluj J00zeks Feed", "j00zek")
            ]
            title_txt = "Menedżer Feedów / Repozytoriów"
        else:
            choices = [
                ("🧪 Test feed connectivity", "test"),
                ("📄 Show active repositories", "list"),
                ("♻️ Clear opkg cache and refresh feeds", "refresh"),
                ("💾 Backup repository files", "backup"),
                ("📦 Add / reinstall J00zek Feed", "j00zek")
            ]
            title_txt = "Feed / Repository Manager"
        self.sess.openWithCallback(self._feed_manager_selected, ChoiceBox, title=title_txt, list=choices)

    def _feed_manager_selected(self, choice):
        if not choice:
            return
        action = choice[1]
        title = choice[0]
        if action == "j00zek":
            self.install_j00zek_repo()
            return
        if action == "list":
            cmd = r'''
                echo "=== AIO Feed Manager: active repositories ==="
                FOUND=0
                for F in /etc/opkg/*.conf /etc/opkg/*.feed /etc/opkg/*.list /etc/opkg/*/*.conf; do
                    [ -f "$F" ] || continue
                    FOUND=1
                    echo ""
                    echo "--- $F ---"
                    cat "$F" 2>/dev/null || true
                done
                [ "$FOUND" -eq 0 ] && echo "No repository files found in /etc/opkg."
            '''
            console_screen_open(self.sess, title, [cmd], close_on_finish=False)
            return
        if action == "refresh":
            cmd = r'''
                echo "=== AIO Feed Manager: refresh feeds ==="
                echo "[1/3] Cleaning package-list cache..."
                rm -rf /var/cache/opkg/* /var/lib/opkg/lists/* 2>/dev/null || true
                echo "[2/3] Repository files:"
                ls -1 /etc/opkg 2>/dev/null || true
                echo "[3/3] Running opkg update..."
                opkg update
                sync
            '''
            console_screen_open(self.sess, title, [cmd], close_on_finish=False)
            return
        if action == "backup":
            out_dir = self._get_backup_path() or "/tmp/"
            out_file = os.path.join(out_dir, "aio_repo_backup_{}.tar.gz".format(self._make_timestamp()))
            cmd = r'''
                OUT="__OUT__"
                mkdir -p "$(dirname "$OUT")"
                echo "=== AIO Feed Manager: backup repositories ==="
                tar -czf "$OUT" /etc/opkg 2>/dev/null || tar -czf "$OUT" /etc/opkg/*.conf 2>/dev/null
                echo "Backup saved to: $OUT"
            '''.replace("__OUT__", out_file)
            console_screen_open(self.sess, title, [cmd], close_on_finish=False)
            return
        if action == "test":
            out_file = os.path.join("/tmp", "aio_feed_test_{}.txt".format(self._make_timestamp()))
            cmd = r'''
                OUT="__OUT__"
                : > "$OUT"
                log(){ echo "$1"; echo "$1" >> "$OUT"; }
                test_url(){
                    URL="$1"
                    wget -qO /dev/null -T 10 "$URL" >/dev/null 2>&1 && return 0
                    wget -qO /dev/null -T 10 "$URL" >/dev/null 2>&1 && return 0
                    curl -fL -m 10 -o /dev/null -sS "$URL" >/dev/null 2>&1 && return 0
                    return 1
                }
                log "=== AIO Feed Test ==="
                log "Date: $(date)"
                log ""
                log "[1/3] Repository files:"
                FOUND=0
                for F in /etc/opkg/*.conf /etc/opkg/*.feed /etc/opkg/*.list /etc/opkg/*/*.conf; do
                    [ -f "$F" ] || continue
                    FOUND=1
                    log "--- $F ---"
                    cat "$F" >> "$OUT" 2>/dev/null || true
                    echo "" >> "$OUT"
                    echo ""
                done
                [ "$FOUND" -eq 0 ] && log "No repository files found in /etc/opkg."
                log ""
                log "[2/3] Feed URL test:"
                URLS=$(grep -h -v '^[[:space:]]*#' /etc/opkg/*.conf /etc/opkg/*/*.conf 2>/dev/null | awk '$1 ~ /^src/ {print $3}' | sort -u)
                if [ -z "$URLS" ]; then
                    log "No active feed URLs detected."
                else
                    for URL in $URLS; do
                        log "Feed: $URL"
                        OK=1
                        for CAND in "$URL/Packages.gz" "$URL/packages.gz" "$URL/Packages" "$URL/packages" "$URL"; do
                            if test_url "$CAND"; then
                                log "  [OK] $CAND"
                                OK=0
                                break
                            fi
                        done
                        [ "$OK" -ne 0 ] && log "  [FAIL] no response from standard feed endpoints"
                    done
                fi
                log ""
                log "[3/3] opkg update test:"
                OPKGLOG="/tmp/aio_opkg_update_test.log"
                opkg update > "$OPKGLOG" 2>&1
                RC=$?
                cat "$OPKGLOG" | tee -a "$OUT"
                log ""
                if [ "$RC" -eq 0 ]; then
                    log "[OK] opkg update completed successfully."
                else
                    log "[FAIL] opkg update returned code: $RC"
                fi
                log "Report saved to: $OUT"
            '''.replace("__OUT__", out_file)
            console_screen_open(self.sess, title, [cmd], close_on_finish=False)

    def open_postinstall_repair(self):
        if self.lang == 'PL':
            choices = [
                ("🛠 Pełna naprawa po instalacji", "full"),
                ("🔐 Napraw uprawnienia plików", "permissions"),
                ("🔑 Napraw Softcam", "softcam"),
                ("📅 Napraw EPG", "epg"),
                ("🖼️ Napraw picony", "picons"),
                ("⚙️ Napraw ServiceApp", "serviceapp"),
                ("🌍 Napraw Streamlink", "streamlink")
            ]
            title_txt = "Tryb Naprawy po Instalacji"
        else:
            choices = [
                ("🛠 Full post-install repair", "full"),
                ("🔐 Repair file permissions", "permissions"),
                ("🔑 Repair Softcam", "softcam"),
                ("📅 Repair EPG", "epg"),
                ("🖼️ Repair picons", "picons"),
                ("⚙️ Repair ServiceApp", "serviceapp"),
                ("🌍 Repair Streamlink", "streamlink")
            ]
            title_txt = "Post-Install Repair Mode"
        self.sess.openWithCallback(self._postinstall_repair_selected, ChoiceBox, title=title_txt, list=choices)

    def _postinstall_repair_selected(self, choice):
        if not choice:
            return
        mode = choice[1]
        title = choice[0]
        cmd = self._build_postinstall_repair_script(mode)
        console_screen_open(self.sess, title, [cmd], close_on_finish=False)

    def _build_postinstall_repair_script(self, mode):
        cmd = r'''
            MODE="__MODE__"
            echo "=== AIO Post-Install Repair ==="
            echo "Mode: $MODE"
            echo "Date: $(date)"
            echo ""

            pkg_exists(){
                PKG="$1"
                opkg list 2>/dev/null | awk '{print $1}' | grep -qx "$PKG"
            }

            install_if_available(){
                for PKG in "$@"; do
                    if pkg_exists "$PKG"; then
                        echo "Installing/reinstalling: $PKG"
                        opkg install --force-reinstall "$PKG" 2>/dev/null || opkg install "$PKG" 2>/dev/null || true
                    fi
                done
            }

            reinstall_detected_or_first(){
                for PKG in "$@"; do
                    if opkg list-installed 2>/dev/null | awk '{print $1}' | grep -qx "$PKG"; then
                        echo "Reinstalling installed package: $PKG"
                        opkg install --force-reinstall "$PKG" 2>/dev/null || opkg install "$PKG" 2>/dev/null || true
                        return 0
                    fi
                done
                for PKG in "$@"; do
                    if pkg_exists "$PKG"; then
                        echo "Installing fallback package: $PKG"
                        opkg install "$PKG" 2>/dev/null || opkg install --force-reinstall "$PKG" 2>/dev/null || true
                        return 0
                    fi
                done
                echo "No matching package found in feeds: $*"
                return 1
            }

            fix_tree(){
                D="$1"
                [ -e "$D" ] || return 0
                chown -R root:root "$D" 2>/dev/null || true
                find "$D" -type d -exec chmod 755 {} \; 2>/dev/null || true
                find "$D" -type f -exec chmod 644 {} \; 2>/dev/null || true
            }

            repair_permissions(){
                echo "[1] Repairing permissions..."
                fix_tree /etc/enigma2
                fix_tree /etc/tuxbox
                fix_tree /etc/tuxbox/config
                fix_tree /usr/keys
                fix_tree /etc/epgimport
                for F in /etc/init.d/softcam /usr/bin/oscam /usr/bin/ncam; do
                    [ -f "$F" ] && chmod 755 "$F" 2>/dev/null || true
                done
                for D in /usr/share/enigma2/picon /media/hdd/picon /media/usb/picon; do
                    [ -d "$D" ] && fix_tree "$D"
                done
                sync
            }

            repair_softcam(){
                echo "[2] Repairing Softcam..."
                opkg update || true
                chmod 755 /etc/init.d/softcam 2>/dev/null || true
                reinstall_detected_or_first enigma2-plugin-softcams-oscam enigma2-plugin-softcams-oscam-emu oscam oscam-emu oscam-smod ncam softcam-ncam enigma2-plugin-softcams-ncam enigma2-plugin-softcams-ncam-emu || true
                /etc/init.d/softcam stop 2>/dev/null || systemctl stop softcam 2>/dev/null || true
                for P in oscam oscam-emu oscam_emu ncam softcam; do killall -TERM "$P" 2>/dev/null || true; done
                N=0; while ps 2>/dev/null | grep -E '[o]scam|[n]cam|[s]oftcam' >/dev/null 2>&1 && [ "$N" -lt 8 ]; do sleep 1; N=$((N+1)); done
                for P in oscam oscam-emu oscam_emu ncam softcam; do killall -KILL "$P" 2>/dev/null || true; done
                sleep 1
                /etc/init.d/softcam start 2>/dev/null || systemctl start softcam 2>/dev/null || systemctl start oscam 2>/dev/null || true
                ps | grep -E 'oscam|ncam|softcam' | grep -v grep || true
            }

            repair_epg(){
                echo "[3] Repairing EPG..."
                mkdir -p /etc/epgimport /etc/enigma2 2>/dev/null || true
                fix_tree /etc/epgimport
                [ -f /tmp/epg.dat ] && rm -f /tmp/epg.dat 2>/dev/null || true
                for F in /media/hdd/epg.dat /media/usb/epg.dat /etc/enigma2/epg.dat; do
                    [ -f "$F" ] && chmod 644 "$F" 2>/dev/null || true
                done
                install_if_available enigma2-plugin-extensions-epgimport epgimport
                sync
            }

            repair_picons(){
                echo "[4] Repairing picons..."
                ACTIVE=""
                for D in /media/hdd/picon /media/usb/picon /usr/share/enigma2/picon; do
                    if [ -d "$D" ]; then
                        fix_tree "$D"
                        [ -z "$ACTIVE" ] && ACTIVE="$D"
                    fi
                done
                if [ -n "$ACTIVE" ]; then
                    if [ -L /picon ]; then
                        ln -sfn "$ACTIVE" /picon 2>/dev/null || true
                    elif [ ! -e /picon ]; then
                        ln -s "$ACTIVE" /picon 2>/dev/null || true
                    fi
                fi
                ls -ld /picon /usr/share/enigma2/picon /media/hdd/picon /media/usb/picon 2>/dev/null || true
            }

            repair_serviceapp(){
                echo "[5] Repairing ServiceApp..."
                opkg update || true
                reinstall_detected_or_first enigma2-plugin-systemplugins-serviceapp serviceapp || true
                install_if_available exteplayer3 gstplayer ffmpeg uchardet
            }

            repair_streamlink(){
                echo "[6] Repairing Streamlink..."
                opkg update || true
                install_if_available enigma2-plugin-extensions-streamlinkwrapper enigma2-plugin-extensions-streamlinkproxy streamlinksrv python3-streamlink python-streamlink streamlink python3-yt-dlp python-youtube-dl
                ps | grep -Ei 'streamlink|streamlinksrv' | grep -v grep || true
            }

            case "$MODE" in
                full)
                    repair_permissions
                    repair_softcam
                    repair_epg
                    repair_picons
                    repair_serviceapp
                    repair_streamlink
                    ;;
                permissions) repair_permissions ;;
                softcam) repair_softcam ;;
                epg) repair_epg ;;
                picons) repair_picons ;;
                serviceapp) repair_serviceapp ;;
                streamlink) repair_streamlink ;;
                *) echo "Unknown repair mode: $MODE"; exit 1 ;;
            esac

            echo ""
            echo "Done."
            sync
        '''
        return cmd.replace("__MODE__", mode)

    def _get_report_output_path(self):
        path = self._get_backup_path()
        if path:
            return path
        return "/tmp/"

    def _make_timestamp(self):
        try:
            return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        except Exception:
            return time.strftime("%Y%m%d_%H%M%S")

    def backup_full_enigma2(self):
        path = self._get_backup_path()
        if not path:
            msg = "Brak nośnika HDD/USB." if self.lang == 'PL' else "No HDD/USB device found."
            show_message_compat(self.sess, msg, MessageBox.TYPE_ERROR)
            return
        ts = self._make_timestamp()
        out_file = os.path.join(path, "aio_full_enigma2_backup_{}.tar.gz".format(ts))
        cmd = r'''
            set -e
            OUT="{out_file}"
            WORK="/tmp/aio_full_backup_{ts}"
            mkdir -p "{path}"
            rm -rf "$WORK"
            mkdir -p "$WORK"
            mkdir -p "$WORK/meta"

            [ -d /etc/enigma2 ] && cp -a /etc/enigma2 "$WORK/"
            if [ -d /etc/tuxbox/config ]; then
                mkdir -p "$WORK/etc_tuxbox"
                cp -a /etc/tuxbox/config "$WORK/etc_tuxbox/"
            fi
            [ -d /usr/keys ] && cp -a /usr/keys "$WORK/"
            [ -d /etc/opkg ] && cp -a /etc/opkg "$WORK/"
            [ -f /etc/issue ] && cp -a /etc/issue "$WORK/meta/issue.txt" || true
            [ -f /etc/image-version ] && cp -a /etc/image-version "$WORK/meta/image-version.txt" || true
            [ -f /etc/vtiversion.info ] && cp -a /etc/vtiversion.info "$WORK/meta/vtiversion.info" || true
            uname -a > "$WORK/meta/uname.txt" 2>/dev/null || true
            opkg list-installed > "$WORK/meta/opkg_list-installed.txt" 2>/dev/null || true
            date > "$WORK/meta/created_at.txt" 2>/dev/null || true

            tar -czf "$OUT" -C "$WORK" .
            rm -rf "$WORK"
            echo "Backup zapisany do: $OUT"
        '''.format(out_file=out_file, path=path, ts=ts)
        title = "Backup Pełny Enigma2" if self.lang == 'PL' else "Full Enigma2 Backup"
        console_screen_open(self.sess, title, [cmd], close_on_finish=False)

    def export_system_report(self):
        out_dir = self._get_report_output_path()
        ts = self._make_timestamp()
        out_file = os.path.join(out_dir, "aio_system_report_{}.txt".format(ts))
        title = "Eksport Raportu Systemowego" if self.lang == 'PL' else "Export System Report"
        cmd = r'''
            OUT="{out_file}"
            mkdir -p "{out_dir}"
            echo "AIO Panel - System Report" > "$OUT"
            echo "Generated: $(date)" >> "$OUT"
            echo "Plugin version: {ver}" >> "$OUT"
            echo "Python branch: {py_branch}" >> "$OUT"
            echo "" >> "$OUT"

            echo "=== IMAGE / SYSTEM ===" >> "$OUT"
            uname -a >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"
            [ -f /etc/issue ] && {{ echo "--- /etc/issue ---"; cat /etc/issue; echo ""; }} >> "$OUT" 2>/dev/null || true
            [ -f /etc/image-version ] && {{ echo "--- /etc/image-version ---"; cat /etc/image-version; echo ""; }} >> "$OUT" 2>/dev/null || true
            [ -f /etc/vtiversion.info ] && {{ echo "--- /etc/vtiversion.info ---"; cat /etc/vtiversion.info; echo ""; }} >> "$OUT" 2>/dev/null || true
            echo "=== UPTIME ===" >> "$OUT"
            uptime >> "$OUT" 2>/dev/null || cat /proc/uptime >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"

            echo "=== CPU ===" >> "$OUT"
            grep -E '^(system type|machine|model name|Hardware|processor|cpu model|BogoMIPS)' /proc/cpuinfo >> "$OUT" 2>/dev/null || cat /proc/cpuinfo >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"

            echo "=== MEMORY ===" >> "$OUT"
            grep -E '^(MemTotal|MemFree|MemAvailable|Buffers|Cached|SwapTotal|SwapFree)' /proc/meminfo >> "$OUT" 2>/dev/null || cat /proc/meminfo >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"

            echo "=== DISKS ===" >> "$OUT"
            df -h >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"

            echo "=== MOUNTS ===" >> "$OUT"
            mount >> "$OUT" 2>/dev/null || cat /proc/mounts >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"

            echo "=== NETWORK ===" >> "$OUT"
            ip -4 addr >> "$OUT" 2>/dev/null || ifconfig >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"
            ip route >> "$OUT" 2>/dev/null || route -n >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"
            [ -f /etc/resolv.conf ] && cat /etc/resolv.conf >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"
            ping -c 1 -W 2 1.1.1.1 >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"

            echo "=== CAM / SERVICES ===" >> "$OUT"
            ps | grep -E 'oscam|ncam|softcam' | grep -v grep >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"

            echo "=== PACKAGES (selected) ===" >> "$OUT"
            opkg list-installed | grep -Ei 'oscam|ncam|softcam|streamlink|serviceapp|exteplayer3|xstreamity|e2iplayer|youtube|jedi|epg|kodi|vavoo|tvgarden|simplezooom|simplezoom|footonsat' >> "$OUT" 2>/dev/null || opkg list-installed >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"

            echo "=== ENIGMA2 CONFIG ===" >> "$OUT"
            ls -la /etc/enigma2 >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"
            echo "Report saved to: $OUT"
        '''.format(out_file=out_file, out_dir=out_dir, ver=VER, py_branch=('Py3' if IS_PY3 else 'Py2'))
        console_screen_open(self.sess, title, [cmd], close_on_finish=False)

    def smart_cleanup(self):
        removed = _cleanup_owned_tmp(PLUGIN_TMP_PATH, 3600)
        gc.collect()
        cmd = "find %s -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true; find %s -type f \\( -name '*.pyc' -o -name '*.pyo' \\) -delete 2>/dev/null || true" % (_safe_shell_arg(PLUGIN_PATH), _safe_shell_arg(PLUGIN_PATH))
        def done(result):
            show_message_compat(self.sess, ('Bezpieczne czyszczenie zakończone. Usunięto elementy robocze AIO: %s. Nie usunięto logów użytkownika ani list OPKG.' % removed if self.lang == 'PL' else 'Safe cleanup completed. Removed AIO work items: %s. User logs and OPKG lists were preserved.' % removed), timeout=9)
        run_command_in_background(self.sess, 'Smart Cleanup', [cmd], callback_on_finish=done)

    def clean_broken_plugins(self):
        report = '/tmp/aio_plugin_compatibility_report.txt'
        cmd = r'''PY=$(command -v python3 || command -v python || true)
    [ -n "$PY" ] || { echo 'Brak Pythona'; exit 1; }
    : > %s
    BASE=/usr/lib/enigma2/python/Plugins
    for GROUP in Extensions SystemPlugins; do
      [ -d "$BASE/$GROUP" ] || continue
      for DIR in "$BASE/$GROUP"/*; do
        [ -f "$DIR/plugin.py" ] || continue
        NAME=$(basename "$DIR")
        if "$PY" -m py_compile "$DIR/plugin.py" >/tmp/aio_pycheck.log 2>&1; then
          echo "OK|$GROUP/$NAME" >> %s
        else
          echo "ERROR|$GROUP/$NAME|$(tr '\n' ' ' </tmp/aio_pycheck.log)" >> %s
        fi
      done
    done
    cat %s
    ''' % tuple(_safe_shell_arg(report) for _ in range(4))
        console_screen_open(self.sess, ('Raport zgodności wtyczek — bez usuwania' if self.lang == 'PL' else 'Plugin compatibility report — no deletion'), [cmd], close_on_finish=False)

    def _get_backup_path(self):
        candidates = []
        try:
            with open('/proc/mounts', 'r') as handle:
                mounts = [line.split()[1] for line in handle if len(line.split()) >= 2]
        except Exception:
            mounts = []
        for path in mounts:
            if re.match(r'^/media/(hdd|usb|mmc|sdcard|cf)(?:\d+)?$', path) and os.path.isdir(path) and os.access(path, os.W_OK):
                candidates.append(path)
        if candidates:
            candidates.sort(key=lambda x: shutil_disk_usage(x).free if os.path.exists(x) else 0, reverse=True)
            return os.path.join(candidates[0], 'aio_backups') + '/'
        fallback = '/home/root/aio_backups/'
        try:
            if not os.path.isdir(fallback): os.makedirs(fallback)
            return fallback
        except Exception:
            return None

    def _find_channel_backup_file(self, path):
        latest = os.path.join(path, "aio_channels_backup.tar.gz")
        if fileExists(latest):
            return latest
        try:
            candidates = []
            for fn in os.listdir(path):
                if fn.startswith("aio_channels_backup_") and fn.endswith(".tar.gz"):
                    candidates.append(os.path.join(path, fn))
            candidates.sort(reverse=True)
            if candidates:
                return candidates[0]
        except Exception as e:
            print("[AIO Panel] Backup search error:", e)
        return latest

    def backup_lists(self):
        path = self._get_backup_path()
        if not path:
            show_message_compat(self.sess, 'Brak zapisywalnego miejsca na backup.', MessageBox.TYPE_ERROR); return
        status = os.path.join(PLUGIN_TMP_PATH, 'backup_channels_%s.status' % int(time.time() * 1000))
        cmd = '/bin/sh %s %s %s' % tuple(_safe_shell_arg(x) for x in (os.path.join(PLUGIN_PATH, 'backup_channels_script.sh'), path, status))
        def done(result):
            text = _read_text_file(status, '').strip()
            if result and result.get('success') and text.startswith('OK'):
                show_message_compat(self.sess, 'Backup list zapisany w:\n%s' % path, timeout=8)
            else:
                show_message_compat(self.sess, 'Backup list nie powiódł się.\n%s' % text, MessageBox.TYPE_ERROR)
        run_command_in_background(self.sess, 'Backup list kanałów', [cmd], callback_on_finish=done)

    def restore_lists(self):
        path = self._get_backup_path()
        if not path: return
        pointer = os.path.join(path, 'aio_channels_backup.latest')
        archive = ''
        if os.path.isfile(pointer):
            archive = _read_text_file(pointer, '').strip()
            if archive and not archive.startswith('/'): archive = os.path.join(path, archive)
        if not archive or not os.path.isfile(archive):
            found = sorted([os.path.join(path, x) for x in os.listdir(path) if x.startswith('aio_channels_backup_') and x.endswith('.tar.gz')], reverse=True) if os.path.isdir(path) else []
            archive = found[0] if found else ''
        if not archive:
            show_message_compat(self.sess, 'Brak backupu list kanałów.', MessageBox.TYPE_ERROR); return
        msg = 'Przywrócić listy z:\n%s?\n\nOperacja ma automatyczny rollback i zawsze ponownie uruchamia GUI.' % archive
        def confirmed(answer):
            if not answer: return
            status = os.path.join(PLUGIN_TMP_PATH, 'restore_channels_%s.status' % int(time.time() * 1000))
            cmd = '/bin/sh %s %s %s' % tuple(_safe_shell_arg(x) for x in (os.path.join(PLUGIN_PATH, 'restore_channels_script.sh'), archive, status))
            console_screen_open(self.sess, 'Bezpieczne przywracanie list', [cmd], close_on_finish=False)
        self.sess.openWithCallback(confirmed, MessageBox, msg, MessageBox.TYPE_YESNO, default=False)

    def backup_oscam(self):
        path = self._get_backup_path()
        if not path: show_message_compat(self.sess, 'Brak miejsca na backup.', MessageBox.TYPE_ERROR); return
        status = os.path.join(PLUGIN_TMP_PATH, 'backup_oscam_%s.status' % int(time.time() * 1000))
        cmd = '/bin/sh %s %s %s' % tuple(_safe_shell_arg(x) for x in (os.path.join(PLUGIN_PATH, 'backup_oscam_script.sh'), path, status))
        run_command_in_background(self.sess, 'Backup OSCam', [cmd], callback_on_finish=lambda result: show_message_compat(self.sess, ('Backup OSCam zakończony.' if result and result.get('success') else 'Backup OSCam nie powiódł się.'), MessageBox.TYPE_INFO if result and result.get('success') else MessageBox.TYPE_ERROR))

    def restore_oscam(self):
        path = self._get_backup_path()
        if not path: return
        pointer = os.path.join(path, 'aio_oscam_config_backup.latest')
        archive = _read_text_file(pointer, '').strip() if os.path.isfile(pointer) else ''
        if archive and not archive.startswith('/'): archive = os.path.join(path, archive)
        if not archive or not os.path.isfile(archive):
            found = sorted([os.path.join(path, x) for x in os.listdir(path) if x.startswith('aio_oscam_config_backup_') and x.endswith('.tar.gz')], reverse=True) if os.path.isdir(path) else []
            archive = found[0] if found else ''
        if not archive: show_message_compat(self.sess, 'Brak backupu OSCam.', MessageBox.TYPE_ERROR); return
        def confirmed(answer):
            if not answer: return
            status = os.path.join(PLUGIN_TMP_PATH, 'restore_oscam_%s.status' % int(time.time() * 1000))
            cmd = '/bin/sh %s %s %s' % tuple(_safe_shell_arg(x) for x in (os.path.join(PLUGIN_PATH, 'restore_oscam_script.sh'), archive, status))
            run_command_in_background(self.sess, 'Przywracanie OSCam', [cmd], callback_on_finish=lambda result: show_message_compat(self.sess, ('Konfiguracja OSCam została przywrócona.' if result and result.get('success') else 'Przywracanie OSCam nie powiodło się.'), MessageBox.TYPE_INFO if result and result.get('success') else MessageBox.TYPE_ERROR))
        self.sess.openWithCallback(confirmed, MessageBox, 'Przywrócić konfigurację OSCam z:\n%s?' % archive, MessageBox.TYPE_YESNO, default=False)
    def run_network_diagnostics(self):
        self.sess.open(NetworkDiagnosticsSummaryScreen, self.lang)

    def _ask_reboot_after_install(self, *args):
        msg = (
            "Instalacja lub aktualizacja została zakończona.\n\nJeżeli wszystko działa, wykonaj restart tunera ręcznie z menu zasilania. AIO Panel 14.0.0 nie wymusza automatycznego restartu, żeby nie powodować pętli restartów po wadliwej zewnętrznej wtyczce.\n\nWykonać pełny restart teraz?"
            if self.lang == 'PL' else
            "The install/update has finished.\n\nIf everything works, reboot the receiver manually from the power menu. AIO Panel 14.0.0 does not force an automatic reboot to avoid reboot loops caused by faulty external plugins.\n\nReboot now?"
        )

        def _open_reboot_prompt():
            try:
                self.sess.openWithCallback(
                    lambda ret: self.sess.open(TryQuitMainloop, 2) if ret else None,
                    MessageBox,
                    msg,
                    MessageBox.TYPE_YESNO,
                    default=False
                )
            except Exception as e:
                print("[AIO Panel] Reboot prompt open error:", e)

        if reactor.running:
            reactor.callLater(0.2, _open_reboot_prompt)
        else:
            _open_reboot_prompt()

    def _is_py2_incompatible_install(self, title, cmdlist):
        try:
            combined = (title + " " + " ".join(cmdlist)).lower()
        except Exception:
            combined = title.lower()
        py3_markers = [
            "python3", "py3", "_py3", "python3/", "refs/heads/python3",
            "e2kodi", "youtube_py3", "enigma2-plugin-youtube"
        ]
        for marker in py3_markers:
            if marker in combined:
                return True
        return False


    def _aio_tmp_name_for_url(self, url, suffix):
        try:
            token = re.sub(r"[^A-Za-z0-9]+", "_", ensure_unicode(url))[-70:].strip("_")
            if not token:
                token = "download"
            return "/tmp/aio_%s%s" % (token, suffix)
        except Exception:
            return "/tmp/aio_download%s" % suffix

    def _extract_first_url_from_cmd(self, cmd):
        try:
            urls = re.findall(r"https?://[^\s'\"|;)]+", ensure_unicode(cmd))
            return urls[0] if urls else ""
        except Exception:
            return ""

    def _command_has_github_download(self, cmd):
        try:
            low = ensure_unicode(cmd).lower()
            return ("github.com" in low or "raw.githubusercontent.com" in low)
        except Exception:
            return False

    def _build_openpli_safe_installer_command(self, title, cmd):
        """Return an audited local command for supported legacy installers."""
        try:
            return self._safe_legacy_action_command(title, cmd)
        except Exception as e:
            print("[AIO Panel] Safe installer translation error:", e)
            return None


    def _sanitize_install_command(self, cmd):
        """Remove automatic reboots and fail closed for every network installer."""
        try:
            original = ensure_unicode(cmd)
            replacements = [
                "&& killall -9 enigma2", "; killall -9 enigma2", "killall -9 enigma2",
                "&& reboot", "; reboot", "&& init 6", "; init 6",
                "&& killall enigma2", "; killall enigma2", "killall enigma2"
            ]
            safe = original
            for item in replacements:
                safe = safe.replace(item, " && echo 'AIO Panel: automatyczny restart pominięty; wykonaj go ręcznie.'")
            if re.search(r'https?://|\bwget\b|\bcurl\b', safe, re.I):
                translated = self._build_openpli_safe_installer_command("", safe)
                if not translated:
                    return "echo 'AIO Panel: zewnętrzna komenda została zablokowana przez zasady bezpieczeństwa.'; exit 126"
                return translated
            return safe
        except Exception as e:
            print('[AIO Panel] Command sanitization error:', e)
            return "echo 'AIO Panel: nie można bezpiecznie przygotować polecenia.'; exit 126"


    def _open_console_install_action_confirmed(self, title, cmdlist):
        safe_cmdlist = [self._sanitize_install_command(c) for c in cmdlist]
        console_screen_open(self.sess, title, safe_cmdlist, callback=self._ask_reboot_after_install, close_on_finish=False)

    def _open_console_install_action(self, title, cmdlist):
        if IS_PY2 and self._is_py2_incompatible_install(title, cmdlist):
            msg = (
                "Ta pozycja wygląda na przeznaczoną dla Pythona 3 i została zablokowana na Pythonie 2.\n\nTo zabezpieczenie dodano w AIO Panel 14.0.0, ponieważ instalacja pakietów Py3 na obrazach Py2 może powodować crashe lub bootloop."
                if self.lang == 'PL' else
                "This item appears to be intended for Python 3 and has been blocked on Python 2.\n\nThis safeguard was added in AIO Panel 14.0.0 because installing Py3 packages on Py2 images may cause crashes or boot loops."
            )
            show_message_compat(self.sess, msg, MessageBox.TYPE_ERROR, timeout=12)
            return

        msg = (
            "Uruchomić zewnętrzny instalator?\n\nAIO Panel nie wymusi restartu GUI po zakończeniu. Jeżeli instalator danej wtyczki jest wadliwy albo niezgodny z obrazem/Pythonem, system może zgłaszać błędy dopiero po restarcie.\n\nFunkcja: %s" % title
            if self.lang == 'PL' else
            "Run external installer?\n\nAIO Panel will not force a GUI restart after finishing. If the external plugin installer is faulty or incompatible with the image/Python version, errors may appear after reboot.\n\nFunction: %s" % title
        )
        try:
            self.sess.openWithCallback(
                lambda ret: self._open_console_install_action_confirmed(title, cmdlist) if ret else None,
                MessageBox,
                msg,
                MessageBox.TYPE_YESNO,
                default=False
            )
        except Exception:
            self._open_console_install_action_confirmed(title, cmdlist)

    def restart_gui(self): self.sess.open(TryQuitMainloop, 3)

    def _reload_channel_lists_core(self):
        """Reload Enigma2 services/bouquets after installing channel lists without GUI restart."""
        try:
            os.system("sync")
        except Exception:
            pass
        try:
            db = eDVBDB.getInstance()
            db.reloadServicelist()
            db.reloadBouquets()
        except Exception as e:
            print("[AIO Panel] Python channel reload error:", e)
        try:
            os.system("(wget -qO- -T 3 'http://127.0.0.1/web/servicelistreload?mode=0' >/dev/null 2>&1; wget -qO- -T 3 'http://127.0.0.1/web/servicelistreload?mode=1' >/dev/null 2>&1; wget -qO- -T 3 'http://127.0.0.1/web/servicelistreload?mode=2' >/dev/null 2>&1) &")
        except Exception as e:
            print("[AIO Panel] OpenWebif channel reload error:", e)

    def reload_settings_python(self, *args):
        def _pass_one():
            self._reload_channel_lists_core()
            reactor.callLater(1.2, _pass_two)

        def _pass_two():
            self._reload_channel_lists_core()
            reactor.callLater(1.8, _pass_three)

        def _pass_three():
            self._reload_channel_lists_core()
            msg = "Listy kanałów przeładowane." if self.lang == 'PL' else "Channel lists reloaded."
            show_message_compat(self.sess, msg, timeout=4)

        reactor.callLater(0.4, _pass_one)
    def clear_oscam_password(self):
        title = "Kasowanie hasła Oscam" if self.lang == 'PL' else "Clear Oscam Password"
        cmd = r'''
            {helpers}
            aio_require_oscam_dirs
            STAMP=$(date +%Y%m%d_%H%M%S)
            echo "$DIRS" | while IFS= read -r D; do
                [ -f "$D/oscam.conf" ] || continue
                cp -a "$D/oscam.conf" "$D/oscam.conf.aio-bak-$STAMP" 2>/dev/null || true
                sed -i '/^[[:space:]]*httppwd[[:space:]]*=/d' "$D/oscam.conf"
                echo "Wyczyszczono hasło w: $D/oscam.conf"
            done
            sync
            aio_soft_restart_oscam
        '''.format(helpers=_oscam_detect_shell_functions())
        console_screen_open(self.sess, title, [cmd], close_on_finish=False)
    def manage_dvbapi(self):
        opt = [("Kasuj zawartość", "clear")] if self.lang == 'PL' else [("Clear file", "clear")]
        self.sess.openWithCallback(self._manage_dvbapi_selected, ChoiceBox, title="oscam.dvbapi", list=opt)

    def _manage_dvbapi_selected(self, choice):
        if not choice:
            return
        if choice[1] == "clear":
            cmd = r'''
                {helpers}
                aio_require_oscam_dirs
                STAMP=$(date +%Y%m%d_%H%M%S)
                echo "$DIRS" | while IFS= read -r D; do
                    [ -d "$D" ] || continue
                    [ -f "$D/oscam.dvbapi" ] && cp -a "$D/oscam.dvbapi" "$D/oscam.dvbapi.aio-bak-$STAMP" 2>/dev/null || true
                    : > "$D/oscam.dvbapi"
                    [ -f "$D/oscam.dvbap" ] && : > "$D/oscam.dvbap" || true
                    chmod 644 "$D/oscam.dvbapi" 2>/dev/null || true
                    echo "Wyczyszczono: $D/oscam.dvbapi"
                done
                sync
                aio_soft_restart_oscam
            '''.format(helpers=_oscam_detect_shell_functions())
            run_command_in_background(
                self.sess,
                "Kasowanie oscam.dvbapi" if self.lang == 'PL' else "Clearing oscam.dvbapi",
                [cmd]
            )

    def update_oscam_dvbapi_poland(self):
        src = os.path.join(PLUGIN_PATH, "oscam.dvbapi.poland")
        if not fileExists(src):
            show_message_compat(self.sess, "Brak pliku oscam.dvbapi.poland w paczce AIO." if self.lang == 'PL' else "Missing oscam.dvbapi.poland file in AIO package.", MessageBox.TYPE_ERROR)
            return
        title = "oscam.dvbapi - aktualizacja Poland" if self.lang == 'PL' else "oscam.dvbapi - Poland update"
        cmd = r'''
            set -u
            SRC="{src}"
            STAMP=$(date +%Y%m%d_%H%M%S)
            {helpers}
            echo "=== AIO Panel 14.0.0: oscam.dvbapi Poland ==="
            [ -f "$SRC" ] || {{ echo "Brak pliku wzorcowego: $SRC"; exit 1; }}
            aio_require_oscam_dirs
            echo "$DIRS" | while IFS= read -r D; do
                [ -n "$D" ] || continue
                [ -d "$D" ] || continue
                if [ -f "$D/oscam.dvbapi" ]; then
                    cp -a "$D/oscam.dvbapi" "$D/oscam.dvbapi.aio-bak-$STAMP" 2>/dev/null || true
                fi
                cp -f "$SRC" "$D/oscam.dvbapi"
                chmod 644 "$D/oscam.dvbapi" 2>/dev/null || true
                echo "Zaktualizowano: $D/oscam.dvbapi"
            done
            sync
            aio_soft_restart_oscam
            echo "Gotowe."
        '''.format(src=src, helpers=_oscam_detect_shell_functions())
        console_screen_open(self.sess, title, [cmd], close_on_finish=False)

    def set_system_password(self):
        def callback(password):
            password = ensure_unicode(password)
            if not password: return
            fd, temp_path = tempfile.mkstemp(prefix='aio-pass-', dir=PLUGIN_TMP_PATH)
            try:
                os.write(fd, ensure_str('root:%s\n' % password).encode('utf-8') if IS_PY3 else ensure_str('root:%s\n' % password))
            finally:
                os.close(fd)
            os.chmod(temp_path, 0o600)
            cmd = 'chpasswd < %s; RC=$?; rm -f %s; exit $RC' % (_safe_shell_arg(temp_path), _safe_shell_arg(temp_path))
            run_command_in_background(self.sess, 'Zmiana hasła root', [cmd])
        kwargs = {'title': 'Nowe hasło root'}
        if Input is not None:
            password_type = getattr(Input, 'PASSWORD', getattr(Input, 'PIN', None))
            if password_type is not None: kwargs['type'] = password_type
        self.sess.openWithCallback(callback, InputBox, **kwargs)
    def restart_oscam(self, *args):
        status = os.path.join(PLUGIN_TMP_PATH, 'oscam_control_%s.status' % int(time.time() * 1000))
        cmd = '/bin/sh %s restart %s' % (_safe_shell_arg(os.path.join(PLUGIN_PATH, 'oscam_control_script.sh')), _safe_shell_arg(status))
        run_command_in_background(self.sess, 'Restart OSCam/NCam', [cmd])
    def show_uninstall_manager(self):
        self.sess.open(UninstallManagerScreen, self.lang)

    def show_plugin_update_manager(self):
        self.sess.open(PluginUpdateManagerScreen, self.lang)
    def install_best_oscam(self):
        title = "OSCam-Emu - Instalator i aktywacja" if self.lang == 'PL' else "OSCam-Emu - Install and activate"
        script_path = os.path.join(PLUGIN_PATH, 'install_oscam_emu_script.sh')
        status_path = os.path.join(PLUGIN_TMP_PATH, 'manual_oscam_%s.status' % int(time.time() * 1000))
        if not os.path.exists(script_path):
            show_message_compat(self.sess, 'Brak pliku install_oscam_emu_script.sh.', MessageBox.TYPE_ERROR)
            return
        cmd = 'chmod 755 {script} && /bin/sh {script} {status}; RC=$?; echo; cat {status} 2>/dev/null || true; exit $RC'.format(
            script=_safe_shell_arg(script_path),
            status=_safe_shell_arg(status_path)
        )
        self._open_console_install_action(title, [cmd])

    def install_softcam_script(self):
        title = 'Softcam - Instalator' if self.lang == 'PL' else 'Softcam - Installer'
        status = os.path.join(PLUGIN_TMP_PATH, 'softcam_feed_%s.status' % int(time.time() * 1000))
        cmd = '/bin/sh %s %s' % (_safe_shell_arg(os.path.join(PLUGIN_PATH, 'install_softcam_feed_safe.sh')), _safe_shell_arg(status))
        def finished(result):
            text = _read_text_file(status, '').strip()
            try: os.remove(status)
            except Exception: pass
            if text.startswith('OK'):
                msg = 'Feed Softcam lub OSCam jest dostępny.' if self.lang == 'PL' else 'Softcam feed or OSCam is available.'
                typ = MessageBox.TYPE_INFO
            elif text.startswith('WARN'):
                msg = ('Zewnętrzny feed Softcam jest niedostępny lub nie został potwierdzony. Nie zablokowano pozostałych funkcji. Log: /tmp/aio_softcam_feed.log' if self.lang == 'PL' else 'The external Softcam feed is unavailable or unconfirmed. Other functions were not blocked. Log: /tmp/aio_softcam_feed.log')
                typ = MessageBox.TYPE_INFO
            else:
                msg = ('Instalacja feedu Softcam nie powiodła się. Log: /tmp/aio_softcam_feed.log' if self.lang == 'PL' else 'Softcam feed installation failed. Log: /tmp/aio_softcam_feed.log')
                typ = MessageBox.TYPE_ERROR
            show_message_compat(self.sess, msg, typ, timeout=14)
        run_command_in_background(self.sess, title, [cmd], callback_on_finish=finished)

    def install_levi45_oscam(self):
        title = "Oscam Levi45"
        raw = "wget -q https://raw.githubusercontent.com/levi-45/Levi45Emulator/main/installer.sh -O - | /bin/sh"
        self._run_safe_legacy_action(title, raw)

    def install_ncam_feed(self):
        title = "NCam (Feed - najnowszy)" if self.lang == 'PL' else "NCam (Feed - latest)"
        cmd = "opkg update && (opkg install --force-reinstall ncam || opkg install --force-reinstall softcam-ncam || opkg install --force-reinstall enigma2-plugin-softcams-ncam || opkg install --force-reinstall enigma2-plugin-softcams-ncam-emu)"
        self._open_console_install_action(title, [cmd])
    def install_iptv_dream_simplified(self):
        raw = "wget -qO- https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh | /bin/sh"
        self._run_safe_legacy_action("IPTV Dream Installer", raw)

    def install_iptv_deps(self):
        title = "Konfiguracja IPTV - zależności" if self.lang == 'PL' else "IPTV Configuration - dependencies"
        
        # --- ZALEŻNOŚCI UNIWERSALNE (Py2 vs Py3) ---
        if IS_PY3:
            # Python 3
            cmds = [
                "opkg update",
                "opkg install enigma2-plugin-systemplugins-serviceapp",
                "opkg install exteplayer3",
                "opkg install ffmpeg",
                "opkg install python3-youtube-dl",
                "opkg install python3-yt-dlp",
                "opkg install enigma2-plugin-extensions-ytdlpwrapper",
                "opkg install enigma2-plugin-extensions-ytdlwrapper",
                "opkg install enigma2-plugin-extensions-streamlinkwrapper",
                "opkg install streamlinksrv",
            ]
        else:
            # Python 2 (Starsze nazewnictwo)
            cmds = [
                "opkg update",
                "opkg install enigma2-plugin-systemplugins-serviceapp",
                "opkg install exteplayer3",
                "opkg install ffmpeg",
                "opkg install python-youtube-dl",
                "opkg install streamlinksrv || true",
            ]

        self._open_console_install_action(title, cmds)

    
    def open_system_monitor(self): self.sess.open(SystemMonitorScreen, self.lang)
    def open_log_viewer(self): self.sess.open(LogViewerScreen, self.lang)
    def open_cron_manager(self): self.sess.open(CronManagerScreen, self.lang)
    def open_service_manager(self): self.sess.open(ServiceManagerScreen, self.lang)
    def open_system_info(self): self.sess.open(SystemInfoScreen, self.lang)
    
    # === NOWA LOGIKA AKTUALIZACJI ===

    # ... (Metody aktualizacji bez zmian) ...


# === Network Diagnostics: readable summary screen (v6.0) ===
class NetworkDiagnosticsSummaryScreen(Screen):
    skin_large = """
    <screen position="center,center" size="980,560" title="Network Diagnostics">
        <widget name="text" position="20,20" size="940,490" font="Regular;22" />
        <widget name="hint" position="20,520" size="940,30" font="Regular;20" halign="center" />
    </screen>"""
    skin_small = """
    <screen position="center,center" size="690,430" title="Network Diagnostics">
        <widget name="text" position="15,15" size="660,355" font="Regular;17" />
        <widget name="hint" position="15,388" size="660,26" font="Regular;17" halign="center" />
    </screen>"""

    def __init__(self, session, lang='PL'):
        self.skin = self.skin_small if _is_small_ui() else self.skin_large
        Screen.__init__(self, session)
        self.session = session
        self.lang = lang or 'PL'
        self._closed = False
        self.onClose.append(self._mark_closed)

        if ScrollLabel:
            self["text"] = ScrollLabel("")
        else:
            self["text"] = Label("")

        self["hint"] = Label("OK / EXIT")
        self["actions"] = ActionMap(["OkCancelActions"], {
            "ok": self.close,
            "cancel": self.close
        }, -1)

        self.onShown.append(self._start)

    def _mark_closed(self):
        self._closed = True

    def _start(self):
        if self._closed:
            return
        self.setTitle(TRANSLATIONS[self.lang].get("net_diag_title", "Network Diagnostics"))
        self["text"].setText(TRANSLATIONS[self.lang].get("net_diag_wait", "Please wait..."))
        Thread(target=self._worker).start()

    def _run_cmd(self, cmd):
        try:
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
            out = out or b""
            err = err or b""
            if IS_PY3:
                return p.returncode, out.decode('utf-8', 'ignore').strip(), err.decode('utf-8', 'ignore').strip()
            else:
                return p.returncode, out.strip(), err.strip()
        except Exception as e:
            return 1, "", str(e)

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return ""

    def _get_route_info(self):
        iface, gw = "", ""
        rc, out, _ = self._run_cmd("ip route show default 2>/dev/null")
        if rc == 0 and out:
            m = re.search(r"default\s+via\s+([0-9\.]+)\s+dev\s+(\S+)", out)
            if m:
                gw, iface = m.group(1), m.group(2)
        if not iface or not gw:
            rc, out, _ = self._run_cmd("route -n | grep '^0.0.0.0' | head -n 1")
            if out:
                parts = out.split()
                if len(parts) >= 8:
                    gw = gw or parts[1]
                    iface = iface or parts[7]
        return iface, gw

    def _get_dns(self):
        dns = []
        try:
            if os.path.exists('/etc/resolv.conf'):
                with open('/etc/resolv.conf', 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('nameserver'):
                            p = line.split()
                            if len(p) >= 2:
                                dns.append(p[1])
        except Exception:
            pass
        return dns

    def _get_public_ip(self):
        for url in (
            'https://api.ipify.org',
            'https://ifconfig.me/ip',
        ):
            rc, out, _ = self._run_cmd("wget -qO- --timeout=10 %s" % url)
            if rc == 0 and out and re.match(r"^\d{1,3}(\.\d{1,3}){3}$", out.strip()):
                return out.strip()
        return ""

    def _ping_test(self, host='8.8.8.8'):
        rc, out, _ = self._run_cmd('ping -c 4 -W 2 %s' % host)
        loss, avg = "", ""
        if out:
            m = re.search(r"(\d+)%\s+packet\s+loss", out)
            if m:
                loss = m.group(1) + '%'
            m = re.search(r"=\s*([0-9\.]+)/([0-9\.]+)/([0-9\.]+)/([0-9\.]+)", out)
            if m:
                avg = m.group(2) + ' ms'
        return avg, loss

    def _download_speed(self):
        # Best-effort. Uses Python HTTP download of ~5 MiB.
        # UNIVERSAL FIX: Use compat imports
        try:
            # Py3
            from urllib.request import urlopen
        except ImportError:
            # Py2
            from urllib2 import urlopen

        candidates = [
            ('Cloudflare', 'https://speed.cloudflare.com/__down?bytes=10000000'),
            ('Hetzner', 'https://speed.hetzner.de/10MB.bin'),
            ('OVH', 'https://proof.ovh.net/files/10Mb.dat'),
        ]
        bytes_target = 5 * 1024 * 1024
        for name, url in candidates:
            try:
                start = time.time()
                r = urlopen(url, timeout=15)
                total = 0
                while total < bytes_target:
                    chunk = r.read(min(65536, bytes_target - total))
                    if not chunk:
                        break
                    total += len(chunk)
                try:
                    r.close()
                except Exception:
                    pass
                dt = max(time.time() - start, 0.001)
                if total >= 256 * 1024:
                    mbps = (total * 8.0) / dt / 1e6
                    return mbps, name
            except Exception:
                continue
        return None

    def _upload_speed(self):
        # Best-effort. Uses HTTP POST upload of 1 MiB.
        try:
            from urllib.request import Request, urlopen
        except ImportError:
            from urllib2 import Request, urlopen

        endpoints = [
            ('Cloudflare', 'https://speed.cloudflare.com/__up'),
            ('httpbin', 'https://httpbin.org/post'),
            ('postman', 'https://postman-echo.com/post'),
        ]
        payload = os.urandom(1024 * 1024)
        for name, url in endpoints:
            try:
                req = Request(url, data=payload)
                try:
                    req.add_header('Content-Type', 'application/octet-stream')
                except Exception:
                    pass
                start = time.time()
                r = urlopen(req, timeout=20)
                try:
                    r.read(256)
                except Exception:
                    pass
                try:
                    r.close()
                except Exception:
                    pass
                dt = max(time.time() - start, 0.001)
                mbps = (len(payload) * 8.0) / dt / 1e6
                return mbps, name
            except Exception:
                continue
        return None

    def _worker(self):
        try:
            local_ip = self._get_local_ip()
            iface, gw = self._get_route_info()
            dns = self._get_dns()
            public_ip = self._get_public_ip()
            ping_avg, ping_loss = self._ping_test('8.8.8.8')
            dl = self._download_speed()
            ul = self._upload_speed()

            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            na = TRANSLATIONS[self.lang].get('net_diag_na', 'N/A')

            lines = []
            lines.append(TRANSLATIONS[self.lang].get('net_diag_results_title', 'Network Diagnostics Results'))
            lines.append('')
            lines.append('Data/Czas: %s' % now)
            lines.append('')
            lines.append('%s %s' % (TRANSLATIONS[self.lang].get('net_diag_local_ip', 'Tuner IP (Local):'), local_ip or na))
            lines.append('Interfejs: %s' % (iface or na))
            lines.append('Brama (Gateway): %s' % (gw or na))
            lines.append('DNS: %s' % (', '.join(dns) if dns else na))
            lines.append('%s %s' % (TRANSLATIONS[self.lang].get('net_diag_ip', 'Public IP:'), public_ip or na))
            lines.append('')

            lines.append('%s %s %s' % (TRANSLATIONS[self.lang].get('net_diag_ping', 'Ping:'), ping_avg or na, ('(loss: %s)' % ping_loss) if ping_loss else ''))

            if dl:
                lines.append('%s %.2f Mbps (%s)' % (TRANSLATIONS[self.lang].get('net_diag_download', 'Download:'), dl[0], dl[1]))
            else:
                lines.append('%s %s' % (TRANSLATIONS[self.lang].get('net_diag_download', 'Download:'), na))

            if ul:
                lines.append('%s %.2f Mbps (%s)' % (TRANSLATIONS[self.lang].get('net_diag_upload', 'Upload:'), ul[0], ul[1]))
            else:
                lines.append('%s %s' % (TRANSLATIONS[self.lang].get('net_diag_upload', 'Upload:'), na))

            # Show additional interface details if available
            if iface:
                rc, out, _ = self._run_cmd('ip addr show %s 2>/dev/null' % iface)
                if out:
                    lines.append('')
                    lines.append('--- %s ---' % iface)
                    for ln in out.splitlines()[:12]:
                        lines.append(ln)

            result = "\n".join(lines)
        except Exception as e:
            result = TRANSLATIONS[self.lang].get('net_diag_error', 'Error') + "\n" + str(e)

        reactor.callFromThread(self._show_results, result)

    def _show_results(self, text):
        if self._closed:
            return
        try:
            self["text"].setText(text)
        except Exception as exc:
            print('[AIO Panel] Network result display error:', exc)
def main(session, **kwargs):
    session.open(AIOLoadingScreen)


def sessionstart(reason, session=None, **kwargs):
    # v12.0.4: no startup task in legacy runtime either.
    return None
def menu(menuid, **kwargs):
    # Register in:
    # - Main Menu (MENU button): menuid == "mainmenu"
    # - Setup -> System: menuid == "system"
    if menuid in ("system", "mainmenu"):
        # Optional: hide AIO Panel from receiver menu
        try:
            if not _get_show_in_menu_setting(True):
                return []
        except Exception:
            pass
        # Use different entry ids to avoid any potential collisions in some images.
        if menuid == "mainmenu":
            return [("AIO Panel", main, "aio_panel_main", 45)]
        return [("AIO Panel", main, "aio_panel", 45)]
    return []

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="AIO Panel",
            description="Panel All-In-One v{}".format(VER),
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="logo.png",
            fnc=main
        ),
        # Menu -> Setup -> System
        PluginDescriptor(where=PluginDescriptor.WHERE_MENU, fnc=menu),
    ]
