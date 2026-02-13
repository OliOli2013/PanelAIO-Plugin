# -*- coding: utf-8 -*-
"""
Panel AIO
by Paweł Pawełek | msisystem@t.pl
Wersja 7.1 - System Tools Suite (Monitor/Logs/Cron/Services/Info)
FIXED & UPDATED (SuperWizard Tooltips + OpenPLi 9 Fix + IPTV Dream Fix + Syntax Error Fix)
"""
from __future__ import print_function
from __future__ import absolute_import
from enigma import eDVBDB, eTimer
from Screens.Screen import Screen
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop
from Screens.ChoiceBox import ChoiceBox
from Screens.InputBox import InputBox
from Components.ActionMap import ActionMap
from Components.Label import Label
try:
    from Components.config import config, ConfigSubsection, ConfigSelection, configfile
except Exception:
    config = None
    ConfigSubsection = None
    ConfigSelection = None
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

import os
import socket
import datetime
import sys
import subprocess
import shutil
import re
import json
import time
from twisted.internet import reactor
from threading import Thread

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

g_auto_ram_timer.callback.append(run_auto_ram_clean_task)
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
PLUGIN_QR_CODE_PATH = os.path.join(PLUGIN_PATH, "Kod_QR_buycoffee.png")
VER = "7.1"
DATE = str(datetime.date.today())
FOOT = "AIO {} | {} | by Paweł Pawełek | msisystem@t.pl".format(VER, DATE) 

# Legenda dla przycisków kolorowych
LEGEND_PL_COLOR = r"\c00ff0000●\c00ffffff PL \c0000ff00●\c00ffffff EN \c00ffff00●\c00ffffff Restart GUI \c000000ff●\c00ffffff Aktualizuj"
LEGEND_EN_COLOR = r"\c00ff0000●\c00ffffff PL \c0000ff00●\c00ffffff EN \c00ffff00●\c00ffffff Restart GUI \c000000ff●\c00ffffff Update"
LEGEND_INFO = " " 

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
        "sk_confirm_basic": "Rozpocznie się podstawowa konfiguracja systemu.\n\n- Instalacja zależności\n- Instalacja listy kanałów\n- Instalacja Softcam Feed + Oscam\n\nCzy chcesz kontynuować?",
        "sk_confirm_full": "Rozpocznie się pełna konfiguracja systemu.\n\n- Instalacja zależności\n- Instalacja listy kanałów\n- Instalacja Softcam Feed + Oscam\n- Instalacja Piconów (duży plik)\n\nCzy chcesz kontynuować?",
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
        "sk_confirm_basic": "A basic system configuration will now begin.\n\n- Install dependencies\n- Install channel list\n- Install Softcam Feed + Oscam\n\nDo you want to continue?",
        "sk_confirm_full": "A full system configuration will now begin.\n\n- Install dependencies\n- Install channel list\n- Install Softcam Feed + Oscam\n- Install Picons (large file)\n\nDo you want to continue?",
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
    reactor.callLater(0.2, lambda: session.openWithCallback(on_close, MessageBox, message, message_type, timeout=timeout))

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
        reactor.callLater(0.1, lambda: session.open(Console, title=title, cmdlist=cmds_list, closeOnSuccess=close_on_finish).onClose.append(callback) if callback else session.open(Console, title=title, cmdlist=cmds_list, closeOnSuccess=close_on_finish))
    else:
        c_dialog = session.open(Console, title=title, cmdlist=cmds_list, closeOnSuccess=close_on_finish)
        if callback: c_dialog.onClose.append(callback)

def prepare_tmp_dir():
    if not os.path.exists(PLUGIN_TMP_PATH):
        try:
            os.makedirs(PLUGIN_TMP_PATH)
        except OSError as e:
            print("[AIO Panel] Error creating tmp dir:", e)

# === FUNKCJA install_archive (GLOBALNA) ===
def install_archive(session, title, url, callback_on_finish=None):
    if not url.endswith((".zip", ".tar.gz", ".tgz", ".ipk")):
        show_message_compat(session, "Nieobsługiwany format archiwum!", message_type=MessageBox.TYPE_ERROR)
        if callback_on_finish: callback_on_finish()
        return
    archive_type = "zip" if url.endswith(".zip") else ("tar.gz" if url.endswith((".tar.gz", ".tgz")) else "ipk")
    prepare_tmp_dir()
    tmp_archive_path = os.path.join(PLUGIN_TMP_PATH, os.path.basename(url))
    
    download_cmd = "wget -T 30 --no-check-certificate -O \"{}\" \"{}\"".format(tmp_archive_path, url)
    
    if "picon" in title.lower():
        picon_path = "/usr/share/enigma2/picon"
        nested_picon_path = os.path.join(picon_path, "picon")
        full_command = (
            "{download_cmd} && "
            "mkdir -p {picon_path} && "
            "unzip -o -q \"{archive_path}\" -d \"{picon_path}\" && "
            "if [ -d \"{nested_path}\" ]; then mv -f \"{nested_path}\"/* \"{picon_path}/\"; rmdir \"{nested_path}\"; fi && "
            "rm -f \"{archive_path}\" && "
            "echo 'Picony zostały pomyślnie zainstalowane.' && sleep 1"
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
        import sys
        ver = sys.version_info
        return f"{ver.major}.{ver.minor}"
    except:
        return None

def get_e2kodi_package_name():
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
    pkg = get_e2kodi_package_name()
    if not pkg:
        show_message_compat(session, "Nieznana wersja Pythona. E2Kodi nie zostało zainstalowane.", MessageBox.TYPE_ERROR)
        return

    repo_file = "/etc/opkg/opkg-j00zka.conf"
    repo_url = "https://j00zek.github.io/eeRepo" 
    if not os.path.exists(repo_file):
        try:
            with open(repo_file, "w") as f:
                f.write(f"src/gz opkg-j00zka {repo_url}\n")
        except Exception as e:
            show_message_compat(session, f"Błąd zapisu repozytorium: {e}", MessageBox.TYPE_ERROR)
            return

    cmd = f"opkg update && opkg install {pkg}"
    run_command_in_background(session, f"E2Kodi v2 (Python {get_python_version()})", [cmd])

# === MENU PL/EN Z E2Kodi (GLOBALNE) ===
SOFTCAM_AND_PLUGINS_PL = [
    (r"\c00FFD200--- Softcamy ---\c00ffffff", "SEPARATOR"),
    ("🔄 Restart Oscam", "CMD:RESTART_OSCAM"),
    ("🧹 Kasuj hasło Oscam", "CMD:CLEAR_OSCAM_PASS"),
    ("⚙️ oscam.dvbapi - kasowanie zawartości", "CMD:MANAGE_DVBAPI"),
    ("🔄 Aktualizuj oscam.srvid/srvid2", "CMD:UPDATE_SRVID"),
    ("🔑 Aktualizuj SoftCam.Key (Online)", "CMD:INSTALL_SOFTCAMKEY_ONLINE"),
    ("📥 Softcam Feed - Instalator", "CMD:INSTALL_SOFTCAM_FEED"),
    ("📥 Oscam Feed - Instalator (Auto)", "CMD:INSTALL_BEST_OSCAM"),
    ("📥 NCam 15.6 (Instalator)", "bash_raw:wget https://raw.githubusercontent.com/biko-73/Ncam_EMU/main/installer.sh -O - | /bin/sh"),
    (r"\c00FFD200--- Wtyczki Online ---\c00ffffff", "SEPARATOR"),
    ("📺 XStreamity - Instalator", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-xstreamity"),
    ("📺 IPTV Dream - Instalator", "CMD:INSTALL_IPTV_DREAM"),
    ("⚙️ ServiceApp - Instalator", "CMD:INSTALL_SERVICEAPP"),
    ("📦 Konfiguracja IPTV - zależności", "CMD:IPTV_DEPS"),
    ("⚙️ StreamlinkProxy - Instalator", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-streamlinkproxy"),
    ("🛠 AJPanel - Instalator", "bash_raw:wget https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh -O - | /bin/sh"),
    ("▶️ E2iPlayer Master - Instalacja/Aktualizacja", "bash_raw:wget -q 'https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh' -O - | /bin/sh"),
    ("📅 EPG Import - Instalator", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh -O - | /bin/bash"),
    ("🔄 S4aUpdater - Instalator", "bash_raw:wget http://s4aupdater.one.pl/instalujs4aupdater.sh -O - | /bin/sh"),
    ("📺 JediMakerXtream - Instalator", "bash_raw:wget https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh -O - | /bin/sh"),
    ("▶️ YouTube - Instalator", "bash_raw:opkg install https://github.com/Taapat/enigma2-plugin-youtube/releases/download/git1294/enigma2-plugin-extensions-youtube_py3-git1294-cbcf8b0-r0.0.ipk"),
    ("📦 J00zeks Feed (Repo Installer)", "CMD:INSTALL_J00ZEK_REPO"),
    ("📺 E2Kodi v2 - Instalator (j00zek)", "CMD:INSTALL_E2KODI"),
    ("🖼️ Picon Updater - Instalator (Picony)", "bash_raw:wget -qO - https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh | /bin/sh"),
]


SOFTCAM_AND_PLUGINS_EN = [
    (r"\c00FFD200--- Softcams ---\c00ffffff", "SEPARATOR"),
    ("🔄 Restart Oscam", "CMD:RESTART_OSCAM"),
    ("🧹 Clear Oscam Password", "CMD:CLEAR_OSCAM_PASS"),
    ("⚙️ oscam.dvbapi - clear file", "CMD:MANAGE_DVBAPI"),
    ("🔄 Update oscam.srvid/srvid2", "CMD:UPDATE_SRVID"),
    ("🔑 Update SoftCam.Key (Online)", "CMD:INSTALL_SOFTCAMKEY_ONLINE"),
    ("📥 Softcam Feed - Installer", "CMD:INSTALL_SOFTCAM_FEED"),
    ("📥 Oscam Feed - Installer (Auto)", "CMD:INSTALL_BEST_OSCAM"),
    ("📥 NCam 15.6 (Installer)", "bash_raw:wget https://raw.githubusercontent.com/biko-73/Ncam_EMU/main/installer.sh -O - | /bin/sh"),
    (r"\c00FFD200--- Online Plugins ---\c00ffffff", "SEPARATOR"),
    ("📺 XStreamity - Installer", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-xstreamity"),
    ("📺 IPTV Dream - Installer", "CMD:INSTALL_IPTV_DREAM"),
    ("⚙️ ServiceApp - Installer", "CMD:INSTALL_SERVICEAPP"),
    ("📦 IPTV Configuration - dependencies", "CMD:IPTV_DEPS"),
    ("⚙️ StreamlinkProxy - Installer", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-streamlinkproxy"),
    ("🛠 AJPanel - Installer", "bash_raw:wget https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh -O - | /bin/sh"),
    ("▶️ E2iPlayer Master - Install/Update", "bash_raw:wget -q 'https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh' -O - | /bin/sh"),
    ("📅 EPG Import - Installer", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh -O - | /bin/bash"),
    ("🔄 S4aUpdater - Installer", "bash_raw:wget http://s4aupdater.one.pl/instalujs4aupdater.sh -O - | /bin/sh"),
    ("📺 JediMakerXtream - Installer", "bash_raw:wget https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh -O - | /bin/sh"),
    ("▶️ YouTube - Installer", "bash_raw:opkg install https://github.com/Taapat/enigma2-plugin-youtube/releases/download/git1294/enigma2-plugin-extensions-youtube_py3-git1294-cbcf8b0-r0.0.ipk"),
    ("📦 J00zeks Feed (Repo Installer)", "CMD:INSTALL_J00ZEK_REPO"),
    ("📺 E2Kodi v2 - Installer (j00zek)", "CMD:INSTALL_E2KODI"),
    ("🖼️ Picon Updater - Installer (Picons)", "bash_raw:wget -qO - https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh | /bin/sh"),
]


# === NOWE PODZIELONE LISTY MENU (PL) ===
SYSTEM_TOOLS_PL = [
    (r"\c00FFD200--- Konfigurator ---\c00ffffff", "SEPARATOR"),
    ("✨ Super Konfigurator (Pierwsza Instalacja)", "CMD:SUPER_SETUP_WIZARD"),
    (r"\c00FFD200--- Narzędzia Systemowe ---\c00ffffff", "SEPARATOR"),
    ("🗑️ Menadżer Deinstalacji", "CMD:UNINSTALL_MANAGER"),
    ("📡 Aktualizuj satellites.xml", "CMD:UPDATE_SATELLITES_XML"),
    ("🖼️ Pobierz Picony (Transparent)", "archive:https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip"),
    ("📊 Monitor Systemowy", "CMD:SYSTEM_MONITOR"),
    ("📄 Przeglądarka Logów", "CMD:LOG_VIEWER"),
    ("⏰ Menedżer Cron", "CMD:CRON_MANAGER"),
    ("🔌 Menedżer Usług", "CMD:SERVICE_MANAGER"),
    ("ℹ️ Informacje o Systemie", "CMD:SYSTEM_INFO"),
    (r"\c00FFD200--- Backup & Restore ---\c00ffffff", "SEPARATOR"),
    ("💾 Backup Listy Kanałów", "CMD:BACKUP_LIST"),
    ("💾 Backup Konfiguracji Oscam", "CMD:BACKUP_OSCAM"),
    ("♻️ Restore Listy Kanałów", "CMD:RESTORE_LIST"),
    ("♻️ Restore Konfiguracji Oscam", "CMD:RESTORE_OSCAM"),
]


SYSTEM_TOOLS_EN = [
    (r"\c00FFD200--- Configurator ---\c00ffffff", "SEPARATOR"),
    ("✨ Super Setup Wizard (First Installation)", "CMD:SUPER_SETUP_WIZARD"),
    (r"\c00FFD200--- System Tools ---\c00ffffff", "SEPARATOR"),
    ("🗑️ Uninstallation Manager", "CMD:UNINSTALL_MANAGER"),
    ("📡 Update satellites.xml", "CMD:UPDATE_SATELLITES_XML"),
    ("🖼️ Download Picons (Transparent)", "archive:https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip"),
    ("📊 System Monitor", "CMD:SYSTEM_MONITOR"),
    ("📄 Log Viewer", "CMD:LOG_VIEWER"),
    ("⏰ Cron Manager", "CMD:CRON_MANAGER"),
    ("🔌 Service Manager", "CMD:SERVICE_MANAGER"),
    ("ℹ️ System Information", "CMD:SYSTEM_INFO"),
    (r"\c00FFD200--- Backup & Restore ---\c00ffffff", "SEPARATOR"),
    ("💾 Backup Channel List", "CMD:BACKUP_LIST"),
    ("💾 Backup Oscam Config", "CMD:BACKUP_OSCAM"),
    ("♻️ Restore Channel List", "CMD:RESTORE_LIST"),
    ("♻️ Restore Oscam Config", "CMD:RESTORE_OSCAM"),
]


DIAGNOSTICS_PL = [
    (r"\c00FFD200--- Informacje i Aktualizacje ---\c00ffffff", "SEPARATOR"),
    ("ℹ️ Informacje o AIO Panel", "CMD:SHOW_AIO_INFO"),
    ("🔄 Aktualizacja Wtyczki", "CMD:CHECK_FOR_UPDATES"),
    (r"\c00FFD200--- Diagnostyka ---\c00ffffff", "SEPARATOR"),
    ("🌐 Diagnostyka Sieci", "CMD:NETWORK_DIAGNOSTICS"),
    ("💾 Wolne miejsce (dysk/flash)", "CMD:FREE_SPACE_DISPLAY"),
    (r"\c00FFD200--- Czyszczenie i Bezpieczeństwo ---\c00ffffff", "SEPARATOR"),
    ("⏱️ Auto RAM Cleaner (Konfiguruj)", "CMD:SETUP_AUTO_RAM"),
    ("🧹 Wyczyść Pamięć Tymczasową", "CMD:CLEAR_TMP_CACHE"),
    ("🧹 Wyczyść Pamięć RAM", "CMD:CLEAR_RAM_CACHE"),
    ("🔑 Kasuj hasło FTP", "CMD:CLEAR_FTP_PASS"),
    ("🔑 Ustaw Hasło FTP", "CMD:SET_SYSTEM_PASSWORD"),
]


DIAGNOSTICS_EN = [
    (r"\c00FFD200--- Info & Updates ---\c00ffffff", "SEPARATOR"),
    ("ℹ️ About AIO Panel", "CMD:SHOW_AIO_INFO"),
    ("🔄 Update Plugin", "CMD:CHECK_FOR_UPDATES"),
    (r"\c00FFD200--- Diagnostics ---\c00ffffff", "SEPARATOR"),
    ("🌐 Network Diagnostics", "CMD:NETWORK_DIAGNOSTICS"),
    ("💾 Free Space (disk/flash)", "CMD:FREE_SPACE_DISPLAY"),
    (r"\c00FFD200--- Cleaning & Security ---\c00ffffff", "SEPARATOR"),
    ("⏱️ Auto RAM Cleaner (Setup)", "CMD:SETUP_AUTO_RAM"),
    ("🧹 Clear Temporary Cache", "CMD:CLEAR_TMP_CACHE"),
    ("🧹 Clear RAM Cache", "CMD:CLEAR_RAM_CACHE"),
    ("🔑 Clear FTP Password", "CMD:CLEAR_FTP_PASS"),
    ("🔑 Set FTP Password", "CMD:SET_SYSTEM_PASSWORD"),
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
        with open(tmp_json_path, 'r', encoding='utf-8') as f:
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
        with open(tmp_list_file, 'r', encoding='utf-8', errors='ignore') as f:
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
            line = stdout.decode('utf-8').strip()
            parts = line.split(' - ')
            if len(parts) > 1:
                return parts[1].strip()
        return "Auto"
    except Exception:
        return "Error"

# === KLASA WizardProgressScreen (GLOBALNA) ===
class WizardProgressScreen(Screen):
    skin = """
    <screen position="center,center" size="800,400" title="Super Konfigurator">
        <widget name="message" position="40,40" size="720,320" font="Regular;28" halign="center" valign="center" />
    </screen>"""

    def __init__(self, session, steps, **kwargs):
        Screen.__init__(self, session)
        self.session = session
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

    def _wizard_step_install_oscam(self):
        title = self._get_wizard_title("Instalacja Softcam Feed + Oscam")
        self["message"].setText("Krok [{}/{}]:\nInstalacja Softcam Feed + Oscam...\nProszę czekać.".format(self.wizard_current_step, self.wizard_total_steps))
        
        cmd = """
            echo "Instalowanie/Aktualizowanie Softcam Feed..."
            wget -O - -q http://updates.mynonpublic.com/oea/feed | bash
            echo "Aktualizuję listę pakietów..."
            opkg update
            echo "Wyszukuję najlepszą wersję Oscam w feedach..."
            PKG_NAME=$(opkg list | grep 'oscam' | grep 'ipv4only' | grep -E -m 1 'master|emu|stable' | cut -d ' ' -f 1)
            if [ -n "$PKG_NAME" ]; then
                echo "Znaleziono pakiet: $PKG_NAME. Rozpoczynam instalację..."
                opkg install $PKG_NAME
            else
                echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                echo "Nie znaleziono odpowiedniego pakietu Oscam w feedach."
                echo "Pomięto instalację Oscam. Możesz ją wykonać ręcznie z menu."
                echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            fi
            echo "Instalacja Oscam zakończona."
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
            self.session.open(TryQuitMainloop, 2)
            
            # [FIX] Zabezpieczenie na wypadek zawieszenia się GUI po instalacji FULL (np. picony)
            # Jeśli TryQuitMainloop nie zadziała w ciągu 3 sekund, wymuś reboot z poziomu systemu.
            def force_reboot_if_hung():
                print("[AIO Panel] Wymuszanie restartu (fallback)...")
                os.system("reboot || killall -9 enigma2")
            
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
        try:
            which = shutil.which
        except Exception:
            which = None

        def _has_cmd(cmd):
            try:
                if which is not None:
                    return which(cmd) is not None
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


# *** NOWA KLASA EKRANU INFO (z notą prawną) ***
class AIOInfoScreen(Screen):
    skin = """
    <screen position="center,center" size="900,540" title="Informacje o AIO Panel">
        <widget name="title" position="20,20" size="860,35" font="Regular;28" halign="center" valign="center" />
        <widget name="author" position="20,60" size="860,25" font="Regular;22" halign="center" valign="center" />
        <widget name="facebook" position="20,85" size="860,25" font="Regular;22" halign="center" valign="center" />
        
        <widget name="legal_title" position="20,125" size="860,30" font="Regular;24" halign="center" foregroundColor="yellow" />
        
        <widget name="legal_text" position="20,165" size="860,200" font="Regular;20" halign="center" valign="top" />
        
        <widget name="changelog_title" position="20,375" size="860,30" font="Regular;26" halign="center" foregroundColor="cyan" />
        <widget name="changelog_text" position="30,415" size="840,105" font="Regular;22" halign="left" valign="top" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.setTitle("Informacje o AIO Panel")

        self["title"] = Label("AIO Panel v{}".format(VER))
        self["author"] = Label("Twórca: Paweł Pawełek | msisystem@t.pl")
        self["facebook"] = Label("Facebook: Enigma 2 Oprogramowanie, dodatki")
        self["legal_title"] = Label("--- Nota Prawna i Licencyjna ---")
        
        legal_note_text = "Nota Licencyjna i Prawa Autorskie\n\n" \
                          "Prawa autorskie (C) 2024, Paweł Pawełek (msisystem@t.pl)\n" \
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
                          "Jest to dobrowolne, ale bardzo motywuje do dalszej pracy. Dziękuję!"
        
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
                with open(tmp_changelog_path, 'r', encoding='utf-8') as f:
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
        except Exception as e:
            print("[AIO Panel] Info screen changelog fetch error:", e)
            changelog_text = "Błąd podczas pobierania listy zmian."
        
        reactor.callFromThread(self.update_changelog_label, changelog_text, found_version_tag)

    def update_changelog_label(self, text, version_tag):
        self["changelog_text"].setText(text)
        if version_tag:
            self["changelog_title"].setText("Zmiany dla {}".format(version_tag))
        else:
            self["changelog_title"].setText("Ostatnie zmiany (z GitHub)")
# *** KONIEC KLASY EKRANU INFO ***


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
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
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
            du = shutil.disk_usage(path)
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
            return out.decode("utf-8", "ignore")
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
        os.makedirs("/etc/crontabs", exist_ok=True)
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
            return out.decode("utf-8","ignore").strip() == "active"
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
            ips = out.decode("utf-8","ignore").strip()
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
            lines.append(subprocess.check_output("df -h | head -n 20", shell=True).decode("utf-8","ignore"))
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
        "📥 Softcam Feed - Instalator": "Instaluje Softcam Feed w obrazie (repozytorium pakietów).\nPo instalacji możesz pobierać softcamy z: Pobierz wtyczki → Pakiety softcam.",
        "📥 Oscam Feed - Instalator (Auto)": "Automatycznie dobiera i instaluje Oscam z feedu (gdy dostępny).\nPo instalacji zalecany restart GUI.",
        "📥 NCam 15.6 (Instalator)": "Instaluje NCam 15.6 z feedu/instalatora.\nPo instalacji zalecany restart GUI i wybór emu w ustawieniach Softcam.",
        "⚙️ ServiceApp - Instalator": "Instaluje ServiceApp (alternatywny odtwarzacz) dla lepszej obsługi streamów IPTV.\nMoże wymagać restartu Enigma2 po instalacji.",
        "🛠 AJPanel - Instalator": "Instaluje AJPanel – zestaw narzędzi serwisowych i administracyjnych.\nPrzydatne do szybkiej diagnostyki i obsługi systemu.",
        "▶️ E2iPlayer Master - Instalacja/Aktualizacja": "Instaluje lub aktualizuje E2iPlayer (Master).\nDostarcza dostęp do wielu serwisów VOD/stream i narzędzi multimedialnych.",
        "📅 EPG Import - Instalator": "Instaluje EPGImport – automatyczny import programu TV.\nPo instalacji skonfiguruj źródła EPG i harmonogram aktualizacji.",
        "🔄 S4aUpdater - Instalator": "Instaluje S4aUpdater do aktualizacji wybranych dodatków.\nUłatwia utrzymanie wtyczek w aktualnej wersji bez ręcznej instalacji.",
        "📺 JediMakerXtream - Instalator": "Instaluje JediMakerXtream do budowy bukietów IPTV z kont Xtream.\nPo instalacji dodaj dane logowania i wygeneruj listę/bukiety.",
        "▶️ YouTube - Instalator": "Instaluje wtyczkę YouTube dla Enigma2.\nMoże wymagać dodatkowych bibliotek zależnych od obrazu.",
        "📦 J00zeks Feed (Repo Installer)": "Dodaje repozytorium J00zeks (feed) do systemu.\nPo instalacji możesz pobierać jego wtyczki z poziomu Menedżera wtyczek.",
        "📺 E2Kodi v2 - Instalator (j00zek)": "Instaluje E2Kodi v2 (wersja z feedu j00zek).\nUmożliwia uruchomienie środowiska Kodi na Enigma2 (zależności zależą od obrazu).",
        "🖼️ Picon Updater - Instalator (Picony)": "Instaluje narzędzie do aktualizacji piconów.\nUłatwia pobieranie i odświeżanie ikon kanałów w systemie.",

        # Narzędzia Systemowe
        "⚙️ Narzędzia Systemowe": "Zaawansowane narzędzia administracyjne systemu",
        "✨ Super Konfigurator (Pierwsza Instalacja)": "Asystent pierwszej konfiguracji tunera",
        ">>> Super Konfigurator (Pierwsza Instalacja)": "Automatyczna pierwsza konfiguracja tunera.\n\nWykonuje kolejno:\n- instalację listy kanałów (Paweł Pawełek)\n- instalację softcamu\n- instalację najnowszego Oscam z feedu (dobór pod tuner/CPU)\n- pobranie piconów (Transparent)\nNa końcu uruchamia pełny restart systemu tunera.",
        "🗑️ Menadżer Deinstalacji": "Odinstalowywanie pakietów z systemu",
        "📡 Aktualizuj satellites.xml": "Pobiera i aktualizuje satellites.xml w systemie.\nPrzydatne przy dodawaniu nowych transponderów; zalecany restart Enigmy2.",
        "🖼️ Pobierz Picony (Transparent)": "Pobiera zestaw piconów (transparent) i zapisuje w docelowym katalogu.\nMoże nadpisać istniejące pliki; po zakończeniu zalecany restart GUI.",
        "📊 Monitor Systemowy": "Podgląd wykorzystania CPU, RAM, temperatury",
        "📄 Przeglądarka Logów": "Przeglądanie logów systemowych i Enigmy2",
        "⏰ Menedżer Cron": "Zarządzanie zadaniami harmonogramu",
        "🔌 Menedżer Usług": "Zarządzanie usługami systemowymi (SSH, FTP itd.)",
        "ℹ️ Informacje o Systemie": "Szczegółowe informacje o sprzęcie i oprogramowaniu",
        "🔄 Aktualizuj oscam.srvid/srvid2": "Aktualizacja listy identyfikatorów kanałów",
        "🔑 Aktualizuj SoftCam.Key (Online)": "Pobiera i aktualizuje plik SoftCam.Key (Online) w typowych lokalizacjach kluczy.\nPo zakończeniu wykonuje restart emulatora (jeśli uruchomiony).",
        "💾 Backup Listy Kanałów": "Kopia zapasowa list kanałów",
        "💾 Backup Konfiguracji Oscam": "Kopia zapasowa konfiguracji Oscam",
        "♻️ Restore Listy Kanałów": "Przywracanie list kanałów z backupu",
        "♻️ Restore Konfiguracji Oscam": "Przywracanie konfiguracji Oscam z backupu",

        # Info i Diagnostyka
        "ℹ️ Info i Diagnostyka": "Informacje o wtyczce i narzędzia diagnostyczne",
        "ℹ️ Informacje o AIO Panel": "Informacje o wersji, licencji i autorze",
        "🔄 Aktualizacja Wtyczki": "Sprawdzenie i instalacja aktualizacji AIO Panel",
        "🌐 Diagnostyka Sieci": "Test prędkości i parametrów połączenia internetowego",
        "💾 Wolne miejsce (dysk/flash)": "Informacja o wykorzystaniu pamięci",
        "⏱️ Auto RAM Cleaner (Konfiguruj)": "Automatyczne czyszczenie pamięci RAM",
        "🧹 Wyczyść Pamięć Tymczasową": "Usunięcie plików tymczasowych z /tmp",
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
        "📥 Softcam Feed - Installer": "Installs Softcam Feed repository on your image.\nAfter install: Download plugins → Softcam packages to pick your emulator.",
        "📥 Oscam Feed - Installer (Auto)": "Automatically selects and installs Oscam from feed (when available).\nGUI restart is recommended after installation.",
        "📥 NCam 15.6 (Installer)": "Installs NCam 15.6 via feed/installer.\nGUI restart recommended; then select the emulator in Softcam settings.",
        "⚙️ ServiceApp - Installer": "Installs ServiceApp (alternative playback engine) for improved IPTV/stream handling.\nMay require Enigma2 restart after installation.",
        "🛠 AJPanel - Installer": "Installs AJPanel – a set of service/administration tools.\nUseful for quick maintenance and diagnostics.",
        "▶️ E2iPlayer Master - Install/Update": "Installs or updates E2iPlayer (Master).\nProvides access to multiple streaming/VOD sources and media tools.",
        "📅 EPG Import - Installer": "Installs EPGImport for automatic EPG data import.\nAfter install, set sources and schedule periodic updates.",
        "🔄 S4aUpdater - Installer": "Installs S4aUpdater to keep selected add-ons up to date.\nReduces manual package installs/updates.",
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
        "🖼️ Download Picons (Transparent)": "Downloads a transparent picon set and writes it to the target folder.\nMay overwrite existing files; GUI restart recommended.",
        "📊 System Monitor": "View CPU, RAM, temperature usage",
        "📄 Log Viewer": "Browse system and Enigma2 logs",
        "⏰ Cron Manager": "Manage scheduled tasks",
        "🔌 Service Manager": "Manage system services (SSH, FTP, etc.)",
        "ℹ️ System Information": "Detailed hardware and software info",
        "🔄 Update oscam.srvid/srvid2": "Update channel identifier list",
        "🔑 Update SoftCam.Key (Online)": "Downloads and updates SoftCam.Key (Online) to common key/config locations.\nRestarts the emulator (if running).",
        "💾 Backup Channel List": "Backup channel lists",
        "💾 Backup Oscam Config": "Backup Oscam configuration",
        "♻️ Restore Channel List": "Restore channel lists from backup",
        "♻️ Restore Oscam Config": "Restore Oscam config from backup",

        # Info & Diagnostics
        "ℹ️ Info & Diagnostics": "Plugin info and diagnostic tools",
        "ℹ️ About AIO Panel": "Version, license and author info",
        "🔄 Update Plugin": "Check and install AIO Panel updates",
        "🌐 Network Diagnostics": "Internet speed and connection test",
        "💾 Free Space (disk/flash)": "Memory usage information",
        "⏱️ Auto RAM Cleaner (Setup)": "Automatic RAM cleaning",
        "🧹 Clear Temporary Cache": "Remove temporary files from /tmp",
        "🧹 Clear RAM Cache": "Manual RAM cache clearing",
        "🔑 Clear FTP Password": "Removes the root password (FTP/SSH).\nAfterwards, login may be passwordless (depends on image security settings).",
        "🔑 Set FTP Password": "Sets a new password for the root user (FTP/SSH).\nImproves security for network access to the receiver.",
    }
}
# === KONIEC OPISÓW FUNKCJI ===

# === NOWA KLASA WYBORU Z OPISEM (DLA WIZARDA) ===
class SuperWizardChoiceScreen(Screen):
    skin = """
    <screen position="center,center" size="800,500" title="Super Konfigurator">
        <widget name="list" position="20,20" size="760,300" scrollbarMode="showOnDemand" />
        <widget name="description" position="20,340" size="760,100" font="Regular;22" halign="center" valign="center" foregroundColor="yellow" />
        <widget name="actions" position="20,460" size="760,30" font="Regular;20" halign="right" />
    </screen>"""

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
    # Nowy skin z jedną listą i informacją o zakładkach
    skin = """
    <screen name='PanelAIO' position='center,center' size='1100,690' title='Panel AIO'>
        <widget name='qr_code_small' position='15,15' size='90,90' pixmap="{}" alphatest='blend' />
        <widget name="support_label" position="125,15" size="400,90" font="Regular;24" halign="left" valign="center" foregroundColor="green" />
        <widget name="title_label" position="500,15" size="585,40" font="Regular;32" halign="right" valign="center" transparent="1" />

        <widget name='tabs_display' position='15,115' size='1070,30' font='Regular;26' halign='center' />

        <widget name='menu' position='15,165' size='1070,380' itemHeight='40' font='Regular;22' scrollbarMode='showOnDemand' selectionPixmap='selection.png'/>

        <widget name='function_description' position='15,550' size='1070,78' font='Regular;22' halign='left' valign='top' foregroundColor='#00FFD200' backgroundColor='#00101010' transparent='0' />

        <widget name='legend' position='15,630'  size='1070,26'  font='Regular;20' halign='center'/>
        <widget name='footer' position='center,658' size='1070,24' font='Regular;16' halign='center' valign='center' foregroundColor='lightgrey'/>
    </screen>""".format(PLUGIN_QR_CODE_PATH)

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
        
        self.active_tab = 0 
        self.tab_titles_def = COL_TITLES 
        self.all_data = ([], [], [], []) 

        self["qr_code_small"] = Pixmap()
        self["support_label"] = Label(TRANSLATIONS[self.lang]["support_text"])
        self["title_label"] = Label("AIO Panel " + VER)
        self["tabs_display"] = Label("") 
        self["menu"] = MenuList([])
        self["function_description"] = Label("") # Tooltip z opisem funkcji
        self["legend"] = Label(" ") 
        self["footer"] = Label(FOOT)
        self["act"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.run_with_confirmation,
            "cancel": self.close,
            "red": lambda: self.set_language('PL'),
            "green": lambda: self.set_language('EN'),
            "yellow": self.restart_gui,
            "blue": self.check_for_updates_manual,
            "left": self.prev_tab,
            "right": self.next_tab,
            "up": self.menu_up,
            "down": self.menu_down
        }, -1)
        
        self.onShown.append(self.post_initial_setup)
        self.set_language(self.lang) 

    # --- FUNKCJE ZAKŁADEK ---
    def next_tab(self):
        new_tab_index = (self.active_tab + 1) % len(self.all_data)
        self.switch_tab(new_tab_index)

    def prev_tab(self):
        new_tab_index = (self.active_tab - 1) % len(self.all_data)
        self.switch_tab(new_tab_index)

    def switch_tab(self, tab_index):
        self.active_tab = tab_index
        lang = self.lang

        all_titles = self.tab_titles_def[lang]

        active_color = r"\c00ffff00" # Żółty
        inactive_color = r"\c00999999" # Szary
        reset_color = r"\c00ffffff" # Biały

        tabs_display_text_list = []
        for i, title in enumerate(all_titles):
            if i == self.active_tab:
                tabs_display_text_list.append("{color}► {title} ◄{reset}".format(color=active_color, title=title, reset=reset_color))
            else:
                tabs_display_text_list.append("{color}{title}{reset}".format(color=inactive_color, title=title, reset=reset_color))

        self["tabs_display"].setText(" | ".join(tabs_display_text_list))

        data_list = self.all_data[self.active_tab]
        if data_list:
            menu_items = [str(item[0]) for item in data_list]
            self["menu"].setList(menu_items)
            # Wyświetl opis pierwszego elementu
            self.update_function_description()
        else:
            self["menu"].setList([(TRANSLATIONS[lang]["loading_error_text"],)])
            self["function_description"].setText("")
    def update_function_description(self):
        """Aktualizuje opis funkcji na podstawie zaznaczonego elementu"""
        try:
            data_list = self.all_data[self.active_tab]
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
                clean_name = func_name.lstrip('📺📡🔑⚙️ℹ️🔄🧹💾♻️🗑️📊📄⏰🔌✨🌐⏱️🖼️🛠▶️📅🔄📦')
                description = descriptions.get(clean_name.strip(), "")

            self["function_description"].setText(description)

        except Exception as e:
            # W przypadku błędu po prostu wyczyść opis
            self["function_description"].setText("")

    def menu_up(self):
        """Przejście w górę w menu z aktualizacją opisu"""
        self["menu"].up()
        self.update_function_description()

    def menu_down(self):
        """Przejście w dół w menu z aktualizacją opisu"""
        self["menu"].down()
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
            
            softcam_menu = list(SOFTCAM_AND_PLUGINS_PL if lang == 'PL' else SOFTCAM_AND_PLUGINS_EN)
            tools_menu = list(SYSTEM_TOOLS_PL if lang == 'PL' else SYSTEM_TOOLS_EN)
            diag_menu = list(DIAGNOSTICS_PL if lang == 'PL' else DIAGNOSTICS_EN)
            
            # Filtrowanie dla Hyperion/VTi
            if self.image_type in ["hyperion", "vti"]:
                emu_actions_to_block = ["CMD:RESTART_OSCAM", "CMD:CLEAR_OSCAM_PASS", "CMD:MANAGE_DVBAPI", "CMD:INSTALL_SOFTCAM_FEED", "CMD:INSTALL_BEST_OSCAM"]
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

            self.all_data = (final_channel_lists, softcam_menu, tools_menu, diag_menu)
            self.switch_tab(self.active_tab) 
            
        except Exception as e:
            print("[AIO Panel] Błąd danych:", e)
            self.all_data = ([(TRANSLATIONS[self.lang]["loading_error_text"], "SEPARATOR")], [], [], [])
            self.switch_tab(0)
            self.update_function_description()

    def set_lang_headers_and_legends(self):
        self["legend"].setText(LEGEND_PL_COLOR if self.lang == 'PL' else LEGEND_EN_COLOR)
        self["support_label"].setText(TRANSLATIONS[self.lang]["support_text"])

    def run_with_confirmation(self):
        try:
            name, action = self.all_data[self.active_tab][self["menu"].getSelectedIndex()]
        except (IndexError, KeyError, TypeError): return 
        if action == "SEPARATOR": return 

        actions_no_confirm = [
            "CMD:SHOW_AIO_INFO", "CMD:NETWORK_DIAGNOSTICS", "CMD:FREE_SPACE_DISPLAY", 
            "CMD:UNINSTALL_MANAGER", "CMD:MANAGE_DVBAPI", "CMD:CHECK_FOR_UPDATES", 
            "CMD:SUPER_SETUP_WIZARD", "CMD:UPDATE_SATELLITES_XML", "CMD:INSTALL_SERVICEAPP", "CMD:IPTV_DEPS", 
            "CMD:INSTALL_E2KODI", "CMD:INSTALL_J00ZEK_REPO", "CMD:CLEAR_TMP_CACHE", "CMD:CLEAR_RAM_CACHE",
            "CMD:INSTALL_SOFTCAM_FEED", "CMD:INSTALL_IPTV_DREAM", "CMD:SETUP_AUTO_RAM"
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
        pass

    def check_for_updates_manual(self):
        show_message_compat(self.sess, TRANSLATIONS[self.lang]["already_latest"].format(ver=VER))

    # --- GŁÓWNY WYKONAWCA AKCJI ---
    def execute_action(self, name, action):
        title = name
        if action.startswith("archive:"):
            install_archive(self.sess, title, action.split(':', 1)[1], callback_on_finish=self.reload_settings_python)
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
            elif key == "INSTALL_SOFTCAM_FEED": self.install_softcam_feed_only()
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
            "install_basic_no_picons": "Konfiguracja standardowa:\n- Lista kanałów\n- Oscam (Softcam Feed)\n- Restart GUI\nSzybka instalacja.",
            "install_with_picons": "Konfiguracja pełna:\n- To co wyżej + PICONY (Transparent)\nUWAGA: Trwa dłużej i wymaga restartu systemu.",
            "cancel": "Powrót do menu."
        }
        if lang != "PL":
            desc_map = {
                "deps_only": "Install only basic system packages (wget, tar, unzip).\nDoes not change channel lists or softcam.",
                "install_basic_no_picons": "Standard configuration:\n- Channel list\n- Oscam (Softcam Feed)\n- GUI Restart\nFast installation.",
                "install_with_picons": "Full configuration:\n- Same as above + PICONS (Transparent)\nNOTE: Takes longer and requires full system reboot.",
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
            steps = ["channel_list", "install_oscam", "reload_settings"]
        elif key == "install_with_picons":
            steps = ["channel_list", "install_oscam", "picons", "reload_settings"]

        if steps:
            picon_url = 'https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip' 
            channel_list_url = 'https://raw.githubusercontent.com/OliOli2013/PanelAIO-Lists/main/archives/Pawel_Pawelek_HB_13E_04.01.2026.zip'
            list_name = 'Paweł Pawełek HB 13E (04.01.2026)'

            try:
                repo_lists = self.fetched_data_cache.get("repo_lists", [])
                for item in repo_lists:
                    if isinstance(item, (list, tuple)) and len(item) >= 2 and str(item[1]).startswith("archive:"):
                        t = str(item[0]).lower()
                        if "pawel" in t and "13e" in t and "dual" not in t:
                            channel_list_url = str(item[1]).split(':', 1)[1]
                            list_name = str(item[0]).replace("📡 ", "")
                            break
            except Exception:
                pass
            
            self.sess.open(WizardProgressScreen, steps=steps, channel_list_url=channel_list_url, channel_list_name=list_name, picon_url=picon_url)

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
            with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
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

        # Stabilne źródła (repo) + bezpieczny fallback:
        # - OpenPLi (repo): gotowy oscam.srvid (często używany w paczkach softcam)
        # - Fallback: generator KingOfSat (jak dotychczas), ale z walidacją treści
        srvid_urls = [
            "https://raw.githubusercontent.com/openmb/open-pli-core/master/meta-openpli/recipes-openpli/enigma2-softcams/enigma2-plugin-softcams-oscam/oscam.srvid",
            "https://raw.githubusercontent.com/bmihovski/Oscam-Services-Bulcrypt/master/oscam.srvid",
        ]
        # Opcjonalna próba pobrania oscam.srvid2 z repo (jeśli istnieje); gdy brak – generujemy lokalnie z srvid
        srvid2_urls = [
            "https://raw.githubusercontent.com/openmb/open-pli-core/master/meta-openpli/recipes-openpli/enigma2-softcams/enigma2-plugin-softcams-oscam/oscam.srvid2",
        ]

        cmd = r"""            set -e

            BASE="{dst}"

            # Katalogi docelowe: wszystkie miejsca, gdzie istnieje oscam.conf (tak jak: find /etc/tuxbox/config -name oscam.conf -exec dirname {{}} \;)
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
        # Aktualne, często aktualizowane repozytorium kluczy (grudzień 2025)
        url = "https://raw.githubusercontent.com/MOHAMED19OS/SoftCam_Emu/main/SoftCam.Key"
        # Alternatywne źródło (backup)
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

    def set_system_password(self): self.sess.openWithCallback(lambda p: run_command_in_background(self.sess, "Hasło", [f"(echo {p}; echo {p}) | passwd"]) if p else None, InputBox, title="Nowe hasło root")
    def restart_oscam(self, *args): run_command_in_background(self.sess, "Restart Oscam", ["killall -9 oscam; /etc/init.d/softcam restart"])
    def show_uninstall_manager(self):
        self.sess.open(UninstallManagerScreen, self.lang)
    def install_best_oscam(self): run_command_in_background(self.sess, "Instalacja Oscam", ["wget -O - -q http://updates.mynonpublic.com/oea/feed | bash && opkg update && opkg install enigma2-plugin-softcams-oscam-emu"])
    def install_softcam_feed_only(self): run_command_in_background(self.sess, "Feed", ["wget -O - -q http://updates.mynonpublic.com/oea/feed | bash"])
    def install_iptv_dream_simplified(self): 
        # [FIX] Uruchamianie w konsoli, aby uniknąć zwisu na "wget pipe"
        cmd = "wget -qO- https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh | sh"
        console_screen_open(self.sess, "IPTV Dream Installer", [cmd], close_on_finish=False)

    def install_iptv_deps(self):
        title = "Konfiguracja IPTV - zależności" if self.lang == 'PL' else "IPTV Configuration - dependencies"
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
        console_screen_open(self.sess, title, cmds, close_on_finish=False)

    
    def open_system_monitor(self): self.sess.open(SystemMonitorScreen, self.lang)
    def open_log_viewer(self): self.sess.open(LogViewerScreen, self.lang)
    def open_cron_manager(self): self.sess.open(CronManagerScreen, self.lang)
    def open_service_manager(self): self.sess.open(ServiceManagerScreen, self.lang)
    def open_system_info(self): self.sess.open(SystemInfoScreen, self.lang)
    
    # === NOWA LOGIKA AKTUALIZACJI ===

    def check_for_updates_manual(self):
        self.session.openWithCallback(self._manual_update_callback, MessageBox, "Sprawdzanie dostępności aktualizacji...", type=MessageBox.TYPE_INFO, timeout=3)
        # Callback uruchomi się po zamknięciu komunikatu, ale lepiej uruchomić sprawdzanie w tle
        self._check_update(silent=False)

    def _manual_update_callback(self, result):
        pass

    def check_for_updates_on_start(self):
        # Uruchamiamy w wątku, aby nie blokować GUI przy starcie
        Thread(target=self.perform_update_check_silent).start()

    def perform_update_check_silent(self):
        # Wersja cicha - uruchamiana w tle
        self._check_update(silent=True)

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

    def post_initial_setup(self):
        # Opóźnienie startowe sprawdzenia aktualizacji
        reactor.callLater(5, self.check_for_updates_on_start)



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
            return p.returncode, out.decode('utf-8', 'ignore').strip(), err.decode('utf-8', 'ignore').strip()
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
        try:
            from urllib.request import urlopen
        except Exception:
            return None

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
        except Exception:
            return None

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
