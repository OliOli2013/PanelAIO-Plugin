# -*- coding: utf-8 -*-
"""Panel AIO
by Paweł Pawełek | aio-iptv@wp.pl
Wersja 9.7 (AIO Extras) - Quick Start + Compatibility + Tips
UNIVERSAL VERSION (Python 2 & Python 3 Compatible)

v9.7: dodano AIO Quick Start, test zgodności systemu, lokalny changelog i tip dnia oraz ujednolicono adres kontaktowy.
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
from threading import Thread
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
except ImportError:
    # Python 2
    from urllib2 import urlopen, Request

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
        # Show/Hide AIO Panel entry in receiver main/system menu
        if ConfigYesNo is not None and not hasattr(config.plugins.panelaio, "show_in_menu"):
            config.plugins.panelaio.show_in_menu = ConfigYesNo(default=True)
    except Exception as e:
        print("[AIO Panel] Config init error:", e)

try:
    from Components.ScrollLabel import ScrollLabel
except Exception:
    ScrollLabel = None
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileExists
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
    """Funkcja wykonywana cyklicznie przez timer"""
    try:
        os.system("sync; echo 3 > /proc/sys/vm/drop_caches")
        print("[AIO Panel] Auto RAM Cleaner: Pamięć wyczyszczona automatycznie.")
    except Exception as e:
        print("[AIO Panel] Auto RAM Cleaner Error:", e)

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

VER = _read_local_version("9.5")
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
            sz = getDesktop(0).size()
            return int(sz.width()), int(sz.height())
    except Exception:
        pass
    return 1280, 720

def _is_hd_ui():
    w, h = _desktop_size()
    return w <= 1280 or h <= 720

def _super_wizard_choice_skin():
    if _is_hd_ui():
        return """
    <screen position="center,center" size="760,460" title="Super Konfigurator">
        <widget name="list" position="20,20" size="720,270" scrollbarMode="showOnDemand" />
        <widget name="description" position="20,305" size="720,95" font="Regular;20" halign="center" valign="center" foregroundColor="#0000C2FF" />
        <widget name="actions" position="20,420" size="720,24" font="Regular;18" halign="right" />
    </screen>"""
    return """
    <screen position="center,center" size="800,500" title="Super Konfigurator">
        <widget name="list" position="20,20" size="760,300" scrollbarMode="showOnDemand" />
        <widget name="description" position="20,340" size="760,100" font="Regular;22" halign="center" valign="center" foregroundColor="#0000C2FF" />
        <widget name="actions" position="20,460" size="760,30" font="Regular;20" halign="right" />
    </screen>"""

def _wizard_progress_skin():
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
    if _is_hd_ui():
        return """
    <screen position="center,center" size="760,560" title="Wsparcie / Support" backgroundColor="#000B0F14">
        <eLabel position="0,0" size="760,560" backgroundColor="#000B0F14" zPosition="-1" />
        <eLabel position="0,0" size="760,70" backgroundColor="#00121824" zPosition="-1" />
        <widget name="title" position="20,15" size="720,34" font="Regular;26" halign="center" foregroundColor="#0000C2FF" transparent="1" />
        <widget name="qr_big" position="170,88" size="420,420" pixmap="{qr}" alphatest="blend" scale="1" />
        <widget name="qr_huge" position="30,82" size="700,450" pixmap="{qr}" alphatest="blend" scale="1" />
        <widget name="txt" position="20,525" size="720,24" font="Regular;18" halign="center" valign="center" foregroundColor="#00D7DEE9" transparent="1" />
    </screen>""".format(qr=PLUGIN_QR_CODE_BIG_PATH)
    return """
    <screen position="center,center" size="900,650" title="Wsparcie / Support" backgroundColor="#000B0F14">
        <eLabel position="0,0" size="900,650" backgroundColor="#000B0F14" zPosition="-1" />
        <eLabel position="0,0" size="900,80" backgroundColor="#00121824" zPosition="-1" />
        <widget name="title" position="20,18" size="860,40" font="Regular;30" halign="center" foregroundColor="#0000C2FF" transparent="1" />
        <widget name="qr_big" position="200,100" size="500,500" pixmap="{qr}" alphatest="blend" scale="1" />
        <widget name="qr_huge" position="50,90" size="800,540" pixmap="{qr}" alphatest="blend" scale="1" />
        <widget name="txt" position="20,610" size="860,35" font="Regular;22" halign="center" valign="center" foregroundColor="#00D7DEE9" transparent="1" />
    </screen>""".format(qr=PLUGIN_QR_CODE_BIG_PATH)

def _info_screen_skin():
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
    if _is_hd_ui():
        return """
    <screen name='PanelAIO' position='center,center' size='980,620' title='AIO Panel' backgroundColor='#000B0F14'>
        <eLabel position='0,0' size='980,82' backgroundColor='#00121824' zPosition='-1' />
        <widget name='qr_code_small' position='16,20' size='40,40' pixmap="{qr}" alphatest='blend' scale='1' />
        <widget name='pp_logo' position='924,20' size='40,40' pixmap="{pp_logo}" alphatest='blend' scale='1' />
        <widget name='support_label' position='66,9' size='350,60' font='Regular;20' halign='left' valign='center' foregroundColor='#0000C2FF' transparent='1' />
        <widget name='title_label' position='420,10' size='490,30' font='Regular;28' halign='right' valign='center' foregroundColor='#0000C2FF' transparent='1' />
        <widget name='health' position='420,44' size='490,22' font='Regular;18' halign='right' valign='center' foregroundColor='#00A9B4C2' transparent='1' />
        <eLabel position='0,82' size='980,2' backgroundColor='#0000C2FF' />

        <widget name='sidebar' position='0,84' size='240,490' itemHeight='52' font='Regular;21' scrollbarMode='showOnDemand' selectionPixmap='sel_sidebar.png' foregroundColor='#0000C2FF' foregroundColorSelected='#0000C2FF' transparent='1'/>
        <eLabel position='240,84' size='2,490' backgroundColor='#00203346' />
        <widget name='menu' position='255,84' size='710,420' itemHeight='40' font='Regular;20' scrollbarMode='showOnDemand' selectionPixmap='sel_menu.png' transparent='1'/>
        <widget name='function_description' position='255,508' size='710,56' font='Regular;18' halign='left' valign='top' foregroundColor='#0000C2FF' backgroundColor='#00121824' transparent='0' />
        <widget name='tabs_display' position='0,0' size='0,0' font='Regular;1' transparent='1' />

        <eLabel position='0,574' size='980,46' backgroundColor='#00121824' zPosition='-1' />
        <widget name='legend' position='10,580'  size='960,20'  font='Regular;18' halign='center' foregroundColor='#00D7DEE9' transparent='1'/>
        <widget name='footer' position='10,600' size='960,16' font='Regular;15' halign='center' valign='center' foregroundColor='#008A94A6' transparent='1'/>
    </screen>""".format(qr=PLUGIN_QR_CODE_SMALL_PATH, pp_logo=PLUGIN_PP_LOGO_PATH)
    return """
    <screen name='PanelAIO' position='center,center' size='1100,690' title='AIO Panel' backgroundColor='#000B0F14'>
        <eLabel position='0,0' size='1100,90' backgroundColor='#00121824' zPosition='-1' />
        <widget name='qr_code_small' position='18,23' size='44,44' pixmap="{qr}" alphatest='blend' scale='1' />
        <widget name='pp_logo' position='1036,23' size='44,44' pixmap="{pp_logo}" alphatest='blend' scale='1' />
        <widget name='support_label' position='72,10' size='420,70' font='Regular;22' halign='left' valign='center' foregroundColor='#0000C2FF' transparent='1' />
        <widget name='title_label' position='470,12' size='560,36' font='Regular;32' halign='right' valign='center' foregroundColor='#0000C2FF' transparent='1' />
        <widget name='health' position='470,52' size='560,26' font='Regular;20' halign='right' valign='center' foregroundColor='#00A9B4C2' transparent='1' />
        <eLabel position='0,90' size='1100,2' backgroundColor='#0000C2FF' />

        <widget name='sidebar' position='0,92' size='270,548' itemHeight='58' font='Regular;24' scrollbarMode='showOnDemand' selectionPixmap='sel_sidebar.png' foregroundColor='#0000C2FF' foregroundColorSelected='#0000C2FF' transparent='1'/>
        <eLabel position='270,92' size='2,548' backgroundColor='#00203346' />
        <widget name='menu' position='285,92' size='800,468' itemHeight='44' font='Regular;22' scrollbarMode='showOnDemand' selectionPixmap='sel_menu.png' transparent='1'/>
        <widget name='function_description' position='285,565' size='800,70' font='Regular;20' halign='left' valign='top' foregroundColor='#0000C2FF' backgroundColor='#00121824' transparent='0' />
        <widget name='tabs_display' position='0,0' size='0,0' font='Regular;1' transparent='1' />

        <eLabel position='0,640' size='1100,50' backgroundColor='#00121824' zPosition='-1' />
        <widget name='legend' position='10,646'  size='1080,22'  font='Regular;20' halign='center' foregroundColor='#00D7DEE9' transparent='1'/>
        <widget name='footer' position='10,668' size='1080,18' font='Regular;16' halign='center' valign='center' foregroundColor='#008A94A6' transparent='1'/>
    </screen>""".format(qr=PLUGIN_QR_CODE_SMALL_PATH, pp_logo=PLUGIN_PP_LOGO_PATH)

# === TŁUMACZENIA ===
TRANSLATIONS = {
    "PL": {
        "support_text": "Wesprzyj rozwój wtyczki",
        "update_available_title": "Dostępna nowa wersja!",
        "update_available_msg": """Dostępna jest nowa wersja AIO Panel: {latest_ver}
Twoja wersja: {current_ver}

Lista zmian:
{changelog}
Czy chcesz ją teraz zainstalować?\n\nPo instalacji KONIECZNY jest restart GUI!""",
        "already_latest": "Używasz najnowszej wersji wtyczki ({ver}).",
        "update_check_error": "Nie można sprawdzić dostępności aktualizacji.\nSprawdź połączenie z internetem.",
        "update_generic_error": "Wystąpił błąd podczas sprawdzania aktualizacji.",
        "loading_text": "Ładowanie...",
        "loading_error_text": "Błąd wczytywania danych",
        "sk_wizard_title": ">>> Super Konfigurator (Pierwsza Instalacja)",
        "sk_choice_title": "Super Konfigurator - Wybierz opcję",
        "sk_option_deps": "1) [PKG] Zainstaluj only zależności (wget, tar, unzip)",
        "sk_option_basic_no_picons": "2) [START] Podstawowa Konfiguracja (bez Picon)",
        "sk_option_full_picons": "3) [FULL] Pełna Konfiguracja (z Piconami)",
        "sk_option_cancel": "[X] Anuluj",
        "sk_confirm_deps": "Czy na pewno chcesz zainstalować only podstawowe zależności systemowe?",
        "sk_confirm_basic": "Rozpocznie się podstawowa konfiguracja systemu.\n\n- Instalacja zależności\n- Instalacja listy kanałów\n- Instalacja Softcam (skrypt)\n- Instalacja Oscam z feed\n\nCzy chcesz kontynuować?",
        "sk_confirm_full": "Rozpocznie się pełna konfiguracja systemu.\n\n- Instalacja zależności\n- Instalacja listy kanałów\n- Instalacja Softcam (skrypt)\n- Instalacja Oscam z feed\n- Instalacja Piconów (duży plik)\n\nCzy chcesz kontynuować?",
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
Do you want to install it now?\n\nGUI restart is REQUIRED after installation!""",
        "already_latest": "You are using the latest version of the plugin ({ver}).",
        "update_check_error": "Could not check for updates.\nPlease check your internet connection.",
        "update_generic_error": "An error occurred while checking for updates.",
        "loading_text": "Loading...",
        "loading_error_text": "Error loading data",
        "sk_wizard_title": ">>> Super Setup Wizard (First Installation)",
        "sk_choice_title": "Super Setup Wizard - Select an option",
        "sk_option_deps": "1) [PKG] Install dependencies only (wget, tar, unzip)",
        "sk_option_basic_no_picons": "2) [START] Basic Configuration (without Picons)",
        "sk_option_full_picons": "3) [FULL] Full Configuration (with Picons)",
        "sk_option_cancel": "[X] Cancel",
        "sk_confirm_deps": "Are you sure you want to install only the basic system dependencies?",
        "sk_confirm_basic": "A basic system configuration will now begin.\n\n- Install dependencies\n- Install channel list\n- Install Softcam (script)\n- Install Oscam from feed\n\nDo you want to continue?",
        "sk_confirm_full": "A full system configuration will now begin.\n\n- Install dependencies\n- Install channel list\n- Install Softcam (script)\n- Install Oscam from feed\n- Install Picons (large file)\n\nDo you want to continue?",
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
def show_message_compat(session, message, message_type=MessageBox.TYPE_INFO, timeout=10, on_close=None):
    if on_close:
        reactor.callLater(0.2, lambda: session.openWithCallback(on_close, MessageBox, message, message_type, timeout=timeout))
    else:
        reactor.callLater(0.2, lambda: session.open(MessageBox, message, message_type, timeout=timeout))

# --- FUNKCJA URUCHAMIANIA W TLE (Dla zadań wewnętrznych) ---
def run_command_in_background(session, title, cmd_list, callback_on_finish=None):
    """
    Otwiera okno "Proszę czekać..." i uruchamia polecenia shella w osobnym wątku.
    """
    wait_message = session.open(MessageBox, "Trwa wykonywanie: {}\n\nProszę czekać...".format(title), MessageBox.TYPE_INFO, enable_input=False)
    
    def command_thread():
        try:
            for cmd in cmd_list:
                print("[AIO Panel] Uruchamianie w tle [{}]: {}".format(title, cmd))
                process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    print("[AIO Panel] Błąd w tle [{}]: {}".format(title, stderr))
                
        except Exception as e:
            print("[AIO Panel] Wyjątek w wątku [{}]: {}".format(title, e))
        finally:
            reactor.callFromThread(on_finish_thread)

    def on_finish_thread():
        wait_message.close()
        if callback_on_finish:
            try:
                callback_on_finish()
            except Exception as e:
                print("[AIO Panel] Błąd w callback po run_command_in_background:", e)

    Thread(target=command_thread).start()

# Funkcja konsoli (teraz używana do diagnostyki i instalatorów zewnętrznych)
def console_screen_open(session, title, cmds_with_args, callback=None, close_on_finish=False):
    cmds_list = cmds_with_args if isinstance(cmds_with_args, list) else [cmds_with_args]
    if reactor.running:
        if callback:
            reactor.callLater(0.1, lambda: session.open(Console, title=title, cmdlist=cmds_list, closeOnSuccess=close_on_finish).onClose.append(callback))
        else:
            reactor.callLater(0.1, lambda: session.open(Console, title=title, cmdlist=cmds_list, closeOnSuccess=close_on_finish))
    else:
        c_dialog = session.open(Console, title=title, cmdlist=cmds_list, closeOnSuccess=close_on_finish)
        if callback: c_dialog.onClose.append(callback)

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

def _command_exists(cmd):
    try:
        return shutil_which(cmd) is not None
    except Exception:
        return False

def _pick_tip_index(total):
    try:
        return datetime.date.today().toordinal() % max(total, 1)
    except Exception:
        return 0

def _get_aio_tips(lang="PL"):
    tips_pl = [
        "Użyj AIO Quick Start, gdy chcesz pokazać najciekawsze funkcje bez przekopywania całego menu.",
        "Po większej instalacji uruchom Tryb Naprawy po Instalacji – często wystarczy do przywrócenia uprawnień i usług.",
        "Gdy flash zaczyna się zapełniać, najpierw uruchom Smart Cleanup zamiast ręcznie kasować pliki systemowe.",
        "Auto RAM Cleaner ustaw tylko na boxach z małą ilością RAM – na mocniejszych tunerach zwykle wystarcza tryb ręczny.",
        "Jeżeli feedy przestaną działać, sprawdź najpierw Menedżer Feedów / Repozytoriów i test połączenia, zanim zrobisz reinstall obrazu.",
        "Przed podmianą list kanałów zrób szybki backup – przywrócenie trwa chwilę i oszczędza nerwów.",
        "Zakładka Informacje o Systemie to dobry pierwszy krok przy diagnozie: od razu widać uptime, RAM i aktywne IP.",
        "Lokalny changelog działa także bez internetu – przydatne, gdy GitHub chwilowo nie odpowiada na starszych obrazach."
    ]
    tips_en = [
        "Use AIO Quick Start when you want to showcase the most useful features without browsing the full menu.",
        "After a bigger install, run Post-Install Repair first – permissions and service fixes often solve the issue immediately.",
        "When flash space gets tight, start with Smart Cleanup before deleting system files manually.",
        "Use Auto RAM Cleaner mainly on low-memory boxes – manual mode is often enough on stronger receivers.",
        "If feeds stop working, check Feed / Repository Manager and connectivity first before reinstalling the image.",
        "Create a quick backup before replacing channel lists – restore takes only a moment and avoids frustration.",
        "System Information is a good first stop for troubleshooting: uptime, RAM and active IPs are visible immediately.",
        "The local changelog works even without internet access, which helps on older images when GitHub is unreachable."
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

# === FUNKCJA install_archive (GLOBALNA) ===
def install_archive(session, title, url, callback_on_finish=None, picon_path=None):
    if not url.endswith((".zip", ".tar.gz", ".tgz", ".ipk")):
        show_message_compat(session, "Nieobsługiwany format archiwum!", message_type=MessageBox.TYPE_ERROR)
        if callback_on_finish: callback_on_finish()
        return
    archive_type = "zip" if url.endswith(".zip") else ("tar.gz" if url.endswith((".tar.gz", ".tgz")) else "ipk")
    prepare_tmp_dir()
    tmp_archive_path = os.path.join(PLUGIN_TMP_PATH, os.path.basename(url))
    
    download_cmd = "wget -T 30 --no-check-certificate -O \"{}\" \"{}\"".format(tmp_archive_path, url)
    
    if "picon" in title.lower():
        picon_path = (picon_path or "/usr/share/enigma2/picon").strip()
        if not picon_path:
            picon_path = "/usr/share/enigma2/picon"
        nested_picon_path = os.path.join(picon_path, "picon")
        full_command = (
            "{download_cmd} && "
            "mkdir -p {picon_path} && "
            "unzip -o -q \"{archive_path}\" -d \"{picon_path}\" && "
            "if [ -d \"{nested_path}\" ]; then mv -f \"{nested_path}\"/* \"{picon_path}/\"; rmdir \"{nested_path}\"; fi && "
            "rm -f \"{archive_path}\" && "
            "echo 'Picony zostały pomyślnie zainstalowane do: {picon_path}' && sleep 1"
        ).format(
            download_cmd=download_cmd,
            archive_path=tmp_archive_path,
            picon_path=picon_path,
            nested_path=nested_picon_path
        )
    elif archive_type == "ipk":
        full_command = "{} && opkg install --force-reinstall \"{}\" && rm -f \"{}\"".format(download_cmd, tmp_archive_path, tmp_archive_path)
    else:
        # Ten blok dotyczy list kanałów (TYPU "LIST")
        install_script_path = os.path.join(PLUGIN_PATH, "install_archive_script.sh")
        if not os.path.exists(install_script_path):
             show_message_compat(session, "BŁĄD: Brak pliku install_archive_script.sh!", message_type=MessageBox.TYPE_ERROR)
             if callback_on_finish: callback_on_finish()
             return
        
        clear_bouquets_cmd = "rm -f /etc/enigma2/bouquets.tv /etc/enigma2/bouquets.radio /etc/enigma2/userbouquet.*.tv /etc/enigma2/userbouquet.*.radio"
        chmod_cmd = "chmod +x \"{}\"".format(install_script_path)
        full_command = "{download_cmd} && {clear_cmd} && {chmod_cmd} && bash {script_path} \"{tmp_archive}\" \"{archive_type}\"".format(
            download_cmd=download_cmd,
            clear_cmd=clear_bouquets_cmd,
            chmod_cmd=chmod_cmd,
            script_path=install_script_path,
            tmp_archive=tmp_archive_path,
            archive_type=archive_type
        )
    
    run_command_in_background(session, title, [full_command], callback_on_finish=callback_on_finish)

def get_python_version():
    try:
        ver = sys.version_info
        return "{}.{}".format(ver[0], ver[1])
    except:
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
    ("🔄 Aktualizuj oscam.srvid/srvid2", "CMD:UPDATE_SRVID"),
    ("🔑 Aktualizuj SoftCam.Key (Online)", "CMD:INSTALL_SOFTCAMKEY_ONLINE"),
    ("📥 Softcam - Instalator", "CMD:INSTALL_SOFTCAM_SCRIPT"),
    ("📥 Oscam Feed - Instalator (Auto)", "CMD:INSTALL_BEST_OSCAM"),
    ("📥 NCam (Feed - najnowszy)", "CMD:INSTALL_NCAM_FEED"),
    (r"\c00FFD200--- Wtyczki Online ---\c00ffffff", "SEPARATOR"),
    ("📺 XStreamity - Instalator", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-xstreamity"),
    ("📺 IPTV Dream - Instalator", "CMD:INSTALL_IPTV_DREAM"),
    ("⚙️ ServiceApp - Instalator", "CMD:INSTALL_SERVICEAPP"),
    ("📦 Konfiguracja IPTV - zależności", "CMD:IPTV_DEPS"),
    ("⚙️ StreamlinkProxy - Instalator", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-streamlinkproxy"),
    ("🛠 AJPanel - Instalator", "bash_raw:wget https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh -O - | /bin/sh"),
    ("▶️ E2iPlayer Master - Instalacja/Aktualizacja", "bash_raw:wget -q 'https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh' -O - | /bin/sh"),
    ("📅 EPG Import - Instalator", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh -O - | /bin/bash"),
    ("📺 Simple IPTV EPG - Instalator", "bash_raw:wget -qO - https://raw.githubusercontent.com/OliOli2013/SimpleIPTV_EPG/main/installer.sh | /bin/sh"),
    ("🔄 S4aUpdater - Instalator", "bash_raw:wget http://s4aupdater.one.pl/instalujs4aupdater.sh -O - | /bin/sh"),
    ("🔄 MyUpdater v5.1 - Instalator", "bash_raw:wget -q -O - https://raw.githubusercontent.com/OliOli2013/MyUpdater-Plugin/main/installer.sh | sh"),
    ("📺 JediMakerXtream - Instalator", "bash_raw:wget https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh -O - | /bin/sh"),
    ("▶️ YouTube - Instalator", "bash_raw:opkg install https://github.com/Taapat/enigma2-plugin-youtube/releases/download/git1294/enigma2-plugin-extensions-youtube_py3-git1294-cbcf8b0-r0.0.ipk"),
    ("📦 J00zeks Feed (Repo Installer)", "CMD:INSTALL_J00ZEK_REPO"),
    ("📺 E2Kodi v2 - Instalator (j00zek)", "CMD:INSTALL_E2KODI"),
    ("🖼️ Picon Updater - Instalator (Picony)", "bash_raw:wget -qO - https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh | /bin/sh"),
    ("🖼️ ChocholousekPicons - Instalator", "bash_raw:wget -qO- --no-check-certificate 'https://github.com/s3n0/e2plugins/raw/master/ChocholousekPicons/online-setup' | bash -s install"),
    ("🔑 CIEFP Oscam Editor - Instalator", "bash_raw:wget -q --no-check-certificate 'https://raw.githubusercontent.com/ciefp/CiefpOscamEditor/main/installer.sh' -O - | /bin/sh"),
    ("📺 e-stralker - Instalator (feed)", "bash_raw:opkg update && (opkg install enigma2-plugin-extensions-estalker || opkg install enigma2-plugin-extensions-e-stralker || opkg install enigma2-plugin-extensions-e-stalker || (PKG=$(opkg list | awk 'BEGIN{IGNORECASE=1} $1 ~ /^enigma2-plugin-extensions-estalker$/ {print $1; exit}'); [ -z \\\"$PKG\\\" ] && PKG=$(opkg list | awk 'BEGIN{IGNORECASE=1} $1 ~ /estalker/ {print $1; exit}'); [ -z \\\"$PKG\\\" ] && PKG=$(opkg list | awk 'BEGIN{IGNORECASE=1} $1 ~ /stalker/ {print $1; exit}'); [ -n \\\"$PKG\\\" ] && opkg install $PKG || (echo 'Nie znaleziono EStalker w feedach (opkg).'; exit 1)))"),
        ("▶️ VAVOO - Instalator", "bash_raw:wget -q \"--no-check-certificate\" https://raw.githubusercontent.com/Belfagor2005/vavoo/main/installer.sh -O - | /bin/sh"),
    ("▶️ FilmXY - Instalator", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/filmxy/main/installer.sh -O - | /bin/sh"),
    ("⚽ FootOnsat - Instalator", "bash_raw:wget https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh -O - | /bin/sh"),
]


SOFTCAM_AND_PLUGINS_EN = [
    (r"\c00FFD200--- Softcams ---\c00ffffff", "SEPARATOR"),
    ("🔄 Restart Oscam", "CMD:RESTART_OSCAM"),
    ("🧹 Clear Oscam Password", "CMD:CLEAR_OSCAM_PASS"),
    ("⚙️ oscam.dvbapi - clear file", "CMD:MANAGE_DVBAPI"),
    ("🔄 Update oscam.srvid/srvid2", "CMD:UPDATE_SRVID"),
    ("🔑 Update SoftCam.Key (Online)", "CMD:INSTALL_SOFTCAMKEY_ONLINE"),
    ("📥 Softcam - Installer", "CMD:INSTALL_SOFTCAM_SCRIPT"),
    ("📥 Oscam Feed - Installer (Auto)", "CMD:INSTALL_BEST_OSCAM"),
    ("📥 NCam (Feed - latest)", "CMD:INSTALL_NCAM_FEED"),
    (r"\c00FFD200--- Online Plugins ---\c00ffffff", "SEPARATOR"),
    ("📺 XStreamity - Installer", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-xstreamity"),
    ("📺 IPTV Dream - Installer", "CMD:INSTALL_IPTV_DREAM"),
    ("⚙️ ServiceApp - Installer", "CMD:INSTALL_SERVICEAPP"),
    ("📦 IPTV Configuration - dependencies", "CMD:IPTV_DEPS"),
    ("⚙️ StreamlinkProxy - Installer", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-streamlinkproxy"),
    ("🛠 AJPanel - Installer", "bash_raw:wget https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh -O - | /bin/sh"),
    ("▶️ E2iPlayer Master - Install/Update", "bash_raw:wget -q 'https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh' -O - | /bin/sh"),
    ("📅 EPG Import - Installer", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh -O - | /bin/bash"),
    ("📺 Simple IPTV EPG - Installer", "bash_raw:wget -qO - https://raw.githubusercontent.com/OliOli2013/SimpleIPTV_EPG/main/installer.sh | /bin/sh"),
    ("🔄 S4aUpdater - Installer", "bash_raw:wget http://s4aupdater.one.pl/instalujs4aupdater.sh -O - | /bin/sh"),
    ("🔄 MyUpdater v5.1 - Installer", "bash_raw:wget -q -O - https://raw.githubusercontent.com/OliOli2013/MyUpdater-Plugin/main/installer.sh | sh"),
    ("📺 JediMakerXtream - Installer", "bash_raw:wget https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh -O - | /bin/sh"),
    ("▶️ YouTube - Installer", "bash_raw:opkg install https://github.com/Taapat/enigma2-plugin-youtube/releases/download/git1294/enigma2-plugin-extensions-youtube_py3-git1294-cbcf8b0-r0.0.ipk"),
    ("📦 J00zeks Feed (Repo Installer)", "CMD:INSTALL_J00ZEK_REPO"),
    ("📺 E2Kodi v2 - Installer (j00zek)", "CMD:INSTALL_E2KODI"),
    ("🖼️ Picon Updater - Installer (Picons)", "bash_raw:wget -qO - https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh | /bin/sh"),
    ("🖼️ ChocholousekPicons - Installer", "bash_raw:wget -qO- --no-check-certificate 'https://github.com/s3n0/e2plugins/raw/master/ChocholousekPicons/online-setup' | bash -s install"),
    ("🔑 CIEFP Oscam Editor - Installer", "bash_raw:wget -q --no-check-certificate 'https://raw.githubusercontent.com/ciefp/CiefpOscamEditor/main/installer.sh' -O - | /bin/sh"),
    ("📺 e-stralker - Installer (feed)", "bash_raw:opkg update && (opkg install enigma2-plugin-extensions-estalker || opkg install enigma2-plugin-extensions-e-stralker || opkg install enigma2-plugin-extensions-e-stalker || (PKG=$(opkg list | awk 'BEGIN{IGNORECASE=1} $1 ~ /^enigma2-plugin-extensions-estalker$/ {print $1; exit}'); [ -z \\\"$PKG\\\" ] && PKG=$(opkg list | awk 'BEGIN{IGNORECASE=1} $1 ~ /estalker/ {print $1; exit}'); [ -z \\\"$PKG\\\" ] && PKG=$(opkg list | awk 'BEGIN{IGNORECASE=1} $1 ~ /stalker/ {print $1; exit}'); [ -n \\\"$PKG\\\" ] && opkg install $PKG || (echo 'EStalker not found in feeds (opkg).'; exit 1)))"),
        ("▶️ VAVOO - Installer", "bash_raw:wget -q \"--no-check-certificate\" https://raw.githubusercontent.com/Belfagor2005/vavoo/main/installer.sh -O - | /bin/sh"),
    ("▶️ FilmXY - Installer", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/filmxy/main/installer.sh -O - | /bin/sh"),
    ("⚽ FootOnsat - Installer", "bash_raw:wget https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh -O - | /bin/sh"),
]


# === NOWE PODZIELONE LISTY MENU (PL) ===
SYSTEM_TOOLS_PL = [
    (r"\c00FFD200--- Konfigurator ---\c00ffffff", "SEPARATOR"),
    ("✨ Super Konfigurator (Pierwsza Instalacja)", "CMD:SUPER_SETUP_WIZARD"),
    ("👁️ Widoczność w menu tunera (ON/OFF)", "CMD:TOGGLE_MENU_VISIBILITY"),
    (r"\c00FFD200--- Narzędzia Systemowe ---\c00ffffff", "SEPARATOR"),
    ("🗑️ Menadżer Deinstalacji", "CMD:UNINSTALL_MANAGER"),
    ("📡 Aktualizuj satellites.xml", "CMD:UPDATE_SATELLITES_XML"),
    ("🖼️ Pobierz Picony (Transparent)", "archive:https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip"),
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
    ("📡 Update satellites.xml", "CMD:UPDATE_SATELLITES_XML"),
    ("🖼️ Download Picons (Transparent)", "archive:https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip"),
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
    ("🎨 Algare FHD - Instalator", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/popking159/skins/refs/heads/main/aglarepli/installer.sh -O - | /bin/sh"),
    ("🎨 Fury FHD - Instalator", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh -O - | /bin/sh"),
    ("🎨 Luka FHD - Instalator", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/popking159/skins/refs/heads/main/lukapli/installer.sh -O - | /bin/sh"),
    ("🎨 Maxy FHD - Instalator", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/popking159/skins/refs/heads/main/maxyatv/installer.sh -O - | /bin/sh"),
    ("🎨 XDreamy - Instalator", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Insprion80/Skins/main/xDreamy/installer.sh -O - | /bin/sh"),
]

SKINS_EN = [
    ("🎨 Algare FHD - Installer", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/popking159/skins/refs/heads/main/aglarepli/installer.sh -O - | /bin/sh"),
    ("🎨 Fury FHD - Installer", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh -O - | /bin/sh"),
    ("🎨 Luka FHD - Installer", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/popking159/skins/refs/heads/main/lukapli/installer.sh -O - | /bin/sh"),
    ("🎨 Maxy FHD - Installer", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/popking159/skins/refs/heads/main/maxyatv/installer.sh -O - | /bin/sh"),
    ("🎨 XDreamy - Installer", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Insprion80/Skins/main/xDreamy/installer.sh -O - | /bin/sh"),
]


# === NOWE 4 KATEGORIE ===
COL_TITLES = {
    "PL": ("📺 Listy Kanałów", "🔑 Softcam i Wtyczki", "⚙️ Narzędzia Systemowe", "ℹ️ Info i Diagnostyka"),
    "EN": ("📺 Channel Lists", "🔑 Softcam & Plugins", "⚙️ System Tools", "ℹ️ Info & Diagnostics")
}


# === FUNKCJE ŁADOWANIA DANYCH (GLOBALNE) ===
def _get_lists_from_repo_sync():
    manifest_url = "https://raw.githubusercontent.com/OliOli2013/PanelAIO-Lists/main/manifest.json"
    tmp_json_path = os.path.join(PLUGIN_TMP_PATH, 'manifest.json')
    prepare_tmp_dir()
    try:
        # [FIX] OpenPLi 9.2: Wymuszenie User-Agent oraz IPv4, aby uniknąć problemów z GitHub/SSL
        cmd = "wget --prefer-family=IPv4 --no-check-certificate -U \"Enigma2\" -q -T 20 -O {} {}".format(tmp_json_path, manifest_url)
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr = process.communicate()
        ret_code = process.returncode
        if ret_code != 0:
             print("[AIO Panel] Wget error downloading manifest (code {}): {}".format(ret_code, stderr))
             return []
        if not (os.path.exists(tmp_json_path) and os.path.getsize(tmp_json_path) > 0):
            print("[AIO Panel] Błąd pobierania manifest.json: plik pusty lub nie istnieje")
            return []
    except Exception as e:
        print("[AIO Panel] Błąd pobierania manifest.json (wyjątek):", e)
        return []
        
    lists_menu = []
    try:
        # UNIVERSAL FIX: Use io.open with utf-8 where supported, or manual decode
        with io.open(tmp_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data:
            item_type = item.get("type", "LIST").upper() 
            name = item.get('name', 'Brak nazwy')
            author = item.get('author', '')
            url = item.get('url', '')
            
            if not url: 
                continue

            if item_type == "M3U":
                bouquet_id = item.get('bouquet_id', 'userbouquet.imported_m3u.tv')
                menu_title = "📺 {} - {} (Dodaj Bukiet M3U)".format(name, author)
                action = "m3u:{}:{}:{}".format(url, bouquet_id, name)
                lists_menu.append((menu_title, action))
            
            elif item_type == "BOUQUET":
                bouquet_id = item.get('bouquet_id', 'userbouquet.imported_ref.tv')
                menu_title = "📺 {} - {} (Dodaj Bukiet REF)".format(name, author)
                action = "bouquet:{}:{}:{}".format(url, bouquet_id, name)
                lists_menu.append((menu_title, action))

            else: 
                version = item.get('version', '')
                menu_title = "📡 {} - {} ({})".format(name, author, version)
                action = "archive:{}".format(url)
                lists_menu.append((menu_title, action))

    except Exception as e:
        print("[AIO Panel] Błąd przetwarzania pliku manifest.json:", e)
        return []
    
    if not lists_menu:
         print("[AIO Panel] Brak list w repozytorium (manifest pusty?)")
         return []
    return lists_menu

def _get_s4aupdater_lists_dynamic_sync():
    s4aupdater_list_txt_url = 'http://s4aupdater.one.pl/s4aupdater_list.txt'
    prepare_tmp_dir()
    tmp_list_file = os.path.join(PLUGIN_TMP_PATH, 's4aupdater_list.txt')
    lists = []
    try:
        cmd = "wget --no-check-certificate -q -T 20 -O {} {}".format(tmp_list_file, s4aupdater_list_txt_url)
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.communicate()
        if not (process.returncode == 0 and os.path.exists(tmp_list_file) and os.path.getsize(tmp_list_file) > 0):
             return []
    except Exception:
        return []
    
    try:
        urls_dict, versions_dict = {}, {}
        # UNIVERSAL FIX: Use io.open
        with io.open(tmp_list_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                clean_line = line.strip()
                if "_url:" in clean_line: parts = clean_line.split(':', 1); urls_dict[parts[0].strip()] = parts[1].strip()
                elif "_version:" in clean_line: parts = clean_line.split(':', 1); versions_dict[parts[0].strip()] = parts[1].strip()
        for var_name, url_value in urls_dict.items():
            display_name_base = var_name.replace('_url', '').replace('_', ' ').title()
            version_key = var_name.replace('_url', '_version')
            date_info = versions_dict.get(version_key, "brak daty")
            lists.append(("📡 {} - {}".format(display_name_base, date_info), "archive:{}".format(url_value)))
    except Exception as e: 
        print("[AIO Panel] Błąd parsowania listy S4aUpdater:", e)
        return []
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

# === KLASA WizardProgressScreen (GLOBALNA) ===
class WizardProgressScreen(Screen):
    skin = _wizard_progress_skin()

    def __init__(self, session, steps, **kwargs):
        Screen.__init__(self, session)
        self.session = session
        self.reboot_mode = kwargs.get("reboot_mode", "full")  # "full" or "gui"
        self.wizard_queue = list(steps)
        self.wizard_total_steps = len(steps)
        self.wizard_current_step = 0
        self.wizard_channel_list_url = kwargs.get("channel_list_url", "")
        self.wizard_channel_list_name = kwargs.get("channel_list_name", "")
        self.wizard_picon_url = kwargs.get("picon_url", "")
        self["message"] = Label("Trwa automatyczna instalacja...\nProszę czekać.\n\nNie wyłączaj tunera.\nPo zakończeniu nastąpi automatyczny restart.")
        self.onShown.append(self.start_wizard)

    def start_wizard(self):
        self._wizard_run_next_step()

    def _wizard_run_next_step(self, *args, **kwargs):
        if not self.wizard_queue:
            self._on_wizard_finish()
            return

        next_step = self.wizard_queue.pop(0)
        self.wizard_current_step += 1
        
        step_functions = {
            "deps": self._wizard_step_deps, 
            "channel_list": self._wizard_step_channel_list,
                "install_softcam": self._wizard_step_install_softcam,
                "install_oscam": self._wizard_step_install_oscam, 
            "picons": self._wizard_step_picons,
            "reload_settings": self._wizard_step_reload_settings
        }
        
        func_to_run = step_functions.get(next_step)
        if func_to_run:
            reactor.callLater(0.5, func_to_run)
        else:
            print("[AIO Panel] Nieznany krok w Super Konfiguratorze:", next_step)
            self._wizard_run_next_step()

    def _get_wizard_title(self, task_name):
        return "Super Konfigurator [{}/{}]: {}".format(self.wizard_current_step, self.wizard_total_steps, task_name)

    def _wizard_step_deps(self):
        title = self._get_wizard_title("Instalacja zależności")
        self["message"].setText("Krok [{}/{}]:\nInstalacja zależności systemowych...\nProszę czekać.".format(self.wizard_current_step, self.wizard_total_steps))
        cmd = """
        echo 'Krok 1/3: Aktualizacja listy pakietów...'
        opkg update
        echo 'Krok 2/3: Instalacja/Aktualizacja wget i certyfikatów SSL...'
        opkg install wget ca-certificates
        echo 'Krok 3/3: Sprawdzanie tar i unzip...'
        opkg install tar || echo 'Info: Pakiet tar nie znaleziony (lub już jest), pomijam błąd.'
        opkg install unzip || echo 'Info: Pakiet unzip nie znaleziony (lub już jest), pomijam błąd.'
        echo 'Zakończono sprawdzanie zależności.'
        sleep 1
        """
        run_command_in_background(self.session, title, [cmd], callback_on_finish=self._wizard_run_next_step)

    def _wizard_step_channel_list(self):
        title = self._get_wizard_title("Instalacja listy '{}'".format(self.wizard_channel_list_name))
        url = self.wizard_channel_list_url
        
        start_msg_pl = "Krok [{}/{}]:\nInstalacja listy kanałów '{}'...\nProszę czekać.".format(self.wizard_current_step, self.wizard_total_steps, self.wizard_channel_list_name)
        start_msg_en = "Step [{}/{}]:\nInstalling channel list '{}'...\nPlease wait.".format(self.wizard_current_step, self.wizard_total_steps, self.wizard_channel_list_name)
        parent_lang = 'PL'
        if hasattr(self.session, 'current_dialog') and hasattr(self.session.current_dialog, 'lang'):
            parent_lang = self.session.current_dialog.lang
        start_msg = start_msg_pl if parent_lang == 'PL' else start_msg_en
        self["message"].setText(start_msg)
        
        install_archive(self.session, title, url, callback_on_finish=self._wizard_run_next_step)

    def _wizard_step_install_softcam(self):
        title = self._get_wizard_title("Instalacja Softcam")
        self["message"].setText(
            "Krok [{}/{}]:\nInstalacja Softcam...\nProszę czekać.".format(self.wizard_current_step, self.wizard_total_steps)
        )

        # IMPORTANT:
        # Softcam is NOT available on many public feeds. We use the known installer script.
        cmd = r"""
            echo "=== Softcam installation (AIO Wizard) ==="
            opkg update || true
            opkg install wget ca-certificates || true
            wget -O - -q http://updates.mynonpublic.com/oea/feed | bash || true
            sync
            sleep 1
        """
        run_command_in_background(self.session, title, [cmd], callback_on_finish=self._wizard_run_next_step)

    def _wizard_step_install_oscam(self):
        title = self._get_wizard_title("Instalacja Oscam")
        self["message"].setText(
            "Krok [{}/{}]:\nInstalacja Oscam z feed...\nProszę czekać.".format(self.wizard_current_step, self.wizard_total_steps)
        )

        cmd = r"""
            echo "=== Oscam installation (AIO Wizard) ==="
            opkg update || true
            echo "Find newest available Oscam package from feed..."
            CAND=""
            for p in enigma2-plugin-softcams-oscam oscam oscam-emu oscam-smod; do
                if opkg list | awk '{print \$1}' | grep -qx "\$p"; then CAND="\$p"; break; fi
            done
            if [ -z "\$CAND" ]; then
                CAND=\$(opkg list | awk "BEGIN{IGNORECASE=1} \$1 ~ /oscam/ {print \$0}" | grep -E "master|emu|stable" | head -n 1 | awk '{print \$1}')
            fi
            if [ -z "\$CAND" ]; then
                CAND=\$(opkg list | awk "BEGIN{IGNORECASE=1} \$1 ~ /oscam/ {print \$1; exit}")
            fi

            if [ -n "\$CAND" ]; then
                echo "Installing: \$CAND"
                opkg install "\$CAND" || opkg install "\$CAND" --force-reinstall || true
            else
                echo "!!! Oscam package not found in feeds. Skipping."
            fi
            sync
            sleep 1
        """
        run_command_in_background(self.session, title, [cmd], callback_on_finish=self._wizard_run_next_step)

    def _wizard_step_picons(self):
        title = self._get_wizard_title("Instalacja Picon (Transparent)")
        url = self.wizard_picon_url

        start_msg_pl = "Krok [{}/{}]:\nInstalacja Picon (Transparent)...\n(To może potrwać kilka minut)\nProszę czekać.".format(self.wizard_current_step, self.wizard_total_steps)
        start_msg_en = "Step [{}/{}]:\nInstalling Picons (Transparent)...\n(This may take a few minutes)\nPlease wait.".format(self.wizard_current_step, self.wizard_total_steps)
        parent_lang = 'PL'
        if hasattr(self.session, 'current_dialog') and hasattr(self.session.current_dialog, 'lang'):
             parent_lang = self.session.current_dialog.lang
        start_msg = start_msg_pl if parent_lang == 'PL' else start_msg_en
        self["message"].setText(start_msg)

        install_archive(self.session, title, url, callback_on_finish=self._wizard_run_next_step)
        
    def _wizard_step_reload_settings(self):
        try:
            eDVBDB.getInstance().reloadServicelist()
            eDVBDB.getInstance().reloadBouquets()
        except Exception as e:
            print("[AIO Panel] Błąd podczas przeładowywania list w wizardzie:", e)
        self._wizard_run_next_step()


    def _on_wizard_finish(self, *args, **kwargs):
        self["message"].setText(
            "Instalacja zakończona!\n\nZa chwilę nastąpi restart całego systemu tunera...\n\n"
            "Installation completed!\n\nThe receiver will reboot now..."
        )
        # [FIX] Czasami GUI nie zamyka się poprawnie przy dużym obciążeniu po instalacji.
        # Wydłużamy czas do 4s i dodajemy bezpiecznik w do_restart_and_close
        reactor.callLater(4, self.do_restart_and_close)

    def do_restart_and_close(self):
        try:
            # Próba "ładnego" restartu
            self.session.open(TryQuitMainloop, 2 if self.reboot_mode == "full" else 3)
            
            # [FIX] Zabezpieczenie na wypadek zawieszenia się GUI po instalacji FULL (np. picony)
            # Jeśli TryQuitMainloop nie zadziała w ciągu 3 sekund, wymuś reboot z poziomu systemu.
            def force_reboot_if_hung():
                print("[AIO Panel] Wymuszanie restartu (fallback)...")
                os.system("reboot || killall -9 enigma2") if self.reboot_mode == "full" else os.system("killall -9 enigma2")
            
            reactor.callLater(3, force_reboot_if_hung)
            
        finally:
            self.close()

# === NOWA KLASA EKRANU ŁADOWANIA ===
class AIOLoadingScreen(Screen):
    skin = """
    <screen position="center,center" size="700,200" title="Panel AIO">
        <widget name="message" position="20,20" size="660,160" font="Regular;26" halign="center" valign="center" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self["message"] = Label("Ładowanie...\nCzekaj, trwa ładowanie danych Panel AIO...\n\nLoading...\nPlease wait, loading AIO Panel data...")
        self.fetched_data_cache = None
        
        self.flag_file = os.path.join(PLUGIN_PATH, ".deps_ok")
        
        self.onShown.append(self.start_loading_process)

    def start_loading_process(self):
        self.check_dependencies()

    def _deps_present(self):
        """Verify runtime prerequisites on the current image."""
        # Używamy polyfill shutil_which jeśli shutil.which nie istnieje (Py2)
        which_func = shutil_which 

        def _has_cmd(cmd):
            try:
                if which_func is not None:
                    return which_func(cmd) is not None
            except Exception:
                pass
            # Fallback
            try:
                return os.system("which %s >/dev/null 2>&1" % cmd) == 0
            except Exception:
                return False

        has_wget = _has_cmd("wget")
        has_tar = _has_cmd("tar")
        has_unzip = _has_cmd("unzip")

        ca_paths = [
            "/etc/ssl/certs/ca-certificates.crt",
            "/etc/ssl/certs/ca-bundle.crt",
            "/etc/ssl/cert.pem",
            "/etc/ssl/certs/ca-certificates.pem",
        ]
        has_ca = any(os.path.exists(p) for p in ca_paths)

        return has_wget and has_tar and has_unzip and has_ca

    def check_dependencies(self):
        if os.path.exists(self.flag_file) and self._deps_present():
            self.start_async_data_load()
            return

        if os.path.exists(self.flag_file):
            try:
                os.remove(self.flag_file)
            except Exception:
                pass

        self["message"].setText("Pierwsze uruchomienie:\nInstalacja/Aktualizacja kluczowych zależności (SSL)...\nProszę czekać, to może potrwać minutę...\n\n(Instalacja odbywa się w tle)")
        
        cmd = """
        echo "AIO Panel: Cicha instalacja zależności (bez opkg update)..."
        opkg install wget ca-certificates ca-bundle > /dev/null 2>&1
        opkg install tar > /dev/null 2>&1 || echo 'Info: Pakiet tar pominięty.'
        opkg install unzip > /dev/null 2>&1 || echo 'Info: Pakiet unzip pominięty.'
        echo "AIO Panel: Zakończono."
        """
        
        Thread(target=self._run_deps_in_background, args=(cmd,)).start()

    def _run_deps_in_background(self, cmd):
        try:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.communicate()
        except Exception as e:
            print("[AIO Panel] Błąd podczas cichej instalacji zależności:", e)
        
        reactor.callFromThread(self.on_dependencies_installed_safe)

    def on_dependencies_installed_safe(self, *args):
        try:
            with open(self.flag_file, 'w') as f:
                f.write('ok')
        except Exception as e:
            print("[AIO Panel] Nie można utworzyć pliku flagi .deps_ok:", e)
            
        self.start_async_data_load()

    def start_async_data_load(self):
        thread = Thread(target=self._background_data_loader)
        thread.start()

    def _background_data_loader(self):
        repo_lists, s4a_lists_full, best_oscam_version = [], [], "N/A"
        try:
            repo_lists = _get_lists_from_repo_sync()
        except Exception as e:
            print("[AIO Panel] Błąd pobierania list repo:", e)
            repo_lists = [(TRANSLATIONS["PL"]["loading_error_text"] + " (REPO)", "SEPARATOR")] 
        try:
            s4a_lists_full = _get_s4aupdater_lists_dynamic_sync()
        except Exception as e:
            print("[AIO Panel] Błąd pobierania list S4a:", e)
        try:
            best_oscam_version = _get_best_oscam_version_info_sync()
        except Exception as e:
            print("[AIO Panel] Błąd pobierania wersji Oscam:", e)
            best_oscam_version = "Error"
        
        self.fetched_data_cache = {
            "repo_lists": repo_lists,
            "s4a_lists_full": s4a_lists_full,
            "best_oscam_version": best_oscam_version
        }
        reactor.callFromThread(self._on_data_loaded)

    def _on_data_loaded(self):
        self.session.open(Panel, self.fetched_data_cache)
        self.close()



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
            cmd_log = "wget --no-check-certificate -O {} {}".format(tmp_changelog_path, changelog_url)
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
    skin = """
    <screen position="center,center" size="900,560" title="AIO Viewer">
        <widget name="title" position="20,10" size="860,36" font="Regular;28" />
        <widget name="text" position="20,55" size="860,455" font="Regular;24" />
        <widget name="help" position="20,520" size="860,28" font="Regular;22" />
    </screen>
    """

    def __init__(self, session, title, content, help_text=None):
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


# === KLASA Panel (GŁÓWNE OKNO) - WERSJA Z ZAKŁADKAMI v2 (Sterowanie L/R) ===

# === NOWE EKRANY v5.0 ===

class SystemMonitorScreen(Screen):
    skin = """
    <screen position="center,center" size="900,520" title="System Monitor">
        <widget name="title" position="20,10" size="860,40" font="Regular;32" halign="left" />
        <widget name="info" position="20,60" size="860,420" font="Regular;26" halign="left" valign="top" />
        <widget name="help" position="20,485" size="860,30" font="Regular;22" halign="left" />
    </screen>"""

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
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "InfoActions"], {
            "ok": self._update,
            "cancel": self.close,
            "red": lambda: self._set_interval(5),
            "green": lambda: self._set_interval(10),
            "yellow": lambda: self._set_interval(30),
        }, -1)
        self.onShown.append(self._start)

    def _start(self):
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
    skin = """
    <screen position="center,center" size="1050,650" title="Log Viewer">
        <widget name="title" position="20,10" size="1010,40" font="Regular;30" halign="left" />
        <widget name="log" position="20,60" size="1010,540" font="Regular;22" halign="left" valign="top" />
        <widget name="help" position="20,610" size="1010,30" font="Regular;22" halign="left" />
    </screen>"""

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
        if self._auto:
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
    skin = """
    <screen position="center,center" size="950,620" title="Cron Manager">
        <widget name="title" position="20,10" size="910,40" font="Regular;30" />
        <widget name="list" position="20,60" size="910,500" scrollbarMode="showOnDemand" />
        <widget name="help" position="20,570" size="910,40" font="Regular;22" />
    </screen>"""

    DISABLED_PREFIX = "#AIO_DISABLED# "

    def __init__(self, session, lang="PL"):
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
            with open(self.cron_path, "w") as f:
                f.write("\n".join(lines).rstrip("\n") + "\n")
            self._reload_daemon()
            return True
        except Exception as e:
            show_message_compat(self.session, "Błąd zapisu cron: %s" % e, MessageBox.TYPE_ERROR, timeout=6)
            return False

    def _reload_daemon(self):
        os.system("killall -HUP crond 2>/dev/null || true")
        os.system("/etc/init.d/cron restart 2>/dev/null || true")
        os.system("/etc/init.d/crond restart 2>/dev/null || true")
        os.system("systemctl restart cron 2>/dev/null || true")
        os.system("systemctl restart crond 2>/dev/null || true")

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
    skin = """
    <screen position="center,center" size="950,620" title="Service Manager">
        <widget name="title" position="20,10" size="910,40" font="Regular;30" />
        <widget name="list" position="20,60" size="910,500" scrollbarMode="showOnDemand" />
        <widget name="help" position="20,570" size="910,40" font="Regular;22" />
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

    def _action(self, act):
        names = self._get_selected_service_names()
        if not names:
            return
        # choose first existing service unit/script
        svc = names[0]
        cmd_parts = []
        if self._is_systemd():
            cmd_parts.append("systemctl %s %s 2>/dev/null" % (act, svc))
            # also try alternates
            for alt in names[1:]:
                cmd_parts.append("systemctl %s %s 2>/dev/null" % (act, alt))
        # init.d fallbacks
        for n in names:
            cmd_parts.append("/etc/init.d/%s %s 2>/dev/null" % (n, act))
        cmd = " || ".join(cmd_parts) + " || true; sleep 1"
        self.session.openWithCallback(lambda *a: self.refresh(), Console, title="Service: %s (%s)" % (svc, act), cmdlist=[cmd], closeOnSuccess=False)

    def show_status(self):
        names = self._get_selected_service_names()
        if not names:
            return
        svc = names[0]
        if self._is_systemd():
            cmd = "systemctl status %s --no-pager | tail -n 60" % svc
        else:
            cmd = "ps | grep -E '%s' | grep -v grep" % "|".join(names)
        self.session.open(Console, title="Status: %s" % svc, cmdlist=[cmd], closeOnSuccess=False)

class SystemInfoScreen(Screen):
    skin = """
    <screen position="center,center" size="1050,650" title="System Information">
        <widget name="title" position="20,10" size="1010,40" font="Regular;30" />
        <widget name="info" position="20,60" size="1010,560" font="Regular;22" halign="left" valign="top" />
        <widget name="help" position="20,620" size="1010,25" font="Regular;22" />
    </screen>"""

    def __init__(self, session, lang="PL"):
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
            return open(path, "r").read().strip()
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
    skin = """
    <screen name="UninstallManagerScreen" position="center,center" size="1100,660" title="Uninstall">
        <widget name="list" position="20,20" size="1060,560" scrollbarMode="showOnDemand" />
        <widget name="status" position="20,595" size="1060,40" font="Regular;24" halign="left" valign="center" />
    </screen>
    """

    def __init__(self, session, lang='PL'):
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
        cmd = "opkg remove %s" % pkg
        console_screen_open(
            self.session,
            ("Odinstalowanie: %s" % pkg) if self.lang == 'PL' else ("Removing: %s" % pkg),
            [cmd],
            callback=lambda *a: self.reload_list(),
            close_on_finish=True
        )


# === OPISY FUNKCJI DLA SYSTEMU TOOLTIP (v6.1) ===
FUNCTION_DESCRIPTIONS = {
    "PL": {
        # Lista kanałów
        "📺 Listy Kanałów": "Zarządzanie listami kanałów: instalacja, aktualizacja i przywracanie.\nObsługa importu list IPTV (M3U) oraz szybki powrót do poprzedniego stanu.",
        "📡 Paweł Pawełek HB 13E (04.01.2026)": "Oficjalna lista kanałów dla HotBird 13E.\nInstalacja listy wraz z automatycznym odświeżeniem bouquetów w Enigma2.",
        "📺 XStreamity - Instalator": "Instaluje XStreamity (IPTV).\nObsługa M3U oraz Xtream Codes; po instalacji uruchom z menu Wtyczki.",
        "📺 IPTV Dream - Instalator": "Instaluje IPTV Dream (zaawansowany odtwarzacz IPTV).\nWymagane biblioteki możesz doinstalować z pozycji zależności IPTV.",
        "📦 Konfiguracja IPTV - zależności": "Instaluje wymagane zależności/biblioteki dla wtyczek IPTV.\nZalecane uruchomienie przed instalacją playerów IPTV.",

        # Softcam i Wtyczki
        "🔑 Softcam i Wtyczki": "Sekcja narzędzi CAM i instalatorów wtyczek.\nWybierz pozycję, aby zainstalować lub uruchomić daną funkcję.",
        "🔄 Restart Oscam": "Restartuje usługę Oscam (jeśli działa w systemie).\nPrzydatne po zmianie konfiguracji lub po zawieszeniu emulatora.",
        "🧹 Kasuj hasło Oscam": "Czyści hasło dostępu do WWW Oscam (jeśli jest ustawione).\nUłatwia odzyskanie dostępu do panelu bez reinstalacji.",
        "⚙️ oscam.dvbapi - kasowanie zawartości": "Czyści (kasuje zawartość) pliku oscam.dvbapi w konfiguracji Oscam.\nPrzydatne, gdy plik zawiera błędne wpisy lub chcesz zacząć od zera.",
        "📥 Softcam - Instalator": "Instaluje Softcam za pomocą skryptu (wget | bash).\nPo instalacji możesz doinstalować/wybrać emulator oraz przejść do instalacji Oscam z feed.",
        "📥 Oscam Feed - Instalator (Auto)": "Automatycznie dobiera i instaluje Oscam z feedu (gdy dostępny).\nPo instalacji zalecany restart GUI.",
        "📥 NCam 15.6 (Instalator)": "Instaluje NCam 15.6 z feedu/instalatora.\nPo instalacji zalecany restart GUI i wybór emu w ustawieniach Softcam.",
        "📥 NCam (Feed - najnowszy)": "Instaluje najnowszy NCam z feedu Twojego systemu (opkg).\nPo instalacji zalecany restart GUI i wybór emu w ustawieniach Softcam.",
        "⚙️ ServiceApp - Instalator": "Instaluje ServiceApp (alternatywny odtwarzacz) dla lepszej obsługi streamów IPTV.\nMoże wymagać restartu Enigma2 po instalacji.",
        "🛠 AJPanel - Instalator": "Instaluje AJPanel – zestaw narzędzi serwisowych i administracyjnych.\nPrzydatne do szybkiej diagnostyki i obsługi systemu.",
        "▶️ E2iPlayer Master - Instalacja/Aktualizacja": "Instaluje lub aktualizuje E2iPlayer (Master).\nDostarcza dostęp do wielu serwisów VOD/stream i narzędzi multimedialnych.",
        "📅 EPG Import - Instalator": "Instaluje EPGImport – automatyczny import programu TV.\nPo instalacji skonfiguruj źródła EPG i harmonogram aktualizacji.",
        "🔄 S4aUpdater - Instalator": "Instaluje S4aUpdater do aktualizacji wybranych dodatków.\nUłatwia utrzymanie wtyczek w aktualnej wersji bez ręcznej instalacji.",
        "🔄 MyUpdater v5.1 - Instalator": "Instaluje MyUpdater v5.1 z oficjalnego skryptu instalacyjnego.\nSłuży do aktualizacji i utrzymania dodatków bez ręcznego pobierania paczek.",
        "📺 JediMakerXtream - Instalator": "Instaluje JediMakerXtream do budowy bukietów IPTV z kont Xtream.\nPo instalacji dodaj dane logowania i wygeneruj listę/bukiety.",
        "▶️ YouTube - Instalator": "Instaluje wtyczkę YouTube dla Enigma2.\nMoże wymagać dodatkowych bibliotek zależnych od obrazu.",
        "📦 J00zeks Feed (Repo Installer)": "Dodaje repozytorium J00zeks (feed) do systemu.\nPo instalacji możesz pobierać jego wtyczki z poziomu Menedżera wtyczek.",
        "📺 E2Kodi v2 - Instalator (j00zek)": "Instaluje E2Kodi v2 (wersja z feedu j00zek).\nUmożliwia uruchomienie środowiska Kodi na Enigma2 (zależności zależą od obrazu).",
        "🖼️ Picon Updater - Instalator (Picony)": "Instaluje narzędzie do aktualizacji piconów.\nUłatwia pobieranie i odświeżanie ikon kanałów w systemie.",

        # Narzędzia Systemowe
        "⚙️ Narzędzia Systemowe": "Zaawansowane narzędzia administracyjne systemu",
        "✨ Super Konfigurator (Pierwsza Instalacja)": "Asystent pierwszej konfiguracji tunera",
        ">>> Super Konfigurator (Pierwsza Instalacja)": "Automatyczna pierwsza konfiguracja tunera.\n\nWykonuje kolejno:\n- instalację listy kanałów (Bzyk83 13E Hotbird)\n- instalację softcamu\n- instalację najnowszego Oscam z feedu (dobór pod tuner/CPU)\n- pobranie piconów (Transparent)\nNa końcu uruchamia pełny restart systemu tunera.",
        "🗑️ Menadżer Deinstalacji": "Odinstalowywanie pakietów z systemu",
        "📡 Aktualizuj satellites.xml": "Pobiera i aktualizuje satellites.xml w systemie.\nPrzydatne przy dodawaniu nowych transponderów; zalecany restart Enigmy2.",
        "🖼️ Pobierz Picony (Transparent)": "Pobiera zestaw piconów (transparent) i przed instalacją pyta o katalog docelowy.\nMożesz wybrać lokalizację domyślną albo urządzenie zewnętrzne; po zakończeniu zalecany restart GUI.",
        "📊 Monitor Systemowy": "Podgląd wykorzystania CPU, RAM, temperatury",
        "📄 Przeglądarka Logów": "Przeglądanie logów systemowych i Enigmy2",
        "⏰ Menedżer Cron": "Zarządzanie zadaniami harmonogramu",
        "🔌 Menedżer Usług": "Zarządzanie usługami systemowymi (SSH, FTP itd.)",
        "ℹ️ Informacje o Systemie": "Szczegółowe informacje o sprzęcie i oprogramowaniu",
        "🔄 Aktualizuj oscam.srvid/srvid2": "Aktualizacja listy identyfikatorów kanałów",
        "🔑 Aktualizuj SoftCam.Key (Online)": "Pobiera i aktualizuje plik SoftCam.Key (Online) w typowych lokalizacjach kluczy.\nPo zakończeniu wykonuje restart emulatora (jeśli uruchomiony).",
        "🌐 Menedżer Feedów / Repozytoriów": "Menedżer repozytoriów opkg. Pozwala podejrzeć aktywne feedy, wykonać test połączenia z feedami, wyczyścić cache list pakietów i odświeżyć repozytoria.",
        "🛠 Tryb Naprawy po Instalacji": "Uruchamia zestaw naprawczy po instalacji dodatków lub po nieudanym update. Dostępne moduły: uprawnienia, Softcam, EPG, picony, ServiceApp i Streamlink oraz tryb pełny.",
        "💾 Backup Listy Kanałów": "Kopia zapasowa list kanałów",
        "💾 Backup Konfiguracji Oscam": "Kopia zapasowa konfiguracji Oscam",
        "♻️ Restore Listy Kanałów": "Przywracanie list kanałów z backupu",
        "♻️ Restore Konfiguracji Oscam": "Przywracanie konfiguracji Oscam z backupu",

        # Info i Diagnostyka
        "ℹ️ Info i Diagnostyka": "Informacje o wtyczce i narzędzia diagnostyczne",
        "ℹ️ Informacje o AIO Panel": "Informacje o wersji, licencji i autorze",
        "🔄 Aktualizacja Wtyczki": "Sprawdzenie i instalacja aktualizacji AIO Panel",
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
        "📦 IPTV Configuration - dependencies": "Installs required IPTV packages/libraries.\nRecommended to run before installing IPTV players.",

        # Softcam & Plugins
        "🔑 Softcam & Plugins": "CAM/tools and plugin installers section.\nSelect an item to install, update or run the selected function.",
        "🔄 Restart Oscam": "Restarts the Oscam service (if available on your image).\nUseful after config changes or when the emulator becomes unresponsive.",
        "🧹 Clear Oscam Password": "Clears the Oscam WebIF password (if configured).\nHelps regain panel access without reinstalling.",
        "⚙️ oscam.dvbapi - clear file": "Clears/truncates the oscam.dvbapi file in Oscam config directories.\nUseful if the file contains wrong entries or you want a clean start.",
        "📥 Softcam - Installer": "Installs Softcam using the installer script (wget | bash).\nAfter install you can proceed with installing Oscam from your feed.",
        "📥 Oscam Feed - Installer (Auto)": "Automatically selects and installs Oscam from feed (when available).\nGUI restart is recommended after installation.",
        "📥 NCam 15.6 (Installer)": "Installs NCam 15.6 via feed/installer.\nGUI restart recommended; then select the emulator in Softcam settings.",
        "📥 NCam (Feed - latest)": "Installs the latest NCam from your system feed (opkg).\nGUI restart recommended; then select the emulator in Softcam settings.",
        "⚙️ ServiceApp - Installer": "Installs ServiceApp (alternative playback engine) for improved IPTV/stream handling.\nMay require Enigma2 restart after installation.",
        "🛠 AJPanel - Installer": "Installs AJPanel – a set of service/administration tools.\nUseful for quick maintenance and diagnostics.",
        "▶️ E2iPlayer Master - Install/Update": "Installs or updates E2iPlayer (Master).\nProvides access to multiple streaming/VOD sources and media tools.",
        "📅 EPG Import - Installer": "Installs EPGImport for automatic EPG data import.\nAfter install, set sources and schedule periodic updates.",
        "🔄 S4aUpdater - Installer": "Installs S4aUpdater to keep selected add-ons up to date.\nReduces manual package installs/updates.",
        "🔄 MyUpdater v5.1 - Installer": "Installs MyUpdater v5.1 using the official installer script.\nHelps keep selected add-ons updated without manual package downloads.",
        "📺 JediMakerXtream - Installer": "Installs JediMakerXtream to build IPTV bouquets from Xtream accounts.\nAdd your credentials and generate bouquets after installation.",
        "▶️ YouTube - Installer": "Installs the YouTube plugin for Enigma2.\nRequired dependencies vary by image.",
        "📦 J00zeks Feed (Repo Installer)": "Adds the J00zek feed repository to your system.\nAfterwards, install his plugins via the Plugin Manager.",
        "📺 E2Kodi v2 - Installer (j00zek)": "Installs E2Kodi v2 (j00zek build).\nLets you run Kodi on Enigma2; dependencies vary by image.",
        "🖼️ Picon Updater - Installer (Picons)": "Installs a picon update utility.\nHelps download and refresh channel icons on the receiver.",

        # System Tools
        "⚙️ System Tools": "Advanced system administration tools",
        "✨ Super Setup Wizard (First Installation)": "First time tuner setup assistant",
        ">>> Super Setup Wizard (First Installation)": "Automatic first-time receiver setup.\n\nRuns in order:\n- install channel list (Paweł Pawełek)\n- install softcam\n- install the newest Oscam from feed (auto-detect tuner/CPU)\n- download picons (Transparent)\nFinally triggers a full system reboot.",
        "🗑️ Uninstallation Manager": "Uninstall packages from system",
        "📡 Update satellites.xml": "Downloads and updates satellites.xml in your system.\nRecommended after changes: restart Enigma2 for full effect.",
        "🖼️ Download Picons (Transparent)": "Downloads a transparent picon set and asks for the target folder before installation.\nYou can keep the default path or choose an external device; GUI restart recommended.",
        "📊 System Monitor": "View CPU, RAM, temperature usage",
        "📄 Log Viewer": "Browse system and Enigma2 logs",
        "⏰ Cron Manager": "Manage scheduled tasks",
        "🔌 Service Manager": "Manage system services (SSH, FTP, etc.)",
        "ℹ️ System Information": "Detailed hardware and software info",
        "🔄 Update oscam.srvid/srvid2": "Update channel identifier list",
        "🔑 Update SoftCam.Key (Online)": "Downloads and updates SoftCam.Key (Online) to common key/config locations.\nRestarts the emulator (if running).",
        "🌐 Feed / Repository Manager": "Opkg repository manager. Lets you inspect active feeds, test feed connectivity, clear package-list cache and refresh repositories.",
        "🛠 Post-Install Repair Mode": "Runs a post-install repair toolkit after a failed install/update. Available modules: permissions, Softcam, EPG, picons, ServiceApp and Streamlink, plus a full repair mode.",
        "💾 Backup Channel List": "Backup channel lists",
        "💾 Backup Oscam Config": "Backup Oscam configuration",
        "♻️ Restore Channel List": "Restore channel lists from backup",
        "♻️ Restore Oscam Config": "Restore Oscam config from backup",

        # Info & Diagnostics
        "ℹ️ Info & Diagnostics": "Plugin info and diagnostic tools",
        "ℹ️ About AIO Panel": "Version, license and author info",
        "🔄 Update Plugin": "Check and install AIO Panel updates",
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



class Panel(Screen):
    # Modern Dashboard UI v9.5 (adaptive HD/FHD layout)
    skin = _panel_main_skin()

    def __init__(self, session, fetched_data):
        Screen.__init__(self, session)
        self.setTitle("Panel AIO " + VER)
        self.sess = session
        self.lang = 'PL'
        
        # Logika detekcji obrazu
        self.image_type = "unknown"
        if fileExists("/etc/issue"):
            try:
                with open("/etc/issue", "r") as f:
                    issue_content = f.read()
                if "Hyperion" in issue_content:
                    self.image_type = "hyperion"
            except: pass
        if self.image_type == "unknown" and fileExists("/etc/image-version"):
            try:
                with open("/etc/image-version", "r") as f:
                    img_info = f.read().lower()
                if "openatv" in img_info: self.image_type = "openatv"
                elif "openpli" in img_info: self.image_type = "openpli"
            except: pass
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
        self._health_timer = eTimer()
        try:
            self._health_timer_conn = self._health_timer.timeout.connect(self._update_health)
        except Exception:
            self._health_timer.callback.append(self._update_health)
        self.onShown.append(self._start_health_timer)
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
                except:
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
        self.lang = lang
        self.set_lang_headers_and_legends()
        
        try:
            repo_lists = self.fetched_data_cache.get("repo_lists", [])
            s4a_lists_full = self.fetched_data_cache.get("s4a_lists_full", [])
            best_oscam_version = self.fetched_data_cache.get("best_oscam_version", "Error")

            if not repo_lists:
                repo_lists = [(TRANSLATIONS[lang]["loading_error_text"] + " (REPO)", "SEPARATOR")]
            
            keywords_to_remove = ['bzyk', 'jakitaki']
            s4a_lists_filtered = [item for item in s4a_lists_full if not any(keyword in item[0].lower() for keyword in keywords_to_remove)]
            final_channel_lists = repo_lists + s4a_lists_filtered
            azman_items = [item for item in final_channel_lists if 'azman' in ensure_unicode(item[0]).lower()]
            non_azman_items = [item for item in final_channel_lists if 'azman' not in ensure_unicode(item[0]).lower()]
            final_channel_lists = non_azman_items + azman_items
            
            softcam_menu = list(SOFTCAM_AND_PLUGINS_PL if lang == 'PL' else SOFTCAM_AND_PLUGINS_EN)
            tools_menu = list(SYSTEM_TOOLS_PL if lang == 'PL' else SYSTEM_TOOLS_EN)
            diag_menu = list(DIAGNOSTICS_PL if lang == 'PL' else DIAGNOSTICS_EN)
            
            # --- FILTROWANIE DLA PYTHON 2 (Kompatybilność) ---
            if IS_PY2:
                 softcam_filtered = []
                 for item in softcam_menu:
                      name, cmd = item
                      # Blokuj wtyczki, które działają tylko na Py3 lub są zbyt ciężkie dla starych boxów
                      if "E2Kodi" in name or cmd == "CMD:INSTALL_E2KODI": continue
                      if "XStreamity" in name: continue # Wersje Py2 rzadko wspierane
                      softcam_filtered.append(item)
                 softcam_menu = softcam_filtered

            # Filtrowanie dla Hyperion/VTi
            if self.image_type in ["hyperion", "vti"]:
                emu_actions_to_block = ["CMD:RESTART_OSCAM", "CMD:CLEAR_OSCAM_PASS", "CMD:MANAGE_DVBAPI", "CMD:INSTALL_SOFTCAM_SCRIPT", "CMD:INSTALL_BEST_OSCAM"]
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
                    oscam_text = "📥 Oscam Feed - {}" if lang == 'PL' else "📥 Oscam Feed - {}"
                    softcam_menu[i] = (oscam_text.format(best_oscam_version), action)
            
            for i, (name, action) in enumerate(tools_menu):
                if action == "CMD:SUPER_SETUP_WIZARD":
                    tools_menu[i] = (TRANSLATIONS[lang]["sk_wizard_title"], action)

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
        prefix = ("Wskazówka #{0}/{1}" if self.lang == "PL" else "Tip #{0}/{1}").format(idx + 1, len(tips))
        show_message_compat(self.sess, "{}\n\n{}".format(prefix, tips[idx]), timeout=14)

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
        """Convert separator titles like '\c00FFD200--- Softcamy ---\c00ffffff' into 'Softcamy'."""
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


    def _start_health_timer(self):
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
            "CMD:INSTALL_E2KODI", "CMD:INSTALL_J00ZEK_REPO", "CMD:CLEAR_TMP_CACHE", "CMD:CLEAR_RAM_CACHE",
            "CMD:INSTALL_SOFTCAM_SCRIPT", "CMD:INSTALL_IPTV_DREAM", "CMD:SETUP_AUTO_RAM",
            "CMD:FEED_MANAGER", "CMD:POSTINSTALL_REPAIR"
        ]
        
        if self.image_type in ["hyperion", "vti"] and action == "CMD:MANAGE_DVBAPI":
             self.sess.openWithCallback(lambda ret: self.execute_action(name, action) if ret else None, MessageBox, "UWAGA (Hyperion/VTi): Opcja może nie działać.\nKontynuować?", type=MessageBox.TYPE_YESNO); return

        if any(action.startswith(prefix) for prefix in actions_no_confirm):
            self.execute_action(name, action)
        else:
            self.sess.openWithCallback(lambda ret: self.execute_action(name, action) if ret else None, MessageBox, "Czy wykonać akcję:\n'{}'?".format(name), type=MessageBox.TYPE_YESNO)

    def clear_ram_memory(self):
        os.system("sync; echo 3 > /proc/sys/vm/drop_caches")
        self.sess.open(MessageBox, "Pamięć RAM została wyczyszczona.", MessageBox.TYPE_INFO)

    def clear_tmp_cache(self):
        try:
            os.system("rm -rf /tmp/*.ipk /tmp/*.zip /tmp/*.tar.gz /tmp/*.tgz /tmp/epg.dat")
            self.sess.open(MessageBox, "Wyczyszczono pamięć podręczną /tmp.", MessageBox.TYPE_INFO)
        except Exception as e:
            self.sess.open(MessageBox, "Błąd: {}".format(e), MessageBox.TYPE_ERROR)

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
        # Wersja cicha - uruchamiana w tle
        self._check_update(silent=True)

    def check_for_updates_manual(self):
        self.session.openWithCallback(self._manual_update_callback, MessageBox, "Sprawdzanie dostępności aktualizacji...", type=MessageBox.TYPE_INFO, timeout=3)
        # Callback uruchomi się po zamknięciu komunikatu, ale lepiej uruchomić sprawdzanie w tle
        self._check_update(silent=False)

    def _manual_update_callback(self, result):
        pass

    def _check_update(self, silent=False):
        # URL do pliku version.txt w Twoim repozytorium
        version_url = "https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/version.txt"
        tmp_ver_path = "/tmp/aio_version.txt"
        
        try:
            # Pobieranie pliku wersji (używamy wget dla kompatybilności z E2)
            os.system("wget -q -T 10 -O {} {}".format(tmp_ver_path, version_url))
            
            if not os.path.exists(tmp_ver_path):
                if not silent:
                    reactor.callFromThread(show_message_compat, self.sess, TRANSLATIONS[self.lang]["update_check_error"], MessageBox.TYPE_ERROR)
                return

            with open(tmp_ver_path, 'r') as f:
                remote_ver_str = f.read().strip()
            
            # Proste porównanie wersji (np. 6.0 > 5.0)
            try:
                local_ver = float(VER)
                remote_ver = float(remote_ver_str)
            except ValueError:
                # Fallback jeśli wersja zawiera litery (np. 6.0b)
                local_ver = VER
                remote_ver = remote_ver_str

            if remote_ver > local_ver:
                # Znaleziono nową wersję!
                changelog_text = "Aktualizacja zalecana."
                # Opcjonalnie: pobierz changelog tutaj, jeśli chcesz
                
                msg = TRANSLATIONS[self.lang]["update_available_msg"].format(
                    latest_ver=remote_ver_str, 
                    current_ver=VER, 
                    changelog=changelog_text
                )
                
                reactor.callFromThread(self.sess.openWithCallback, self._do_update_action, MessageBox, msg, MessageBox.TYPE_YESNO)
            else:
                if not silent:
                    reactor.callFromThread(show_message_compat, self.sess, TRANSLATIONS[self.lang]["already_latest"].format(ver=VER), MessageBox.TYPE_INFO)
                    
        except Exception as e:
            print("[AIO Panel] Update check error:", e)
            if not silent:
                reactor.callFromThread(show_message_compat, self.sess, TRANSLATIONS[self.lang]["update_generic_error"], MessageBox.TYPE_ERROR)

    def _do_update_action(self, confirmed):
        if not confirmed:
            return
        
        # Uruchomienie installera z GitHuba
        installer_url = "https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh"
        cmd = "wget -qO- --no-check-certificate {} | /bin/sh".format(installer_url)
        
        # Bezpieczniej uruchomić to w konsoli widocznej dla usera:
        console_screen_open(self.sess, "Aktualizacja AIO Panel", [cmd], callback=lambda *args: reactor.callLater(1, lambda: self.sess.open(TryQuitMainloop, 3)), close_on_finish=True)


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

    # --- GŁÓWNY WYKONAWCA AKCJI ---
    def execute_action(self, name, action):
        title = name
        if action.startswith("archive:"):
            archive_url = action.split(':', 1)[1]
            if archive_url == "https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip" or "picon" in title.lower():
                self._prompt_picon_target(title, archive_url)
            else:
                install_archive(self.sess, title, archive_url, callback_on_finish=self.reload_settings_python)
        elif action.startswith("m3u:"):
            parts = action.split(':', 3)
            self.install_m3u_as_bouquet(title, parts[1] + ":" + parts[2], parts[3].split(':', 1)[0], parts[3].split(':', 1)[1] if len(parts[3].split(':', 1)) > 1 else parts[3].split(':', 1)[0])
        elif action.startswith("bouquet:"):
            parts = action.split(':', 3)
            self.install_bouquet_reference(title, parts[1] + ":" + parts[2], parts[3].split(':', 1)[0], parts[3].split(':', 1)[1] if len(parts[3].split(':', 1)) > 1 else parts[3].split(':', 1)[0])
        elif action.startswith("bash_raw:"):
            self.session.open(Console, title=title, cmdlist=[action.split(':', 1)[1]], closeOnSuccess=False)
        elif action.startswith("CMD:"):
            key = action.split(':', 1)[1]
            if key == "SUPER_SETUP_WIZARD": self.run_super_setup_wizard()
            elif key == "CHECK_FOR_UPDATES": self.check_for_updates_manual()
            elif key == "UPDATE_SATELLITES_XML": run_command_in_background(self.sess, title, ["bash " + os.path.join(PLUGIN_PATH, "update_satellites_xml.sh")], callback_on_finish=self.reload_settings_python)
            elif key == "INSTALL_SERVICEAPP": run_command_in_background(self.sess, title, ["opkg update && opkg install enigma2-plugin-systemplugins-serviceapp exteplayer3 gstplayer && opkg install uchardet --force-reinstall"])
            elif key == "IPTV_DEPS": self.install_iptv_deps()
            elif key == "INSTALL_BEST_OSCAM": self.install_best_oscam()
            elif key == "INSTALL_SOFTCAM_SCRIPT": self.install_softcam_script()
            elif key == "INSTALL_NCAM_FEED": self.install_ncam_feed()
            elif key == "INSTALL_IPTV_DREAM": self.install_iptv_dream_simplified()
            elif key == "MANAGE_DVBAPI": self.manage_dvbapi()
            elif key == "UNINSTALL_MANAGER": self.show_uninstall_manager()
            elif key == "CLEAR_OSCAM_PASS": self.clear_oscam_password() 
            elif key == "CLEAR_FTP_PASS": run_command_in_background(self.sess, title, ["passwd -d root"])
            elif key == "SET_SYSTEM_PASSWORD": self.set_system_password()
            elif key == "RESTART_OSCAM": self.restart_oscam()
            elif key == "SETUP_AUTO_RAM": self.show_auto_ram_menu()
            elif key == "CLEAR_TMP_CACHE": self.clear_tmp_cache()
            elif key == "CLEAR_RAM_CACHE": self.clear_ram_memory()
            elif key == "INSTALL_E2KODI": install_e2kodi(self.sess)
            elif key == "INSTALL_J00ZEK_REPO": self.install_j00zek_repo()
            elif key == "SHOW_AIO_INFO": self.show_info_screen()
            elif key == "BACKUP_LIST": self.backup_lists()
            elif key == "BACKUP_OSCAM": self.backup_oscam()
            elif key == "FEED_MANAGER": self.open_feed_manager()
            elif key == "POSTINSTALL_REPAIR": self.open_postinstall_repair()
            elif key == "RESTORE_LIST": self.restore_lists()
            elif key == "RESTORE_OSCAM": self.restore_oscam()
            elif key == "SYSTEM_MONITOR": self.open_system_monitor()
            elif key == "LOG_VIEWER": self.open_log_viewer()
            elif key == "CRON_MANAGER": self.open_cron_manager()
            elif key == "SERVICE_MANAGER": self.open_service_manager()
            # REMOVED: NETWORK_TOOLS
            elif key == "SYSTEM_INFO": self.open_system_info()
            # REMOVED: AUTO_BACKUP
            elif key == "NETWORK_DIAGNOSTICS": self.run_network_diagnostics()
            elif key == "FREE_SPACE_DISPLAY": console_screen_open(self.sess, "Wolne miejsce", ["df -h"], close_on_finish=False)
            elif key == "SMART_CLEANUP": self.smart_cleanup()
            elif key == "AIO_QUICKSTART": self.open_aio_quickstart()
            elif key == "COMPATIBILITY_CHECK": self.open_compatibility_check()
            elif key == "SHOW_AIO_TIP": self.show_aio_tip()
            elif key == "LOCAL_CHANGELOG": self.show_local_changelog()
            
            # --- ZMIANY TUTAJ: Obsługa nowych funkcji ---
            elif key == "UPDATE_SRVID": self.update_oscam_srvid_files() # Poprawiona
            elif key == "INSTALL_SOFTCAMKEY_ONLINE": self.install_softcam_key_online() # Nowa

    # --- FUNKCJE INSTALACYJNE I POMOCNICZE ---
    
    # NAPRAWIONY SUPER KONFIGURATOR Z OPISEM
    def run_super_setup_wizard(self):
        lang = self.lang
        options = [
            (TRANSLATIONS[lang]["sk_option_deps"], "deps_only"),
            (TRANSLATIONS[lang]["sk_option_basic_no_picons"], "install_basic_no_picons"),
            (TRANSLATIONS[lang]["sk_option_full_picons"], "install_with_picons"),
            (TRANSLATIONS[lang]["sk_option_cancel"], "cancel")
        ]

        # Mapa opisów dla opcji
        desc_map = {
            "deps_only": "Tylko podstawowe pakiety systemowe (wget, tar, unzip).\nNie zmienia konfiguracji kanałów ani softcamu.",
            "install_basic_no_picons": "Konfiguracja standardowa:\n- Lista kanałów\n- Instalacja Softcam (skrypt)\n- Instalacja Oscam z feed\n- Restart GUI\nSzybka instalacja.",
            "install_with_picons": "Konfiguracja pełna:\n- Lista kanałów\n- Instalacja Softcam (skrypt)\n- Instalacja Oscam z feed\n- PICONY (Transparent)\nUWAGA: Trwa dłużej i wymaga restartu systemu.",
            "cancel": "Powrót do menu."
        }
        if lang != "PL":
            desc_map = {
                "deps_only": "Install only basic system packages (wget, tar, unzip).\nDoes not change channel lists or softcam.",
                "install_basic_no_picons": "Standard configuration:\n- Channel list\n- Install Softcam (script)\n- Install Oscam from feed\n- GUI Restart\nFast installation.",
                "install_with_picons": "Full configuration:\n- Channel list\n- Install Softcam (script)\n- Install Oscam from feed\n- PICONS (Transparent)\nNOTE: Takes longer and requires full system reboot.",
                "cancel": "Back to menu."
            }

        # Użycie nowej klasy zamiast standardowego ChoiceBox
        self.sess.openWithCallback(
            self._super_wizard_selected,
            SuperWizardChoiceScreen,
            options=options,
            title=TRANSLATIONS[lang]["sk_choice_title"],
            description_map=desc_map
        )

    def _super_wizard_selected(self, choice):
        if not choice or choice[1] == "cancel":
            return

        key, lang = choice[1], self.lang
        steps = []

        if key == "deps_only":
            steps = ["deps"]
        elif key == "install_basic_no_picons":
            steps = ["channel_list", "install_softcam", "install_oscam", "reload_settings"]
        elif key == "install_with_picons":
            steps = ["channel_list", "install_softcam", "install_oscam", "picons", "reload_settings"]

        if steps:
            picon_url = 'https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip'
            channel_list_url = 'https://raw.githubusercontent.com/OliOli2013/PanelAIO-Lists/main/archives/bzyk83_hb_13E_2026_02_24.zip'
            list_name = 'Bzyk83 Hotbird 13E (2026-02-24)'

            try:
                repo_lists = self.fetched_data_cache.get("repo_lists", [])
                for item in repo_lists:
                    if isinstance(item, (list, tuple)) and len(item) >= 2 and str(item[1]).startswith("archive:"):
                        t = str(item[0]).lower()
                        if ("bzyk83" in t or "bzyk 83" in t) and ("13e" in t) and ("hotbird" in t) and ("dual" not in t):
                            channel_list_url = str(item[1]).split(':', 1)[1]
                            list_name = str(item[0]).replace("📡 ", "")
                            break
            except Exception:
                pass

            self.sess.open(
                WizardProgressScreen,
                steps=steps,
                channel_list_url=channel_list_url,
                channel_list_name=list_name,
                picon_url=picon_url,
                reboot_mode=("full" if key == "install_with_picons" else "gui")
            )

    def toggle_menu_visibility(self):
        # Toggle visibility of AIO Panel entry in receiver main/system menu (WHERE_MENU)
        try:
            if config is None or not hasattr(config.plugins, 'panelaio') or not hasattr(config.plugins.panelaio, 'show_in_menu'):
                show_message_compat(self.sess, 'Brak obsługi ustawień na tym obrazie.', MessageBox.TYPE_ERROR)
                return
            config.plugins.panelaio.show_in_menu.value = not config.plugins.panelaio.show_in_menu.value
            try:
                config.plugins.panelaio.show_in_menu.save()
                if configfile is not None:
                    configfile.save()
            except Exception:
                pass
            state = 'WŁĄCZONE' if config.plugins.panelaio.show_in_menu.value else 'WYŁĄCZONE'
            show_message_compat(
                self.sess,
                'Widoczność w menu tunera: %s\n\nZmiana zadziała po restarcie GUI.' % state,
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
        tmp = os.path.join(PLUGIN_TMP_PATH, "temp.m3u")
        run_command_in_background(self.sess, title, ["wget -T 30 --no-check-certificate -O \"{}\" \"{}\"".format(tmp, url)], 
                                  callback_on_finish=lambda: Thread(target=self._parse_m3u_thread, args=(tmp, bouquet_id, bouquet_name)).start())

    def _parse_m3u_thread(self, tmp_path, bid, bname):
        try:
            if not os.path.exists(tmp_path): return
            e2 = ["#NAME {}\n".format(bname)]
            with io.open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                name = "N/A"
                for line in f:
                    l = line.strip()
                    if l.startswith('#EXTINF:'): name = l.split(',')[-1].strip()
                    elif l.startswith('http'): e2.append("#SERVICE 4097:0:1:0:0:0:0:0:0:0:{}:{}\n".format(l.replace(':', '%3a'), name)); name="N/A"
            if len(e2) > 1:
                t_bq = os.path.join(PLUGIN_TMP_PATH, bid)
                with open(t_bq, 'w') as f: f.writelines(e2)
                reactor.callFromThread(self._install_parsed_bouquet, t_bq, bid)
        except Exception: pass

    def _install_parsed_bouquet(self, t_bq, bid):
        try:
            shutil.move(t_bq, os.path.join("/etc/enigma2", bid))
            with open("/etc/enigma2/bouquets.tv", 'r+') as f:
                if bid not in f.read(): f.write('#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "{}" ORDER BY bouquet\n'.format(bid))
            self.reload_settings_python()
        except Exception: pass

    def install_bouquet_reference(self, title, url, bid, bname):
        cmd = "wget -qO \"/etc/enigma2/{b}\" \"{u}\" && (grep -q \"{b}\" /etc/enigma2/bouquets.tv || echo '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"{b}\" ORDER BY bouquet' >> /etc/enigma2/bouquets.tv)".format(b=bid, u=url)
        run_command_in_background(self.sess, title, [cmd], callback_on_finish=self.reload_settings_python)

    # --- NOWA, NAPRAWIONA FUNKCJA SRVID (Źródło: Aktualne repozytoria) ---
    def update_oscam_srvid_files(self):
        title = "Aktualizacja oscam.srvid / oscam.srvid2"
        dst_dir = "/etc/tuxbox/config"

        # Stabilne źródła
        srvid_urls = [
            "https://raw.githubusercontent.com/openmb/open-pli-core/master/meta-openpli/recipes-openpli/enigma2-softcams/enigma2-plugin-softcams-oscam/oscam.srvid",
            "https://raw.githubusercontent.com/bmihovski/Oscam-Services-Bulcrypt/master/oscam.srvid",
        ]
        srvid2_urls = [
            "https://raw.githubusercontent.com/openmb/open-pli-core/master/meta-openpli/recipes-openpli/enigma2-softcams/enigma2-plugin-softcams-oscam/oscam.srvid2",
        ]

        cmd = r"""            set -e

            BASE="{dst}"

            TARGET_DIRS=$(find "$BASE" -type f -name oscam.conf -exec dirname {{}} \; 2>/dev/null | sort -u)
            if [ -z "$TARGET_DIRS" ]; then
                TARGET_DIRS="$BASE"
            else
                echo "$TARGET_DIRS" | grep -qx "$BASE" || TARGET_DIRS="$BASE $TARGET_DIRS"
            fi

            WORK="/tmp/aio_srvid_work"
            mkdir -p "$WORK"

            echo "Tworzenie kopii w katalogach docelowych..."
            for D in $TARGET_DIRS; do
                [ -d "$D" ] || continue
                [ -f "$D/oscam.srvid" ]  && cp -f "$D/oscam.srvid"  "$D/oscam.srvid.bak"  || true
                [ -f "$D/oscam.srvid2" ] && cp -f "$D/oscam.srvid2" "$D/oscam.srvid2.bak" || true
            done

            is_valid_srvid() {{
                # odrzucamy HTML / puste / podejrzane pliki
                [ -s "$1" ] || return 1
                head -n 5 "$1" | grep -qiE '^\s*<|<!doctype|<html' && return 1
                grep -qE '^[0-9A-Fa-f,]+:[0-9A-Fa-f]+' "$1" || return 1
                return 0
            }}

            is_valid_srvid2() {{
                [ -s "$1" ] || return 1
                head -n 5 "$1" | grep -qiE '^\s*<|<!doctype|<html' && return 1
                grep -qE '^[0-9A-Fa-f]+:[0-9A-Fa-f]+' "$1" || return 1
                return 0
            }}

            echo "Pobieranie oscam.srvid z repo (jeśli dostępne)..."
            SRVID_OK=0
            for URL in {srvid_urls}; do
                echo " - $URL"
                if wget -q --no-check-certificate -U "Enigma2" -O "$WORK/oscam.srvid.tmp" "$URL"; then
                    if is_valid_srvid "$WORK/oscam.srvid.tmp"; then
                        SRVID_OK=1
                        break
                    else
                        echo "   (pomijam: plik nie wygląda jak oscam.srvid)"
                    fi
                fi
            done

            if [ "$SRVID_OK" -ne 1 ]; then
                echo "Repo nie dało poprawnego pliku – generowanie z KingOfSat..."
                rm -f "$WORK/oscam.srvid.tmp"
                echo "# Generated by AIO Panel - $(date)" > "$WORK/oscam.srvid.tmp"
                echo "# Source: KingOfSat.net (fallback)" >> "$WORK/oscam.srvid.tmp"
                echo "" >> "$WORK/oscam.srvid.tmp"

                PACKS="polsat:0B01,0B02,0B03,0B04 canal:0100,0500,1803,1813,0D00,0D01"

                for PACK in $PACKS; do
                    PACK_NAME=$(echo "$PACK" | cut -d: -f1)
                    CAIDS=$(echo "$PACK" | cut -d: -f2)
                    echo "Pobieranie danych dla $PACK_NAME..."
                    if wget -q --user-agent="Mozilla/5.0" -O "/tmp/kos_${{PACK_NAME}}.html" "http://en.kingofsat.net/pack-${{PACK_NAME}}.php" 2>/dev/null; then
                        grep -o 'href="channel.php[^"]*">[^<]*</a>' "/tmp/kos_${{PACK_NAME}}.html" | \
                            sed -e 's/.*channel\.php[^>]*>\([^<]*\)<\/a>.*/\1/' | \
                            head -n 2000 > "/tmp/channels_${{PACK_NAME}}.txt" || true

                        grep -o 'serviceid=[0-9A-Fa-f]\{{4\}}' "/tmp/kos_${{PACK_NAME}}.html" | \
                            sed -e 's/serviceid=//' | \
                            head -n 2000 > "/tmp/sids_${{PACK_NAME}}.txt" || true

                        paste -d'|' "/tmp/sids_${{PACK_NAME}}.txt" "/tmp/channels_${{PACK_NAME}}.txt" | \
                            while IFS='|' read -r SID CH; do
                                [ -n "$SID" ] && [ -n "$CH" ] && echo "${{CAIDS}}:${{SID}}|${{PACK_NAME}}|${{CH}}|TV|" >> "$WORK/oscam.srvid.tmp"
                            done
                    fi
                done

                rm -f /tmp/kos_*.html /tmp/channels_*.txt /tmp/sids_*.txt || true

                if ! is_valid_srvid "$WORK/oscam.srvid.tmp"; then
                    echo "Błąd: Nie udało się pobrać/wygenerować poprawnego oscam.srvid."
                    exit 1
                fi
            fi

            echo "Pobieranie oscam.srvid2 z repo (jeśli istnieje)..."
            SRVID2_OK=0
            for URL in {srvid2_urls}; do
                echo " - $URL"
                if wget -q --no-check-certificate -U "Enigma2" -O "$WORK/oscam.srvid2.tmp" "$URL"; then
                    if is_valid_srvid2 "$WORK/oscam.srvid2.tmp"; then
                        SRVID2_OK=1
                        break
                    else
                        echo "   (pomijam: plik nie wygląda jak oscam.srvid2)"
                    fi
                fi
            done

            if [ "$SRVID2_OK" -ne 1 ]; then
                echo "Generowanie oscam.srvid2 z oscam.srvid..."
                rm -f "$WORK/oscam.srvid2.tmp"
                echo "# Generated by AIO Panel - $(date)" > "$WORK/oscam.srvid2.tmp"
                echo "# Source: oscam.srvid (local convert)" >> "$WORK/oscam.srvid2.tmp"
                echo "" >> "$WORK/oscam.srvid2.tmp"

                awk -F'[:|]' 'BEGIN{{OFS=""}}
                    $0 ~ /^#/ {{next}}
                    NF >= 2 {{
                        caids=$1; sid=$2;
                        provider=(NF>=3)?$3:"";
                        name=(NF>=4)?$4:"";
                        type=(NF>=5)?$5:"";
                        desc=(NF>=6)?$6:"";
                        if (name == "" && provider != "") {{ name=provider; provider="" }}
                        print sid ":" caids "|" name "|" type "|" desc "|" provider
                    }}
                ' "$WORK/oscam.srvid.tmp" >> "$WORK/oscam.srvid2.tmp"

                if ! is_valid_srvid2 "$WORK/oscam.srvid2.tmp"; then
                    echo "Błąd: Nie udało się utworzyć poprawnego oscam.srvid2."
                    exit 1
                fi
            fi

            echo "Instalacja plików do katalogów:"
            for D in $TARGET_DIRS; do
                [ -d "$D" ] || continue
                echo " - $D"
                cp -f "$WORK/oscam.srvid.tmp"  "$D/oscam.srvid"
                cp -f "$WORK/oscam.srvid2.tmp" "$D/oscam.srvid2"
            done

            rm -f "$WORK/oscam.srvid.tmp" "$WORK/oscam.srvid2.tmp" 2>/dev/null || true

            echo "Zakończono. Restart softcam (jeśli uruchomiony)..."
            killall -HUP oscam 2>/dev/null || true
            /etc/init.d/softcam restart 2>/dev/null || true
            sleep 2""".format(
            dst=dst_dir,
            srvid_urls=" ".join(['"%s"' % u for u in srvid_urls]),
            srvid2_urls=" ".join(['"%s"' % u for u in srvid2_urls]),
        )
        console_screen_open(self.sess, title, [cmd], close_on_finish=False)
    def install_softcam_key_online(self):
        title = "Aktualizacja SoftCam.Key (Online)"
        url = "https://raw.githubusercontent.com/MOHAMED19OS/SoftCam_Emu/main/SoftCam.Key"
        url_alt = "https://raw.githubusercontent.com/PAKO34/softcam.key/master/softcam.key"
        
        cmd = r'''
            URL="{url}"
            URL_ALT="{url_alt}"

            BASE="/etc/tuxbox/config"
            CONF_DIRS=$(find "$BASE" -type f -name oscam.conf -exec dirname {{}} \; 2>/dev/null | sort -u)
            if [ -z "$CONF_DIRS" ]; then
                CONF_DIRS="$BASE"
            else
                echo "$CONF_DIRS" | grep -qx "$BASE" || CONF_DIRS="$BASE $CONF_DIRS"
            fi

            # Docelowo: wszystkie katalogi z oscam.conf + standardowy katalog /usr/keys
            TARGETS="$CONF_DIRS /usr/keys"
            FOUND=0

            echo "Pobieranie SoftCam.Key z repozytorium MOHAMED19OS (SoftCam_Emu)..."
            if ! wget --no-check-certificate -U "Enigma2" -qO /tmp/SoftCam.Key.dl "$URL"; then
                echo "Główne źródło niedostępne, próbuję alternatywnego źródła..."
                echo "Pobieranie SoftCam.Key z repozytorium PAKO34..."
                if ! wget --no-check-certificate -U "Enigma2" -qO /tmp/SoftCam.Key.dl "$URL_ALT"; then
                    echo "BŁĄD: Nie udało się pobrać pliku SoftCam.Key z żadnego źródła."
                    exit 1
                fi
            fi

            if [ -s "/tmp/SoftCam.Key.dl" ]; then
                echo "Pobrano pomyślnie."
                for T in $TARGETS; do
                    [ -d "$T" ] || mkdir -p "$T"
                    if [ -d "$T" ]; then
                        echo "Instalacja w: $T"
                        [ -f "$T/SoftCam.Key" ] && cp -f "$T/SoftCam.Key" "$T/SoftCam.Key.bak"
                        cp -f /tmp/SoftCam.Key.dl "$T/SoftCam.Key"
                        FOUND=1
                    fi
                done
                rm -f /tmp/SoftCam.Key.dl

                if [ $FOUND -eq 1 ]; then
                    echo "Klucze zaktualizowane."
                    echo "Restartowanie emulatorów..."
                    killall -9 oscam 2>/dev/null
                    /etc/init.d/softcam restart 2>/dev/null || systemctl restart oscam 2>/dev/null
                else
                    echo "Ostrzeżenie: Nie znaleziono katalogów docelowych (config/keys)."
                fi
            else
                echo "BŁĄD: Nie udało się pobrać pliku SoftCam.Key."
                exit 1
            fi
            sleep 3
        '''.format(url=url, url_alt=url_alt)
        console_screen_open(self.sess, title, [cmd], close_on_finish=False)



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
                    wget -qO /dev/null --no-check-certificate -T 10 "$URL" >/dev/null 2>&1 && return 0
                    wget -qO /dev/null -T 10 "$URL" >/dev/null 2>&1 && return 0
                    curl -k -L -m 10 -o /dev/null -s "$URL" >/dev/null 2>&1 && return 0
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
                /etc/init.d/softcam stop 2>/dev/null || true
                killall -9 oscam ncam softcam 2>/dev/null || true
                sleep 2
                /etc/init.d/softcam start 2>/dev/null || /etc/init.d/softcam restart 2>/dev/null || systemctl restart softcam 2>/dev/null || systemctl restart oscam 2>/dev/null || true
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
            opkg list-installed | grep -Ei 'oscam|ncam|softcam|streamlink|serviceapp|exteplayer3|xstreamity|e2iplayer|youtube|jedi|epg|kodi|vavoo|filmxy|footonsat' >> "$OUT" 2>/dev/null || opkg list-installed >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"

            echo "=== ENIGMA2 CONFIG ===" >> "$OUT"
            ls -la /etc/enigma2 >> "$OUT" 2>/dev/null || true
            echo "" >> "$OUT"
            echo "Report saved to: $OUT"
        '''.format(out_file=out_file, out_dir=out_dir, ver=VER, py_branch=('Py3' if IS_PY3 else 'Py2'))
        console_screen_open(self.sess, title, [cmd], close_on_finish=False)

    def smart_cleanup(self):
        title = "Smart Cleanup"
        cmd = r'''
            BEFORE=$(df -k / 2>/dev/null | awk 'NR==2 {print $4}')
            echo "=== AIO Smart Cleanup ==="
            echo "Start: $(date)"
            echo ""

            echo "[1/4] Czyszczenie archiwów i plików tymczasowych z /tmp..."
            rm -f /tmp/*.ipk /tmp/*.zip /tmp/*.tar.gz /tmp/*.tgz /tmp/*.tbz2 /tmp/*.tmp /tmp/epg.dat 2>/dev/null || true
            rm -f /tmp/enigma2_crash*.log /tmp/*crash*.log /tmp/*debug*.log 2>/dev/null || true

            echo "[2/4] Czyszczenie crashlogów i logów użytkownika..."
            rm -f /home/root/enigma2_crash*.log /home/root/*crash*.log 2>/dev/null || true
            if [ -d /home/root/logs ]; then
                find /home/root/logs -type f \( -name '*.log' -o -name '*.txt' \) -print -delete 2>/dev/null || true
            fi

            echo "[3/4] Czyszczenie cache menedżera pakietów..."
            rm -rf /var/cache/opkg/* /var/lib/opkg/lists/* 2>/dev/null || true

            echo "[4/4] Sync + odświeżenie RAM cache..."
            sync
            echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
            sync

            AFTER=$(df -k / 2>/dev/null | awk 'NR==2 {print $4}')
            if [ -n "$BEFORE" ] && [ -n "$AFTER" ]; then
                GAIN=$((AFTER - BEFORE))
                echo ""
                echo "Odzyskane miejsce w głównym systemie: ${GAIN} KB"
            fi
            echo "Koniec: $(date)"
        '''
        console_screen_open(self.sess, title, [cmd], close_on_finish=False)

    def _get_backup_path(self):
        if os.path.exists("/media/hdd") and os.path.ismount("/media/hdd"): return "/media/hdd/aio_backups/"
        elif os.path.exists("/media/usb") and os.path.ismount("/media/usb"): return "/media/usb/aio_backups/"
        elif os.path.exists("/media/hdd"): return "/media/hdd/aio_backups/"
        elif os.path.exists("/media/usb"): return "/media/usb/aio_backups/"
        return None

    def backup_lists(self):
        path = self._get_backup_path()
        if not path:
            show_message_compat(self.sess, "Brak nośnika HDD/USB.", MessageBox.TYPE_ERROR); return
        cmd = "mkdir -p \"{p}\" && cd /etc/enigma2 && tar -czf \"{p}aio_channels_backup.tar.gz\" lamedb bouquets.tv bouquets.radio userbouquet.*.tv userbouquet.*.radio 2>/dev/null && echo 'Backup OK'".format(p=path)
        run_command_in_background(self.sess, "Backup Listy", [cmd])

    def backup_oscam(self):
        path = self._get_backup_path()
        if not path:
            show_message_compat(self.sess, "Brak nośnika HDD/USB.", MessageBox.TYPE_ERROR); return
        cmd = "mkdir -p \"{p}\" && cd /etc/tuxbox/config && tar -czf \"{p}aio_oscam_config_backup.tar.gz\" . && echo 'Backup Oscam OK'".format(p=path)
        run_command_in_background(self.sess, "Backup Oscam", [cmd])

    def restore_lists(self):
        path = self._get_backup_path()
        if not path: return
        f = os.path.join(path, "aio_channels_backup.tar.gz")
        if not fileExists(f): show_message_compat(self.sess, "Brak pliku backupu.", MessageBox.TYPE_ERROR); return
        self.sess.openWithCallback(lambda c: run_command_in_background(self.sess, "Przywracanie", ["tar -xzf \"{}\" -C /etc/enigma2/".format(f)], self.reload_settings_python) if c else None, MessageBox, "Przywrócić listę?", MessageBox.TYPE_YESNO)

    def restore_oscam(self):
        path = self._get_backup_path()
        if not path: return
        f = os.path.join(path, "aio_oscam_config_backup.tar.gz")
        if not fileExists(f): show_message_compat(self.sess, "Brak pliku backupu.", MessageBox.TYPE_ERROR); return
        self.sess.openWithCallback(lambda c: run_command_in_background(self.sess, "Przywracanie", ["tar -xzf \"{}\" -C /etc/tuxbox/config/".format(f)], self.restart_oscam) if c else None, MessageBox, "Przywrócić Oscam?", MessageBox.TYPE_YESNO)
    def run_network_diagnostics(self):
        self.sess.open(NetworkDiagnosticsSummaryScreen, self.lang)

    def restart_gui(self): self.sess.open(TryQuitMainloop, 3)
    def reload_settings_python(self, *args): eDVBDB.getInstance().reloadServicelist(); eDVBDB.getInstance().reloadBouquets(); show_message_compat(self.sess, "Listy przeładowane.", timeout=3)
    def clear_oscam_password(self): run_command_in_background(self.sess, "Kasowanie hasła", ["sed -i '/httppwd/d' /etc/tuxbox/config/oscam.conf"])
    def manage_dvbapi(self):
        opt = [("Kasuj zawartość", "clear")] if self.lang == 'PL' else [("Clear file", "clear")]
        self.sess.openWithCallback(self._manage_dvbapi_selected, ChoiceBox, title="oscam.dvbapi", list=opt)

    def _manage_dvbapi_selected(self, choice):
        if not choice:
            return
        if choice[1] == "clear":
            cmd = r"""
                BASE="/etc/tuxbox/config"
                TARGET_DIRS=$(find "$BASE" -type f -name oscam.conf -exec dirname {} \; 2>/dev/null | sort -u)
                if [ -z "$TARGET_DIRS" ]; then
                    TARGET_DIRS="$BASE"
                else
                    echo "$TARGET_DIRS" | grep -qx "$BASE" || TARGET_DIRS="$BASE $TARGET_DIRS"
                fi

                for D in $TARGET_DIRS; do
                    [ -d "$D" ] || mkdir -p "$D"
                    : > "$D/oscam.dvbapi"
                    # kompatybilność (stare/literówka): jeśli istnieje, wyczyść też oscam.dvbap
                    [ -f "$D/oscam.dvbap" ] && : > "$D/oscam.dvbap" || true
                done
                sync
                sleep 1
            """
            run_command_in_background(
                self.sess,
                "Kasowanie oscam.dvbapi" if self.lang == 'PL' else "Clearing oscam.dvbapi",
                [cmd]
            )

    def set_system_password(self): self.sess.openWithCallback(lambda p: run_command_in_background(self.sess, "Hasło", ["(echo {0}; echo {0}) | passwd".format(p)]) if p else None, InputBox, title="Nowe hasło root")
    def restart_oscam(self, *args): run_command_in_background(self.sess, "Restart Oscam", ["killall -9 oscam; /etc/init.d/softcam restart"])
    def show_uninstall_manager(self):
        self.sess.open(UninstallManagerScreen, self.lang)
    def install_best_oscam(self):
        title = "Oscam - Instalator (Auto)" if self.lang == 'PL' else "Oscam - Installer (Auto)"
        cmd = r"""
            echo "=== Oscam installer (feed) ==="
            opkg update || true
            echo "Searching for best Oscam package in feeds..."
            CAND=""
            for p in enigma2-plugin-softcams-oscam enigma2-plugin-softcams-oscam-emu oscam oscam-emu oscam-smod; do
                if opkg list | awk '{print $1}' | grep -qx "$p"; then CAND="$p"; break; fi
            done
            if [ -z "$CAND" ]; then
                CAND=$(opkg list | awk 'BEGIN{IGNORECASE=1} $1 ~ /oscam/ {print $0}' | grep -E 'master|emu|stable' | head -n 1 | awk '{print $1}')
            fi
            if [ -z "$CAND" ]; then
                CAND=$(opkg list | awk 'BEGIN{IGNORECASE=1} $1 ~ /oscam/ {print $1; exit}')
            fi
            if [ -n "$CAND" ]; then
                echo "Installing: $CAND"
                opkg install "$CAND" || opkg install "$CAND" --force-reinstall || true
            else
                echo "!!! Oscam not found in feeds."
                exit 1
            fi
            sync
            sleep 1
        """
        console_screen_open(self.sess, title, [cmd], close_on_finish=False)

    def install_softcam_script(self):
        title = "Softcam - Instalator" if self.lang == 'PL' else "Softcam - Installer"
        cmd = "opkg update || true; opkg install wget ca-certificates || true; wget -O - -q http://updates.mynonpublic.com/oea/feed | bash || true"
        console_screen_open(self.sess, title, [cmd], close_on_finish=False)

    def install_ncam_feed(self):
        title = "NCam (Feed - najnowszy)" if self.lang == 'PL' else "NCam (Feed - latest)"
        cmd = "opkg update && (opkg install --force-reinstall ncam || opkg install --force-reinstall softcam-ncam || opkg install --force-reinstall enigma2-plugin-softcams-ncam || opkg install --force-reinstall enigma2-plugin-softcams-ncam-emu)"
        console_screen_open(self.sess, title, [cmd], close_on_finish=False)
    def install_iptv_dream_simplified(self): 
        # [FIX] Uruchamianie w konsoli, aby uniknąć zwisu na "wget pipe"
        cmd = "wget -qO- https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh | sh"
        console_screen_open(self.sess, "IPTV Dream Installer", [cmd], close_on_finish=False)

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

        console_screen_open(self.sess, title, cmds, close_on_finish=False)

    
    def open_system_monitor(self): self.sess.open(SystemMonitorScreen, self.lang)
    def open_log_viewer(self): self.sess.open(LogViewerScreen, self.lang)
    def open_cron_manager(self): self.sess.open(CronManagerScreen, self.lang)
    def open_service_manager(self): self.sess.open(ServiceManagerScreen, self.lang)
    def open_system_info(self): self.sess.open(SystemInfoScreen, self.lang)
    
    # === NOWA LOGIKA AKTUALIZACJI ===

    # ... (Metody aktualizacji bez zmian) ...


# === Network Diagnostics: readable summary screen (v6.0) ===
class NetworkDiagnosticsSummaryScreen(Screen):
    skin = """
    <screen position="center,center" size="980,560" title="Network Diagnostics">
        <widget name="text" position="20,20" size="940,490" font="Regular;22" />
        <widget name="hint" position="20,520" size="940,30" font="Regular;20" halign="center" />
    </screen>"""

    def __init__(self, session, lang='PL'):
        Screen.__init__(self, session)
        self.session = session
        self.lang = lang or 'PL'

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

    def _start(self):
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
            'http://api.ipify.org',
            'https://ifconfig.me/ip',
            'http://ifconfig.me/ip',
        ):
            rc, out, _ = self._run_cmd("wget -qO- --no-check-certificate --timeout=10 %s" % url)
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
        try:
            self["text"].setText(text)
        except Exception:
            pass
def main(session, **kwargs):
    session.open(AIOLoadingScreen)


def sessionstart(reason, session=None, **kwargs):
    # reason == 0: start, reason == 1: shutdown
    if reason == 0:
        try:
            _apply_auto_ram_from_config()
        except Exception as e:
            print("[AIO Panel] sessionstart error:", e)
def menu(menuid, **kwargs):
    # Register in:
    # - Main Menu (MENU button): menuid == "mainmenu"
    # - Setup -> System: menuid == "system"
    if menuid in ("system", "mainmenu"):
        # Optional: hide AIO Panel from receiver menu
        try:
            if config is not None and hasattr(config.plugins, "panelaio") and hasattr(config.plugins.panelaio, "show_in_menu"):
                if not config.plugins.panelaio.show_in_menu.value:
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
        PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart),
    ]
