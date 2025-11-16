# -*- coding: utf-8 -*-
"""
Panel AIO
by Paweł Pawełek | msisystem@t.pl
Wersja 4.2 - Aktualizacja J00zek repo i poprawki instalatora Ncam
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

# === GLOBALNE ===
PLUGIN_PATH = os.path.dirname(os.path.realpath(__file__))
PLUGIN_TMP_PATH = "/tmp/PanelAIO/"
PLUGIN_ICON_PATH = os.path.join(PLUGIN_PATH, "logo.png")
PLUGIN_SELECTION_PATH = os.path.join(PLUGIN_PATH, "selection.png")
PLUGIN_QR_CODE_PATH = os.path.join(PLUGIN_PATH, "Kod_QR_buycoffee.png")
VER = "4.2"  # <-- Wersja 4.2
DATE = str(datetime.date.today())
FOOT = "AIO {} | {} | by Paweł Pawełek | msisystem@t.pl".format(VER, DATE) 

# Legenda dla przycisków kolorowych
LEGEND_PL_COLOR = r"\c00ff0000●\c00ffffff PL \c0000ff00●\c00ffffff EN \c00ffff00●\c00ffffff Restart GUI \c000000ff●\c00ffffff Aktualizuj"
LEGEND_EN_COLOR = r"\c00ff0000●\c00ffffff PL \c0000ff00●\c00ffffff EN \c00ffff00●\c00ffffff Restart GUI \c000000ff●\c00ffffff Update"
LEGEND_INFO = r" " 

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
        "sk_wizard_title": "Super Konfigurator (Pierwsza Instalacja)",
        "sk_choice_title": "Super Konfigurator - Wybierz opcję",
        "sk_option_deps": "1) Zainstaluj only zależności (wget, tar, unzip)",
        "sk_option_basic_no_picons": "2) Podstawowa Konfiguracja (bez Picon)",
        "sk_option_full_picons": "3) Pełna Konfiguracja (z Piconami)",
        "sk_option_cancel": "Anuluj",
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
        "sk_wizard_title": "Super Setup Wizard (First Installation)",
        "sk_choice_title": "Super Setup Wizard - Select an option",
        "sk_option_deps": "1) Install dependencies only (wget, tar, unzip)",
        "sk_option_basic_no_picons": "2) Basic Configuration (without Picons)",
        "sk_option_full_picons": "3) Full Configuration (with Picons)",
        "sk_option_cancel": "Cancel",
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

# --- NOWA FUNKCJA URUCHAMIANIA W TLE (v4.1) ---
def run_command_in_background(session, title, cmd_list, callback_on_finish=None):
    """
    Otwiera okno "Proszę czekać..." i uruchamia polecenia shella w osobnym wątku,
    ukrywając wyjście konsoli.
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
                # Kontynuuj nawet jeśli jest błąd, tak jak w Console
                
        except Exception as e:
            print("[AIO Panel] Wyjątek w wątku [{}]: {}".format(title, e))
        finally:
            # Wywołaj zamknięcie okna i callback w głównym wątku
            reactor.callFromThread(on_finish_thread)

    def on_finish_thread():
        wait_message.close()
        if callback_on_finish:
            try:
                callback_on_finish()
            except Exception as e:
                print("[AIO Panel] Błąd w callback po run_command_in_background:", e)

    # Uruchom wątek
    Thread(target=command_thread).start()

# Funkcja konsoli (teraz używana tylko do diagnostyki)
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
# ZMODYFIKOWANA v4.1: Używa run_command_in_background
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
            "echo 'Picony zostały pomyślnie zainstalowane.' && sleep 3"
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
    
    # Użyj nowej funkcji tła zamiast console_screen_open
    run_command_in_background(session, title, [full_command], callback_on_finish=callback_on_finish)

# === E2KODI V2 - ROZPOZNAJ SYSTEM I ZAINSTALUJ (FUNKCJE GLOBALNE) ===
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

# ZMODYFIKOWANA v4.2: Używa nowego repo J00zka
def install_e2kodi(session):
    pkg = get_e2kodi_package_name()
    if not pkg:
        show_message_compat(session, "Nieznana wersja Pythona. E2Kodi nie zostało zainstalowane.", MessageBox.TYPE_ERROR)
        return

    repo_file = "/etc/opkg/opkg-j00zka.conf"
    repo_url = "https://j00zek.github.io/eeRepo" # <-- NOWY ADRES REPO
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
    ("--- Softcamy ---", "SEPARATOR"),
    ("Restart Oscam", "CMD:RESTART_OSCAM"),
    ("Kasuj hasło Oscam", "CMD:CLEAR_OSCAM_PASS"),
    ("oscam.dvbapi - zarządzaj", "CMD:MANAGE_DVBAPI"),
    ("Oscam z Feeda (Auto)", "CMD:INSTALL_BEST_OSCAM"),
    ("NCam 15.6 (Instalator)", "bash_raw:wget https://raw.githubusercontent.com/biko-73/Ncam_EMU/main/installer.sh -O - | /bin/sh"), # <-- POPRAWKA v4.2.1
    ("--- Wtyczki Online ---", "SEPARATOR"),
    ("XStreamity - Instalator", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-xstreamity"),
    ("ServiceApp - Instalator", "CMD:INSTALL_SERVICEAPP"),
    ("StreamlinkProxy - Instalator", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-streamlinkproxy"),
    ("AJPanel - Instalator", "bash_raw:wget https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh -O - | /bin/sh"),
    ("E2iPlayer Master - Instalacja/Aktualizacja", "bash_raw:wget -q 'https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh' -O - | /bin/sh"),
    ("EPG Import - Instalator", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh -O - | /bin/bash"),
    ("S4aUpdater - Instalator", "bash_raw:wget http://s4aupdater.one.pl/instalujs4aupdater.sh -O - | /bin/sh"),
    ("JediMakerXtream - Instalator", "bash_raw:wget https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh -O - | /bin/sh"),
    ("YouTube - Instalator", "bash_raw:opkg install https://github.com/Taapat/enigma2-plugin-youtube/releases/download/git1294/enigma2-plugin-extensions-youtube_py3-git1294-cbcf8b0-r0.0.ipk"),
    ("J00zeks Feed (Repo Installer)", "CMD:INSTALL_J00ZEK_REPO"),
    ("E2Kodi v2 - Instalator (j00zek)", "CMD:INSTALL_E2KODI"),
    ("Picon Updater - Instalator (Picony)", "bash_raw:wget -qO - https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh | /bin/sh"),
]

SOFTCAM_AND_PLUGINS_EN = [
    ("--- Softcams ---", "SEPARATOR"),
    ("Restart Oscam", "CMD:RESTART_OSCAM"),
    ("Clear Oscam Password", "CMD:CLEAR_OSCAM_PASS"),
    ("oscam.dvbapi - manage", "CMD:MANAGE_DVBAPI"),
    ("Oscam from Feed (Auto)", "CMD:INSTALL_BEST_OSCAM"),
    ("NCam 15.6 (Installer)", "bash_raw:wget https://raw.githubusercontent.com/biko-73/Ncam_EMU/main/installer.sh -O - | /bin/sh"), # <-- POPRAWKA v4.2.1
    ("--- Online Plugins ---", "SEPARATOR"),
    ("XStreamity - Installer", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-xstreamity"),
    ("ServiceApp - Installer", "CMD:INSTALL_SERVICEAPP"),
    ("StreamlinkProxy - Installer", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-streamlinkproxy"),
    ("AJPanel - Installer", "bash_raw:wget https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh -O - | /bin/sh"),
    ("E2iPlayer Master - Install/Update", "bash_raw:wget -q 'https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh' -O - | /bin/sh"),
    ("EPG Import - Installer", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh -O - | /bin/bash"),
    ("S4aUpdater - Installer", "bash_raw:wget http://s4aupdater.one.pl/instalujs4aupdater.sh -O - | /bin/sh"),
    ("JediMakerXtream - Installer", "bash_raw:wget https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh -O - | /bin/sh"),
    ("YouTube - Installer", "bash_raw:opkg install https://github.com/Taapat/enigma2-plugin-youtube/releases/download/git1294/enigma2-plugin-extensions-youtube_py3-git1294-cbcf8b0-r0.0.ipk"),
    ("J00zeks Feed (Repo Installer)", "CMD:INSTALL_J00ZEK_REPO"),
    ("E2Kodi v2 - Installer (j00zek)", "CMD:INSTALL_E2KODI"),
    ("Picon Updater - Installer (Picons)", "bash_raw:wget -qO - https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh | /bin/sh"),
]

# === NOWE PODZIELONE LISTY MENU (PL) ===
SYSTEM_TOOLS_PL = [
    ("--- Konfigurator ---", "SEPARATOR"),
    ("Super Konfigurator (Pierwsza Instalacja)", "CMD:SUPER_SETUP_WIZARD"),
    ("--- Narzędzia Systemowe ---", "SEPARATOR"),
    ("Menadżer Deinstalacji", "CMD:UNINSTALL_MANAGER"),
    ("Aktualizuj satellites.xml", "CMD:UPDATE_SATELLITES_XML"),
    ("Pobierz Picony (Transparent)", "archive:https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip"),
    ("--- Backup & Restore ---", "SEPARATOR"),
    ("Backup Listy Kanałów", "CMD:BACKUP_LIST"),
    ("Backup Konfiguracji Oscam", "CMD:BACKUP_OSCAM"),
    ("Restore Listy Kanałów", "CMD:RESTORE_LIST"),
    ("Restore Konfiguracji Oscam", "CMD:RESTORE_OSCAM"),
]

DIAGNOSTICS_PL = [
    ("--- Informacje i Aktualizacje ---", "SEPARATOR"),
    ("Informacje o AIO Panel", "CMD:SHOW_AIO_INFO"),
    ("Aktualizacja Wtyczki", "CMD:CHECK_FOR_UPDATES"),
    ("--- Diagnostyka ---", "SEPARATOR"),
    ("Diagnostyka Sieci", "CMD:NETWORK_DIAGNOSTICS"),
    ("Wolne miejsce (dysk/flash)", "CMD:FREE_SPACE_DISPLAY"),
    ("--- Czyszczenie i Bezpieczeństwo ---", "SEPARATOR"),
    ("Wyczyść Pamięć Tymczasową", "CMD:CLEAR_TMP_CACHE"),
    ("Wyczyść Pamięć RAM", "CMD:CLEAR_RAM_CACHE"),
    ("Kasuj hasło FTP", "CMD:CLEAR_FTP_PASS"),
    ("Ustaw Hasło FTP", "CMD:SET_SYSTEM_PASSWORD"),
]

# === NOWE PODZIELONE LISTY MENU (EN) ===
SYSTEM_TOOLS_EN = [
    ("--- Configurator ---", "SEPARATOR"),
    ("Super Setup Wizard (First Installation)", "CMD:SUPER_SETUP_WIZARD"),
    ("--- System Tools ---", "SEPARATOR"),
    ("Uninstallation Manager", "CMD:UNINSTALL_MANAGER"),
    ("Update satellites.xml", "CMD:UPDATE_SATELLITES_XML"),
    ("Download Picons (Transparent)", "archive:https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip"),
    ("--- Backup & Restore ---", "SEPARATOR"),
    ("Backup Channel List", "CMD:BACKUP_LIST"),
    ("Backup Oscam Config", "CMD:BACKUP_OSCAM"),
    ("Restore Channel List", "CMD:RESTORE_LIST"),
    ("Restore Oscam Config", "CMD:RESTORE_OSCAM"),
]

DIAGNOSTICS_EN = [
    ("--- Info & Updates ---", "SEPARATOR"),
    ("About AIO Panel", "CMD:SHOW_AIO_INFO"),
    ("Update Plugin", "CMD:CHECK_FOR_UPDATES"),
    ("--- Diagnostics ---", "SEPARATOR"),
    ("Network Diagnostics", "CMD:NETWORK_DIAGNOSTICS"),
    ("Free Space (disk/flash)", "CMD:FREE_SPACE_DISPLAY"),
    ("--- Cleaning & Security ---", "SEPARATOR"),
    ("Clear Temporary Cache", "CMD:CLEAR_TMP_CACHE"),
    ("Clear RAM Cache", "CMD:CLEAR_RAM_CACHE"),
    ("Clear FTP Password", "CMD:CLEAR_FTP_PASS"),
    ("Set FTP Password", "CMD:SET_SYSTEM_PASSWORD"),
]

# === NOWE 4 KATEGORIE ===
COL_TITLES = {
    "PL": ("Listy Kanałów", "Softcam i Wtyczki", "Narzędzia Systemowe", "Info i Diagnostyka"),
    "EN": ("Channel Lists", "Softcam & Plugins", "System Tools", "Info & Diagnostics")
}


# === FUNKCJE ŁADOWANIA DANYCH (GLOBALNE) ===
def _get_lists_from_repo_sync():
    manifest_url = "https://raw.githubusercontent.com/OliOli2013/PanelAIO-Lists/main/manifest.json"
    tmp_json_path = os.path.join(PLUGIN_TMP_PATH, 'manifest.json')
    prepare_tmp_dir()
    try:
        cmd = "wget --no-check-certificate -q -T 20 -O {} {}".format(tmp_json_path, manifest_url)
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
            item_type = item.get("type", "LIST").upper() # Domyślnie "LIST" (czyli kompletna lista .zip)
            name = item.get('name', 'Brak nazwy')
            author = item.get('author', '')
            url = item.get('url', '')
            
            if not url: # Pomiń, jeśli nie ma URL
                continue

            if item_type == "M3U":
                bouquet_id = item.get('bouquet_id', 'userbouquet.imported_m3u.tv')
                menu_title = "{} - {} (Dodaj jako Bukiet M3U)".format(name, author)
                action = "m3u:{}:{}:{}".format(url, bouquet_id, name)
                lists_menu.append((menu_title, action))
            
            elif item_type == "BOUQUET":
                # To jest dla plików .tv Azmana, które wymagają pasującego lamedb
                bouquet_id = item.get('bouquet_id', 'userbouquet.imported_ref.tv')
                menu_title = "{} - {} (Dodaj Bukiet REF)".format(name, author)
                action = "bouquet:{}:{}:{}".format(url, bouquet_id, name)
                lists_menu.append((menu_title, action))

            else: # Domyślnie type == "LIST"
                version = item.get('version', '')
                menu_title = "{} - {} ({})".format(name, author, version)
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
            lists.append(("{} - {}".format(display_name_base, date_info), "archive:{}".format(url_value)))
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
        sleep 3
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
            sleep 3
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
        self["message"].setText("Instalacja zakończona!\n\nZa chwilę nastąpi restart interfejsu GUI...")
        reactor.callLater(4, self.do_restart_and_close)

    def do_restart_and_close(self):
        self.close(self.session.open(TryQuitMainloop, 3))


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

    def check_dependencies(self):
        if os.path.exists(self.flag_file):
            self.start_async_data_load()
            return

        self["message"].setText("Pierwsze uruchomienie:\nInstalacja/Aktualizacja kluczowych zależności (SSL)...\nProszę czekać, to może potrwać minutę...\n\n(Instalacja odbywa się w tle)")
        
        # --- POPRAWKA v4.0.1 (Anti-Hang) ---
        # Usunięto 'opkg update', aby uniknąć zawieszania się na wolnej sieci
        cmd = """
        echo "AIO Panel: Cicha instalacja zależności (bez opkg update)..."
        opkg install wget ca-certificates > /dev/null 2>&1
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
        
        <widget name="legal_title" position="20,125" size="860,30" font="Regular;24" halign="center" valign="center" foregroundColor="yellow" />
        
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
class Panel(Screen):
    # Nowy skin z jedną listą i informacją o zakładkach
    skin = """
    <screen name='PanelAIO' position='center,center' size='1100,660' title='Panel AIO'>
        <widget name='qr_code_small' position='15,15' size='90,90' pixmap="{}" alphatest='blend' />
        <widget name="support_label" position="125,15" size="400,90" font="Regular;24" halign="left" valign="center" foregroundColor="green" />
        <widget name="title_label" position="500,15" size="585,40" font="Regular;32" halign="right" valign="center" transparent="1" />
        
        <widget name='tabs_display' position='15,115' size='1070,30' font='Regular;26' halign='center' />
        
        <widget name='menu' position='15,165' size='1070,420' itemHeight='40' font='Regular;22' scrollbarMode='showOnDemand' selectionPixmap='selection.png'/>
        
        <widget name='legend' position='15,600'  size='1070,28'  font='Regular;20' halign='center'/>
        <widget name='footer' position='center,630' size='1070,28' font='Regular;16' halign='center' foregroundColor='lightgrey'/>
    </screen>""".format(PLUGIN_QR_CODE_PATH)

    def __init__(self, session, fetched_data):
        Screen.__init__(self, session)
        self.setTitle("Panel AIO " + VER)
        self.sess = session
        self.lang = 'PL'
        
        # Logika detekcji obrazu (skopiowana z Twojego kodu)
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
        print(f"[AIO Panel] Przebudowa v2: Wykryto system: {self.image_type}")

        self.fetched_data_cache = fetched_data
        self.update_info = None
        self.update_prompt_shown = False
        self.wait_message_box = None
        
        self.active_tab = 0 # 0 = Listy, 1 = Wtyczki, 2 = Narzędzia, 3 = Diagnostyka
        self.tab_titles_def = COL_TITLES # Używamy globalnej definicji 4-kategorii
        self.all_data = ([], [], [], []) # Pusta krotka na 4 kategorie

        # Inicjalizacja komponentów skin
        self["qr_code_small"] = Pixmap()
        self["support_label"] = Label(TRANSLATIONS[self.lang]["support_text"])
        self["title_label"] = Label("AIO Panel " + VER)
        self["tabs_display"] = Label("") # Ustawiane w switch_tab
        self["menu"] = MenuList([])
        self["legend"] = Label(" ") # Ustawiane w set_language
        self["footer"] = Label(FOOT)
        
        # NOWA MAPA KLAWISZY (PRZYWRÓCONA LEGENDA + NAWIGACJA L/R)
        self["act"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.run_with_confirmation,
            "cancel": self.close,
            
            # Przyciski kolorowe (Twoja legenda)
            "red": lambda: self.set_language('PL'),
            "green": lambda: self.set_language('EN'),
            "yellow": self.restart_gui,
            "blue": self.check_for_updates_manual,
            
            # Przyciski nawigacyjne (L/R do zmiany zakładek)
            "left": self.prev_tab,
            "right": self.next_tab
            # Up/Down są domyślnie obsługiwane przez MenuList
        }, -1) 
        
        self.onShown.append(self.post_initial_setup)
        self.set_language(self.lang) # Pierwsze wypełnienie danych

    # --- NOWE FUNKCJE DLA ZAKŁADEK (L/R) ---
    
    def next_tab(self):
        """Przełącza na następną zakładkę"""
        new_tab_index = (self.active_tab + 1) % len(self.all_data) # % 4
        self.switch_tab(new_tab_index)

    def prev_tab(self):
        """Przełącza na poprzednią zakładkę"""
        new_tab_index = (self.active_tab - 1) % len(self.all_data) # % 4
        self.switch_tab(new_tab_index)

    def switch_tab(self, tab_index):
        """Przełącza aktywną zakładkę i odświeża listę menu oraz tytuł."""
        self.active_tab = tab_index
        lang = self.lang
        
        all_titles = self.tab_titles_def[lang]
        
        # --- NOWA LOGIKA PASKA ZAKŁADEK (Wizualna) ---
        active_color = r"\c00ffff00" # Żółty
        inactive_color = r"\c00999999" # Szary
        separator = r"\c00ffffff | " # Biały separator
        reset_color = r"\c00ffffff" # Domyślny (biały)
        
        tabs_display_text_list = []
        for i, title in enumerate(all_titles):
            if i == self.active_tab:
                tabs_display_text_list.append("{color}► {title} ◄{reset}".format(color=active_color, title=title, reset=reset_color))
            else:
                tabs_display_text_list.append("{color}{title}{reset}".format(color=inactive_color, title=title, reset=reset_color))
        
        # Połącz je separatorem
        self["tabs_display"].setText(separator.join(tabs_display_text_list))
        # --- KONIEC NOWEJ LOGIKI ---
        
        # Załaduj dane dla tej zakładki do menu
        data_list = self.all_data[self.active_tab]
        if data_list:
            menu_items = [str(item[0]) for item in data_list]
            self["menu"].setList(menu_items)
        else:
            self["menu"].setList([(TRANSLATIONS[lang]["loading_error_text"],)])

    # --- ZMODYFIKOWANE STARE FUNKCJE ---

    def set_language(self, lang):
        """ZMODYFIKOWANA: Ustawia język, buduje listę self.all_data (z 4 kategorii) i odświeża zakładkę."""
        self.lang = lang
        self.set_lang_headers_and_legends() # Ustawia legendę i etykiety
        
        try:
            # Pobieranie danych (skopiowane z Twojego kodu)
            repo_lists = self.fetched_data_cache.get("repo_lists", [])
            s4a_lists_full = self.fetched_data_cache.get("s4a_lists_full", [])
            best_oscam_version = self.fetched_data_cache.get("best_oscam_version", "Error")

            if not repo_lists:
                repo_lists = [(TRANSLATIONS[lang]["loading_error_text"] + " (REPO)", "SEPARATOR")]
            
            keywords_to_remove = ['bzyk', 'jakitaki']
            s4a_lists_filtered = [item for item in s4a_lists_full if not any(keyword in item[0].lower() for keyword in keywords_to_remove)]
            final_channel_lists = repo_lists + s4a_lists_filtered
            
            # Używamy nowych, podzielonych list globalnych
            softcam_menu = list(SOFTCAM_AND_PLUGINS_PL if lang == 'PL' else SOFTCAM_AND_PLUGINS_EN)
            tools_menu = list(SYSTEM_TOOLS_PL if lang == 'PL' else SYSTEM_TOOLS_EN)
            diag_menu = list(DIAGNOSTICS_PL if lang == 'PL' else DIAGNOSTICS_EN)
            
            # Logika filtrowania dla Hyperion/VTi (skopiowana z)
            if self.image_type in ["hyperion", "vti"]:
                emu_actions_to_block = [
                    "CMD:RESTART_OSCAM", "CMD:CLEAR_OSCAM_PASS", "CMD:MANAGE_DVBAPI",
                    "CMD:INSTALL_BEST_OSCAM", "bash_raw:wget https://raw.githubusercontent.com/biko-73/Ncam_EMU/main/installer.sh -O - | /bin/sh"
                ]
                softcam_menu_filtered = []
                for (name, action) in softcam_menu:
                    if action not in emu_actions_to_block:
                        softcam_menu_filtered.append((name, action))
                    elif "--- Softcamy ---" in name:
                        softcam_menu_filtered.append((name, action))
                        note = ("(Opcje EMU wyłączone - użyj menedżera obrazu)", "SEPARATOR") if lang == 'PL' else ("(EMU options disabled - use image manager)", "SEPARATOR")
                        softcam_menu_filtered.append(note)
                softcam_menu = softcam_menu_filtered

                # Filtrujemy też SuperKonfigurator z Narzędzi
                tools_menu_filtered = []
                for (name, action) in tools_menu:
                    if action != "CMD:SUPER_SETUP_WIZARD":
                        tools_menu_filtered.append((name, action))
                tools_menu = tools_menu_filtered
            
            # Logika dla Oscam (skopiowana z)
            for i, (name, action) in enumerate(softcam_menu):
                if action == "CMD:INSTALL_BEST_OSCAM":
                    oscam_text = "Oscam z Feeda ({})" if lang == 'PL' else "Oscam from Feed ({})"
                    softcam_menu[i] = (oscam_text.format(best_oscam_version), action)
            
            # Logika dla SuperKonfiguratora (skopiowana z)
            for i, (name, action) in enumerate(tools_menu):
                if action == "CMD:SUPER_SETUP_WIZARD":
                    tools_menu[i] = (TRANSLATIONS[lang]["sk_wizard_title"], action)

            # NOWA LOGIKA: Ustawiamy self.all_data na 4 kategorie
            self.all_data = (final_channel_lists, softcam_menu, tools_menu, diag_menu)
            
            # Odśwież bieżącą zakładkę, aby załadować dane
            self.switch_tab(self.active_tab) 
            
        except Exception as e:
            print("[AIO Panel] Błąd podczas przetwarzania danych dla set_language:", e)
            self.all_data = ([(TRANSLATIONS[self.lang]["loading_error_text"], "SEPARATOR")], [], [], [])
            self.switch_tab(0) # Załaduj zakładkę z błędem

    def set_lang_headers_and_legends(self):
        """ZMODYFIKOWANA: Ustawia tylko legendę i etykietę wsparcia."""
        # Ustawia legendę (Czerwony, Zielony, Żółty, Niebieski)
        self["legend"].setText(LEGEND_PL_COLOR if self.lang == 'PL' else LEGEND_EN_COLOR)
        
        # Ustawia etykietę "Wesprzyj rozwój..."
        self["support_label"].setText(TRANSLATIONS[self.lang]["support_text"])
        
        # Tytuł zakładki jest teraz ustawiany w switch_tab()

    def run_with_confirmation(self):
        """ZMODYFIKOWANA: Pobiera akcję z aktywnej zakładki i jednej listy."""
        try:
            # Pobieramy akcję z jednej listy, bazując na aktywnej zakładce
            name, action = self.all_data[self.active_tab][self["menu"].getSelectedIndex()]
        except (IndexError, KeyError, TypeError): 
            return # Błąd lub pusta lista
        if action == "SEPARATOR": 
            return # Nie rób nic dla separatorów

        # Reszta tej funkcji jest skopiowana 1:1 z Twojej starej funkcji
        actions_no_confirm = [
            "CMD:SHOW_AIO_INFO", "CMD:NETWORK_DIAGNOSTICS", "CMD:FREE_SPACE_DISPLAY", 
            "CMD:UNINSTALL_MANAGER", "CMD:MANAGE_DVBAPI", "CMD:CHECK_FOR_UPDATES", 
            "CMD:SUPER_SETUP_WIZARD", "CMD:UPDATE_SATELLITES_XML", "CMD:INSTALL_SERVICEAPP", 
            "CMD:INSTALL_E2KODI", "CMD:INSTALL_J00ZEK_REPO"
        ]
        
        # Logika dla Hyperion/VTi (skopiowana z)
        if self.image_type in ["hyperion", "vti"]:
            emu_actions = ["CMD:MANAGE_DVBAPI"]
            if action in emu_actions:
                self.sess.openWithCallback(
                    lambda ret: self.execute_action(name, action) if ret else None,
                    MessageBox, "UWAGA (Hyperion/VTi):\nTa funkcja może nie działać poprawnie, jeśli Twoje ścieżki EMU są niestandardowe.\n\nKontynuować mimo to?\n'{}'?".format(name), type=MessageBox.TYPE_YESNO
                )
                return 

        # Domyślna logika potwierdzenia (skopiowana z)
        if any(action.startswith(prefix) for prefix in actions_no_confirm):
            self.execute_action(name, action)
        else:
            self.sess.openWithCallback(
                lambda ret: self.execute_action(name, action) if ret else None,
                MessageBox, "Czy na pewno chcesz wykonać akcję:\n'{}'?".format(name), type=MessageBox.TYPE_YESNO
            )

    # --- POZOSTAŁE FUNKCJE POMOCNICZE (SKOPIOWANE 1:1) ---

    def show_info_screen(self):
        self.session.open(AIOInfoScreen)

    def post_initial_setup(self):
        reactor.callLater(1, self.check_for_updates_on_start)

    def check_for_updates_on_start(self):
        thread = Thread(target=self.fetch_update_info_in_background)
        thread.start()

    def fetch_update_info_in_background(self):
        try:
            update_info = self.perform_update_check_silent()
            if update_info and not self.update_prompt_shown:
                reactor.callFromThread(self.ask_for_update, update_info)
        except Exception as e:
            print("[AIO Panel] Błąd automatycznego sprawdzania aktualizacji:", e)

    def perform_update_check_silent(self):
        repo_base_url = "https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/"
        version_url = repo_base_url + "version.txt"
        changelog_url = repo_base_url + "changelog.txt"
        tmp_version_path = os.path.join(PLUGIN_TMP_PATH, 'version.txt')
        tmp_changelog_path = os.path.join(PLUGIN_TMP_PATH, 'changelog.txt')
        prepare_tmp_dir()
        try:
            cmd_ver = "wget --no-check-certificate -O {} {}".format(tmp_version_path, version_url)
            cmd_log = "wget --no-check-certificate -O {} {}".format(tmp_changelog_path, changelog_url)
            subprocess.Popen(cmd_ver, shell=True).wait()
            subprocess.Popen(cmd_log, shell=True).wait()

            if os.path.exists(tmp_version_path) and os.path.getsize(tmp_version_path) > 0:
                with open(tmp_version_path, 'r') as f:
                    latest_ver = f.read().strip()
                
                def parse_version(v_str):
                    v_str_clean = v_str.split('-')[0]
                    try:
                        return [int(part) for part in v_str_clean.split('.')]
                    except Exception:
                        return [0]
                
                current_ver_parts = parse_version(VER)
                latest_ver_parts = parse_version(latest_ver)

                if latest_ver_parts > current_ver_parts:
                    changelog_text = "Brak informacji o zmianach."
                    if os.path.exists(tmp_changelog_path) and os.path.getsize(tmp_changelog_path) > 0:
                        with open(tmp_changelog_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        found_version_section, changes = False, []
                        for line in lines:
                            line = line.strip()
                            if line == "[{}]".format(latest_ver):
                                found_version_section = True
                                continue
                            if found_version_section:
                                if line.startswith("[") and line.endswith("]"): break
                                if line: changes.append(line)
                        if changes: changelog_text = "\n".join(changes)
                    return {'latest_ver': latest_ver, 'changelog': changelog_text}
        except Exception as e:
            print("[AIO Panel] Silent update check failed:", e)
        return None

    def check_for_updates_manual(self):
        def manual_check_thread():
            info = self.perform_update_check_silent()
            if info:
                reactor.callFromThread(self.ask_for_update, info)
            else:
                reactor.callFromThread(lambda: show_message_compat(self.sess, TRANSLATIONS[self.lang]["already_latest"].format(ver=VER)))

        Thread(target=manual_check_thread).start()

    def ask_for_update(self, update_info):
        if not update_info: return
        self.update_prompt_shown = True
        self.update_info = update_info
        message = TRANSLATIONS[self.lang]["update_available_msg"].format(
            latest_ver=update_info['latest_ver'],
            current_ver=VER,
            changelog=update_info['changelog']
        )
        self.sess.openWithCallback(
            self.do_update, MessageBox, message, 
            title=TRANSLATIONS[self.lang]["update_available_title"], 
            type=MessageBox.TYPE_YESNO
        )
    
    def do_update(self, confirmed):
        if confirmed:
            update_cmd = 'wget -q "--no-check-certificate" https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh -O - | /bin/sh'
            # Używamy nowej funkcji tła
            run_command_in_background(self.sess, "Aktualizacja AIO Panel", [update_cmd])
            show_message_compat(self.sess, "Aktualizacja została uruchomiona w tle.\nProszę ZRESTARTOWAĆ GUI za około minutę.", MessageBox.TYPE_INFO, timeout=10)
        else:
            self.update_info = None

    # --- NOWA, GŁÓWNA FUNKCJA WYKONAWCZA ---
    def execute_action(self, name, action):
        title = name
        
        # --- LOGIKA DLA STARYCH LIST (.zip) ---
        if action.startswith("archive:"):
            try:
                list_url = action.split(':', 1)[1]
                # Wywołuje starą funkcję, która KASUJE wszystko (i używa teraz run_command_in_background)
                install_archive(self.sess, title, list_url, callback_on_finish=self.reload_settings_python)
            except IndexError:
                 show_message_compat(self.sess, "Błąd: Nieprawidłowy format akcji archive.", message_type=MessageBox.TYPE_ERROR)

        # --- NOWA LOGIKA DLA BUKIETÓW M3U (np. IPTV.org) ---
        elif action.startswith("m3u:"):
            try:
                parts = action.split(':', 3)
                url = parts[1] + ":" + parts[2] # Poprawka dla URLi zawierających ':'
                bouquet_info = parts[3].split(':', 1)
                bouquet_id = bouquet_info[0]
                bouquet_name = bouquet_info[1] if len(bouquet_info) > 1 else bouquet_id
                self.install_m3u_as_bouquet(title, url, bouquet_id, bouquet_name)
            except Exception as e:
                show_message_compat(self.sess, "Błąd parsowania akcji M3U: {}".format(e), message_type=MessageBox.TYPE_ERROR)
        
        # --- NOWA LOGIKA DLA BUKIETÓW REFERENCYJNYCH (pliki .tv Azmana) ---
        elif action.startswith("bouquet:"):
            try:
                parts = action.split(':', 3)
                url = parts[1] + ":" + parts[2] # Poprawka dla URLi
                bouquet_info = parts[3].split(':', 1)
                bouquet_id = bouquet_info[0]
                bouquet_name = bouquet_info[1] if len(bouquet_info) > 1 else bouquet_id
                self.install_bouquet_reference(title, url, bouquet_id, bouquet_name)
            except Exception as e:
                show_message_compat(self.sess, "Błąd parsowania akcji BOUQUET: {}".format(e), message_type=MessageBox.TYPE_ERROR)
        
        # --- LOGIKA DLA POLECEŃ CMD ---
        elif action.startswith("bash_raw:"):
            run_command_in_background(self.sess, title, [action.split(':', 1)[1]])

        elif action.startswith("CMD:"):
            command_key = action.split(':', 1)[1]
            if command_key == "SUPER_SETUP_WIZARD": self.run_super_setup_wizard()
            elif command_key == "CHECK_FOR_UPDATES": self.check_for_updates_manual()
            elif command_key == "UPDATE_SATELLITES_XML":
                script_path = os.path.join(PLUGIN_PATH, "update_satellites_xml.sh")
                run_command_in_background(self.sess, title, ["bash " + script_path], callback_on_finish=self.reload_settings_python)
            elif command_key == "INSTALL_SERVICEAPP":
                cmd = "opkg update && opkg install enigma2-plugin-systemplugins-serviceapp exteplayer3 gstplayer && opkg install uchardet --force-reinstall"
                run_command_in_background(self.sess, title, [cmd])
            elif command_key == "INSTALL_BEST_OSCAM": self.install_best_oscam()
            elif command_key == "MANAGE_DVBAPI": self.manage_dvbapi()
            elif command_key == "UNINSTALL_MANAGER": self.show_uninstall_manager()
            elif command_key == "CLEAR_OSCAM_PASS": self.clear_oscam_password() # Ta jest bez konsoli
            elif command_key == "CLEAR_FTP_PASS":
                run_command_in_background(self.sess, title, ["passwd -d root"])
            elif command_key == "SET_SYSTEM_PASSWORD": self.set_system_password()
            elif command_key == "RESTART_OSCAM": self.restart_oscam()
            elif command_key == "CLEAR_TMP_CACHE": 
                run_command_in_background(self.sess, title, ["rm -rf " + PLUGIN_TMP_PATH + "*"])
            elif command_key == "CLEAR_RAM_CACHE": 
                run_command_in_background(self.sess, title, ["sync; echo 3 > /proc/sys/vm/drop_caches"])
            elif command_key == "INSTALL_E2KODI": install_e2kodi(self.sess) # Ta już używa tła
            elif command_key == "INSTALL_J00ZEK_REPO": self.install_j00zek_repo() # Ta używa tła
            elif command_key == "SHOW_AIO_INFO": self.show_info_screen()
            elif command_key == "BACKUP_LIST": self.backup_lists()
            elif command_key == "BACKUP_OSCAM": self.backup_oscam()
            elif command_key == "RESTORE_LIST": self.restore_lists()
            elif command_key == "RESTORE_OSCAM": self.restore_oscam()
            
            # WYJĄTKI, KTÓRE MUSZĄ POKAZAĆ KONSOLĘ
            elif command_key == "NETWORK_DIAGNOSTICS": self.run_network_diagnostics() # Pokazuje wyjście
            elif command_key == "FREE_SPACE_DISPLAY": 
                console_screen_open(self.sess, "Wolne miejsce", ["df -h"], close_on_finish=False) # Pokazuje wyjście

    # --- NOWE FUNKCJE DLA J00ZEK I BUKIETÓW ---

    def install_j00zek_repo(self):
        """Instaluje repozytorium J00Zek i aktualizuje pakiety."""
        title = "Instalator Repozytorium J00Zek"
        cmd = """
            echo "Instalowanie J00Zek Feed..."
            echo "src/gz opkg-j00zka https://j00zek.github.io/eeRepo" > /etc/opkg/opkg-j00zka.conf
            echo "Aktualizowanie listy pakietów..."
            opkg update
            echo "Zakończono."
            sleep 3
        """
        run_command_in_background(self.sess, title, [cmd])

    def install_m3u_as_bouquet(self, title, url, bouquet_id, bouquet_name):
        """Pobiera M3U, konwertuje je w locie na bukiet E2 i dodaje do listy."""
        tmp_m3u_path = os.path.join(PLUGIN_TMP_PATH, "temp.m3u")
        download_cmd = "wget -T 30 --no-check-certificate -O \"{}\" \"{}\"".format(tmp_m3u_path, url)
        
        def on_download_finished(*args):
            if not (fileExists(tmp_m3u_path) and os.path.getsize(tmp_m3u_path) > 0):
                show_message_compat(self.sess, "Błąd: Nie udało się pobrać pliku M3U.", message_type=MessageBox.TYPE_ERROR)
                return
            
            # Pokaż okno "Pracuję"
            self.wait_message_box = self.sess.open(MessageBox, "Pobrano plik M3U.\nTrwa konwersja na bukiet E2...\nProszę czekać.", MessageBox.TYPE_INFO, enable_input=False)
            
            # Uruchom parsowanie w osobnym wątku, aby nie blokować GUI
            Thread(target=self._parse_m3u_thread, args=(tmp_m3u_path, bouquet_id, bouquet_name)).start()

        run_command_in_background(self.sess, "Pobieranie M3U: " + title, [download_cmd], callback_on_finish=on_download_finished)

    def _parse_m3u_thread(self, tmp_m3u_path, bouquet_id, bouquet_name):
        """Wątek roboczy do parsowania M3U i tworzenia pliku bukietu."""
        try:
            e2_bouquet_path = os.path.join(PLUGIN_TMP_PATH, bouquet_id)
            e2_lines = ["#NAME {}\n".format(bouquet_name)]
            channel_name = "N/A"
            
            with open(tmp_m3u_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#EXTINF:'):
                        try:
                            channel_name = line.split(',')[-1].strip()
                        except:
                            channel_name = "Brak Nazwy"
                    elif line.startswith('http://') or line.startswith('https://'):
                        # Formatowanie URL dla Enigmy2: zamień : na %3a
                        formatted_url = line.replace(':', '%3a')
                        # Używamy serwisu 4097 (non-TS, np. HLS)
                        e2_lines.append("#SERVICE 4097:0:1:0:0:0:0:0:0:0:{}:{}\n".format(formatted_url, channel_name))
                        channel_name = "N/A" # Reset
            
            if len(e2_lines) <= 1:
                raise Exception("Nie znaleziono kanałów w pliku M3U")

            # Zapisz tymczasowy plik bukietu
            with open(e2_bouquet_path, 'w', encoding='utf-8') as f:
                f.writelines(e2_lines)

            # Przekaż do głównego wątku, aby wykonać operacje na plikach E2
            reactor.callFromThread(self._install_parsed_bouquet, e2_bouquet_path, bouquet_id)

        except Exception as e:
            print("[AIO Panel] Błąd parsowania M3U:", e)
            if self.wait_message_box: 
                reactor.callFromThread(self.wait_message_box.close)
            reactor.callFromThread(show_message_compat, self.sess, "Błąd parsowania pliku M3U:\n{}".format(e), message_type=MessageBox.TYPE_ERROR)

    def _install_parsed_bouquet(self, tmp_bouquet_path, bouquet_id):
        """Wywoływane w głównym wątku: Kopiuje plik bukietu i aktualizuje bouquets.tv."""
        if self.wait_message_box:
            reactor.callFromThread(self.wait_message_box.close)
            
        e2_dir = "/etc/enigma2"
        bouquets_tv_path = os.path.join(e2_dir, "bouquets.tv")
        target_bouquet_path = os.path.join(e2_dir, bouquet_id)
        
        # 1. Przenieś plik
        try:
            shutil.move(tmp_bouquet_path, target_bouquet_path)
        except Exception as e:
            show_message_compat(self.sess, "Błąd kopiowania bukietu: {}".format(e), message_type=MessageBox.TYPE_ERROR)
            return

        # 2. Edytuj bouquets.tv
        try:
            entry_to_add = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "{}" ORDER BY bouquet\n'.format(bouquet_id)
            entry_exists = False
            
            if fileExists(bouquets_tv_path):
                with open(bouquets_tv_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if bouquet_id in line:
                            entry_exists = True
                            break
            
            if not entry_exists:
                with open(bouquets_tv_path, 'a', encoding='utf-8') as f:
                    f.write(entry_to_add)
            
        except Exception as e:
            show_message_compat(self.sess, "Błąd edycji bouquets.tv: {}".format(e), message_type=MessageBox.TYPE_ERROR)
            return

        # 3. Przeładuj listę
        msg = "Bukiet '{}' został pomyślnie dodany.\nPrzeładowuję listy...".format(bouquet_id) if not entry_exists else "Bukiet '{}' został zaktualizowany.\nPrzeładowuję listy...".format(bouquet_id)
        show_message_compat(self.sess, msg, message_type=MessageBox.TYPE_INFO, timeout=5)
        self.reload_settings_python()

    def install_bouquet_reference(self, title, url, bouquet_id, bouquet_name):
        """Instaluje plik bukietu .tv (tylko referencje, bez lamedb)."""
        e2_dir = "/etc/enigma2"
        bouquets_tv_path = os.path.join(e2_dir, "bouquets.tv")
        target_bouquet_path = os.path.join(e2_dir, bouquet_id)
        tmp_bouquet_path = os.path.join(PLUGIN_TMP_PATH, bouquet_id)

        cmd = """
        echo "Pobieranie pliku bukietu referencyjnego..."
        wget -T 30 --no-check-certificate -O "{tmp_path}" "{url}"
        if [ $? -eq 0 ] && [ -s "{tmp_path}" ]; then
            echo "Instalowanie bukietu..."
            mv "{tmp_path}" "{target_path}"
            
            BOUQUET_ENTRY='#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "{b_id}" ORDER BY bouquet'
            
            if ! grep -q -F "{b_id}" "{bq_tv_path}"; then
                echo "Dodawanie wpisu do bouquets.tv..."
                echo "$BOUQUET_ENTRY" >> "{bq_tv_path}"
            else
                echo "Wpis dla {b_id} już istnieje w bouquets.tv."
            fi
            echo "Instalacja bukietu zakończona."
            echo " "
            echo "!!! UWAGA !!!"
            echo "To jest bukiet referencyjny. Kanały będą działać (nie będą 'N/A')"
            echo "TYLKO jeśli Twoja główna lista (np. bzyk83) zawiera pasujący plik lamedb!"
            echo " "
            sleep 8
        else
            echo "BŁĄD: Nie udało się pobrać pliku bukietu."
            sleep 5
        fi
        """.format(
            url=url,
            tmp_path=tmp_bouquet_path,
            target_path=target_bouquet_path,
            b_id=bouquet_id,
            bq_tv_path=bouquets_tv_path
        )
        
        run_command_in_background(self.sess, title, [cmd], callback_on_finish=self.reload_settings_python)

    # --- NOWE FUNKCJE DLA BACKUP/RESTORE (v4.1.2 z poprawką) ---

    def _get_backup_path(self):
        """Zwraca najlepszą ścieżkę do backupu lub None, jeśli nie ma nośnika."""
        hdd_path = "/media/hdd/aio_backups/"
        usb_path = "/media/usb/aio_backups/"
        
        if os.path.exists("/media/hdd") and os.path.ismount("/media/hdd"):
            return hdd_path
        elif os.path.exists("/media/usb") and os.path.ismount("/media/usb"):
            return usb_path
        elif os.path.exists("/media/hdd"):
            return hdd_path
        elif os.path.exists("/media/usb"):
            return usb_path
            
        return None # Nie znaleziono nośnika

    def backup_lists(self):
        path = self._get_backup_path()
        if not path:
            show_message_compat(self.sess, "Błąd: Nie znaleziono /media/hdd ani /media/usb.\nPodłącz nośnik i spróbuj ponownie.", MessageBox.TYPE_ERROR)
            return
        
        title = "Backup Listy Kanałów"
        backup_file = os.path.join(path, "aio_channels_backup.tar.gz")
        
        # --- POPRAWKA v4.1.1 (Błąd 'tar') ---
        cmd = """
            echo "Tworzenie ścieżki backupu: {path}"
            mkdir -p "{path}"
            echo "Archiwizowanie listy kanałów z /etc/enigma2/..."
            
            # Przejdź do katalogu i twórz archiwum
            cd /etc/enigma2
            
            # Spakuj pliki, ignoruj błędy jeśli któregoś pliku nie ma (np. bouquets.radio)
            tar -czf "{backup_file}" lamedb bouquets.tv bouquets.radio userbouquet.*.tv userbouquet.*.radio 2>/dev/null
            
            if [ $? -eq 0 ]; then
                echo "Backup listy kanałów zakończony pomyślnie!"
                echo "Zapisano w: {backup_file}"
            else
                echo "BŁĄD: Wystąpił błąd podczas tworzenia archiwum."
            fi
            sleep 5
        """.format(path=path, backup_file=backup_file)
        
        run_command_in_background(self.sess, title, [cmd])

    def backup_oscam(self):
        path = self._get_backup_path()
        if not path:
            show_message_compat(self.sess, "Błąd: Nie znaleziono /media/hdd ani /media/usb.\nPodłącz nośnik i spróbuj ponownie.", MessageBox.TYPE_ERROR)
            return

        title = "Backup Konfiguracji Oscam"
        backup_file = os.path.join(path, "aio_oscam_config_backup.tar.gz")
        cmd = """
            echo "Tworzenie ścieżki backupu: {path}"
            mkdir -p "{path}"
            echo "Lokalizowanie konfiguracji Oscam..."
            CONFIG_DIR=$(find /etc/tuxbox/config -name oscam.conf -exec dirname {{}} \\; | sort -u | head -n 1)
            
            if [ -z "$CONFIG_DIR" ]; then
                echo "BŁĄD: Nie mogę znaleźć katalogu z oscam.conf!"
                echo "Standardowe ścieżki to /etc/tuxbox/config/"
                sleep 5
                exit 1
            fi
            
            echo "Znaleziono konfigurację w: $CONFIG_DIR"
            echo "Archiwizowanie..."
            tar -czf "{backup_file}" -C "$CONFIG_DIR" .
            
            if [ $? -eq 0 ]; then
                echo "Backup Oscam zakończony pomyślnie!"
                echo "Zapisano w: {backup_file}"
            else
                echo "BŁĄD: Wystąpił błąd podczas tworzenia archiwum."
            fi
            sleep 5
        """.format(path=path, backup_file=backup_file)
        run_command_in_background(self.sess, title, [cmd])

    def restore_lists(self):
        path = self._get_backup_path()
        if not path:
            show_message_compat(self.sess, "Błąd: Nie znaleziono /media/hdd ani /media/usb.", MessageBox.TYPE_ERROR)
            return
        
        backup_file = os.path.join(path, "aio_channels_backup.tar.gz")
        if not fileExists(backup_file):
            show_message_compat(self.sess, "Błąd: Nie znaleziono pliku kopii zapasowej:\n" + backup_file, MessageBox.TYPE_ERROR)
            return

        self.sess.openWithCallback(
            lambda ret: self._do_restore_lists(backup_file) if ret else None,
            MessageBox, "Czy na pewno chcesz przywrócić listę kanałów z kopii?\n\nObecna lista zostanie NADPISANA.", type=MessageBox.TYPE_YESNO
        )

    def _do_restore_lists(self, backup_file):
        title = "Przywracanie Listy Kanałów"
        # --- POPRAWKA v4.1.2 ---
        # Poprawna ścieżka rozpakowania to /etc/enigma2
        cmd = """
            echo "Przywracanie listy kanałów z pliku..."
            echo "{backup_file}"
            
            # Kasujemy starą listę, aby uniknąć konfliktów
            rm -f /etc/enigma2/bouquets.tv /etc/enigma2/bouquets.radio /etc/enigma2/userbouquet.*.tv /etc/enigma2/userbouquet.*.radio /etc/enigma2/lamedb
            
            # Rozpakowujemy do /etc/enigma2/
            tar -xzf "{backup_file}" -C /etc/enigma2/
            
            if [ $? -eq 0 ]; then
                echo "Lista kanałów przywrócona pomyślnie."
                echo "Przeładowywanie listy..."
            else
                echo "BŁĄD: Wystąpił błąd podczas przywracania."
            fi
            sleep 5
        """.format(backup_file=backup_file)
        
        run_command_in_background(self.sess, title, [cmd], callback_on_finish=self.reload_settings_python)

    def restore_oscam(self):
        path = self._get_backup_path()
        if not path:
            show_message_compat(self.sess, "Błąd: Nie znaleziono /media/hdd ani /media/usb.", MessageBox.TYPE_ERROR)
            return
        
        backup_file = os.path.join(path, "aio_oscam_config_backup.tar.gz")
        if not fileExists(backup_file):
            show_message_compat(self.sess, "Błąd: Nie znaleziono pliku kopii zapasowej:\n" + backup_file, MessageBox.TYPE_ERROR)
            return

        self.sess.openWithCallback(
            lambda ret: self._do_restore_oscam(backup_file) if ret else None,
            MessageBox, "Czy na pewno chcesz przywrócić konfigurację Oscam?\n\nObecna konfiguracja zostanie NADPISANA.", type=MessageBox.TYPE_YESNO
        )
        
    def _do_restore_oscam(self, backup_file):
        title = "Przywracanie Konfiguracji Oscam"
        cmd = """
            echo "Lokalizowanie konfiguracji Oscam..."
            CONFIG_DIR=$(find /etc/tuxbox/config -name oscam.conf -exec dirname {{}} \\; | sort -u | head -n 1)
            if [ -z "$CONFIG_DIR" ]; then
                echo "BŁĄD: Nie mogę znaleźć katalogu konfiguracyjnego Oscam!"
                sleep 5
                exit 1
            fi

            echo "Przywracanie konfiguracji do: $CONFIG_DIR"
            tar -xzf "{backup_file}" -C "$CONFIG_DIR"
            
            if [ $? -eq 0 ]; then
                echo "Konfiguracja Oscam przywrócona."
                echo "Restartowanie Oscam..."
            else
                echo "BŁĄD: Wystąpił błąd podczas przywracania."
            fi
            sleep 3
        """.format(backup_file=backup_file)
        
        run_command_in_background(self.sess, title, [cmd], callback_on_finish=self.restart_oscam)

    # --- POZOSTAŁE FUNKCJE POMOCNICZE (BEZ ZMIAN) ---

    def run_network_diagnostics(self):
        # Ta funkcja celowo używa console_screen_open, aby pokazać wynik
        local_ip = "N/A"
        try:
            if network is not None: 
                for iface in ("eth0", "wlan0", "br0", "br-lan"):
                    if network.isLinkUp(iface):
                        ip = network.getIpAddress(iface)
                        if ip and ip != "0.0.0.0":
                            local_ip = ip
                            break
            elif iNetworkInfo is not None:
                 for iface in ("eth0", "wlan0", "br0", "br-lan"):
                     if iNetworkInfo.getAdapterAttribute(iface, "up"):
                         ip = iNetworkInfo.getAdapterAttribute(iface, "ip")
                         if ip and ip != "0.0.0.0":
                            local_ip = ip
                            break
        except Exception as e:
            print("[AIO Panel] Błąd pobierania lokalnego IP:", e)
            local_ip = TRANSLATIONS[self.lang]["net_diag_na"]
        
        if isinstance(local_ip, (list, tuple)):
            local_ip = '.'.join(map(str, local_ip)).replace(',', '.')
        elif local_ip:
            local_ip = str(local_ip).strip("[]' ")
            
        na_text = TRANSLATIONS[self.lang]["net_diag_na"]
        script_path = os.path.join(PLUGIN_TMP_PATH, "speedtest.py")
        output_file = os.path.join(PLUGIN_TMP_PATH, "speedtest_result.txt")
        cmd = """
            echo "--- AIO Panel - Diagnostyka Sieci ---"
            echo " "
            echo "Sprawdzanie połączenia z internetem..."
            if ! ping -c 1 -W 3 google.com &>/dev/null; then
                echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                echo "!!! {no_connection} !!!"
                echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                exit 1 
            fi
            
            echo "Pobieranie publicznego adresu IP..."
            PUBLIC_IP=$(wget -qO- --timeout=10 http://ipinfo.io/ip || echo "{na}")
            
            echo "Uruchamianie testu prędkości (może to potrwać minutę)..."
            
            if [ ! -f "{script_path}" ]; then
                echo "Pobieranie narzędzia speedtest-cli..."
                if command -v curl >/dev/null 2>&1; then
                    curl -s -o "{script_path}" https://raw.githubusercontent.com/sivel/speedtest-cli/master/speedtest.py
                else
                    wget -O "{script_path}" https://raw.githubusercontent.com/sivel/speedtest-cli/master/speedtest.py &>/dev/null
                fi
                chmod +x "{script_path}"
            fi
            
            if command -v python3 >/dev/null 2>&1; then
                PYTHON_CMD="python3"
            else
                PYTHON_CMD="python"
            fi
            
            echo "Uruchamianie skryptu speedtest..."
            $PYTHON_CMD -W ignore "{script_path}" --simple > "{output_file}" 2>&1
            EXIT_CODE=$?
            
            if [ $EXIT_CODE -ne 0 ]; then
                echo "--- BEGIN speedtest output (code: $EXIT_CODE) ---"
                cat "{output_file}"
                echo "--- END speedtest output ---"
            fi
            
            if [ $EXIT_CODE -eq 0 ] && [ -s "{output_file}" ]; then
                PING_SPEEDTEST=$(grep 'Ping:' "{output_file}" | awk '{{print $2" "$3}}' || echo "{na}")
                DOWNLOAD_SPEED=$(grep 'Download:' "{output_file}" | awk '{{print $2" "$3}}' || echo "{na}")
                UPLOAD_SPEED=$(grep 'Upload:' "{output_file}" | awk '{{print $2" "$3}}' || echo "{na}")
            else
                echo " "
                if [ $EXIT_CODE -ne 0 ]; then
                    echo "*** {error_msg} (kod: $EXIT_CODE) ***"
                fi
                PING_SPEEDTEST="{na}"
                DOWNLOAD_SPEED="{na}"
                UPLOAD_SPEED="{na}"
            fi
            
            rm -f "{output_file}"

            echo " "
            echo "-------------------------------------------"
            echo " {local_ip_label} {local_ip_val}" 
            echo " {ip_label} $PUBLIC_IP"
            echo " {ping_label} $PING_SPEEDTEST"
            echo " {download_label} $DOWNLOAD_SPEED"
            echo " {upload_label} $UPLOAD_SPEED"
            echo "-------------------------------------------"
            echo " "
            echo "Diagnostyka zakończona."
            echo "Naciśnij OK lub EXIT, aby zamknąć."
        """.format(
            no_connection=TRANSLATIONS[self.lang]["net_diag_no_connection"],
            local_ip_label=TRANSLATIONS[self.lang]["net_diag_local_ip"],
            local_ip_val=local_ip if local_ip else na_text, 
            ip_label=TRANSLATIONS[self.lang]["net_diag_ip"],
            ping_label=TRANSLATIONS[self.lang]["net_diag_ping"],
            download_label=TRANSLATIONS[self.lang]["net_diag_download"],
            upload_label=TRANSLATIONS[self.lang]["net_diag_upload"],
            na=na_text,
            script_path=script_path,
            output_file=output_file,
            error_msg=TRANSLATIONS[self.lang]["net_diag_error"]
        )
        console_screen_open(self.sess, TRANSLATIONS[self.lang]["net_diag_title"], [cmd], close_on_finish=False)
        
    def restart_gui(self): 
        self.sess.open(TryQuitMainloop, 3)

    def reload_settings_python(self, *args):
        try:
            db = eDVBDB.getInstance()
            db.reloadServicelist()
            db.reloadBouquets()
            show_message_compat(self.session, "Listy kanałów przeładowane.", message_type=MessageBox.TYPE_INFO, timeout=3)
        except Exception as e:
            print("[AIO Panel] Błąd podczas przeładowywania list:", e)
            show_message_compat(self.session, "Wystąpił błąd podczas przeładowywania list.", message_type=MessageBox.TYPE_ERROR)

    def clear_oscam_password(self):
        # Ta funkcja nie używa konsoli, jest OK
        cmd_find = "find /etc/tuxbox/config -name oscam.conf -exec dirname {} \\; | sort -u"
        try:
            process = subprocess.Popen(cmd_find, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            config_dirs = [line.strip() for line in stdout.decode('utf-8').splitlines() if line.strip()]
            if not config_dirs: config_dirs.append("/etc/tuxbox/config")
            found = False
            for d in config_dirs:
                conf_path = os.path.join(d, "oscam.conf")
                if fileExists(conf_path):
                    with open(conf_path, "r") as f: lines = f.readlines()
                    new_lines = [line for line in lines if not line.strip().lower().startswith("httppwd") or line.strip().startswith('#')]
                    if len(new_lines) < len(lines):
                        with open(conf_path, "w") as f: f.writelines(new_lines)
                        found = True
            if found:
                show_message_compat(self.sess, "Hasło Oscam zostało skasowane.", message_type=MessageBox.TYPE_INFO)
            else:
                show_message_compat(self.sess, "Nie znaleziono hasła Oscam w plikach konfiguracyjnych.", message_type=MessageBox.TYPE_INFO)
        except Exception as e:
            show_message_compat(self.sess, "Błąd: {}".format(e), message_type=MessageBox.TYPE_ERROR)

    def manage_dvbapi(self):
        dvbapi_options = [
            ("Pobierz z oficjalnego repo Oscam (GitHub)", "https://raw.githubusercontent.com/picons/oscam-configs/main/oscam.dvbapi"),
            ("Pobierz z repo Oscam-Emu (GitHub)", "https://raw.githubusercontent.com/oscam-emu/oscam-emu/master/oscam.dvbapi"),
            ("Pobierz z repo Oscam-Patched (GitHub)", "https://raw.githubusercontent.com/oscam-emu/oscam-patched/master/oscam.dvbapi"),
            ("Pobierz z oryginalnego repo SVN", "http://www.streamboard.tv/svn/oscam/trunk/oscam.dvbapi"),
            ("Pobierz z własnego źródła (ręczny URL)...", "custom"),
            ("Kasuj zawartość pliku oscam.dvbapi", "clear")
        ]
        self.sess.openWithCallback(
            self.on_dvbapi_option_selected,
            ChoiceBox,
            title="Zarządzanie plikiem oscam.dvbapi",
            list=[(name, url) for name, url in dvbapi_options]
        )

    def on_dvbapi_option_selected(self, choice):
        if not choice: return
        if choice[1] == "custom":
            self.sess.openWithCallback(self.on_custom_dvbapi_url_entered, InputBox, title="Podaj własny URL do pliku oscam.dvbapi", text="https://")
        elif choice[1] == "clear":
            self.sess.openWithCallback(self.do_clear_dvbapi, MessageBox, "Czy na pewno chcesz skasować zawartość pliku oscam.dvbapi?", type=MessageBox.TYPE_YESNO)
        else:
            self.process_dvbapi_download(choice[1])

    def on_custom_dvbapi_url_entered(self, url):
        if url: self.process_dvbapi_download(url)

    def process_dvbapi_download(self, url):
        cmd = """URL="{url}"; CONFIG_DIRS=$(find /etc/tuxbox/config -name oscam.conf -exec dirname {{}} \\; | sort -u); [ -z "$CONFIG_DIRS" ] && CONFIG_DIRS="/etc/tuxbox/config"; for DIR in $CONFIG_DIRS; do [ ! -d "$DIR" ] && mkdir -p "$DIR"; [ -f "$DIR/oscam.dvbapi" ] && cp "$DIR/oscam.dvbapi" "$DIR/oscam.dvbapi.bak"; if wget -q --timeout=30 -O "$DIR/oscam.dvbapi.tmp" "$URL"; then if grep -q "P:" "$DIR/oscam.dvbapi.tmp"; then mv "$DIR/oscam.dvbapi.tmp" "$DIR/oscam.dvbapi"; echo "Zaktualizowano: $DIR/oscam.dvbapi"; else echo "Błąd pobierania: Plik z URL nie zawiera wpisów 'P:'. Przywrcono backup dla $DIR/oscam.dvbapi"; [ -f "$DIR/oscam.dvbapi.bak" ] && mv "$DIR/oscam.dvbapi.bak" "$DIR/oscam.dvbapi"; fi; else echo "Błąd pobierania z URL dla: $DIR/oscam.dvbapi. Przywrcono backup."; [ -f "$DIR/oscam.dvbapi.bak" ] && mv "$DIR/oscam.dvbapi.bak" "$DIR/oscam.dvbapi"; fi; done; for i in softcam.oscam oscam softcam; do [ -f "/etc/init.d/$i" ] && /etc/init.d/$i restart && break; done""".format(url=url)
        run_command_in_background(self.sess, "Aktualizacja oscam.dvbapi", [cmd])

    def do_clear_dvbapi(self, confirmed):
        if confirmed:
            cmd = """CONFIG_DIRS=$(find /etc/tuxbox/config -name oscam.conf -exec dirname {{}} \\; | sort -u); [ -z "$CONFIG_DIRS" ] && CONFIG_DIRS="/etc/tuxbox/config"; echo "Próbuję skasować zawartość oscam.dvbapi w katalogach: $CONFIG_DIRS"; for DIR in $CONFIG_DIRS; do DVBAPI_PATH="$DIR/oscam.dvbapi"; if [ -f "$DVBAPI_PATH" ]; then cp "$DVBAPI_PATH" "$DVBAPI_PATH.bak"; echo "" > "$DVBAPI_PATH"; echo "Skasowano: $DVBAPI_PATH"; fi; done; for i in softcam.oscam oscam softcam; do [ -f "/etc/init.d/$i" ] && /etc/init.d/$i restart && break; done"""
            run_command_in_background(self.sess, "Kasowanie oscam.dvbapi", [cmd])

    def clear_ftp_password(self):
        run_command_in_background(self.sess, "Kasowanie hasła FTP", ["passwd -d root"])

    def set_system_password(self):
        self.sess.openWithCallback(lambda p: run_command_in_background(self.sess, "Ustawianie Hasła", ["(echo {}; echo {}) | passwd".format(p, p)]) if p else None, InputBox, title="Wpisz nowe hasło dla konta root:")

    def show_free_space(self):
        # Ta funkcja celowo używa console_screen_open
        console_screen_open(self.sess, "Wolne miejsce", ["df -h"], close_on_finish=False)

    def restart_oscam(self, *args): # Dodano *args, aby akceptować callback z konsoli
        cmd = 'FOUND=0; for SCRIPT in softcam.oscam oscam softcam; do INIT_SCRIPT="/etc/init.d/$SCRIPT"; if [ -f "$INIT_SCRIPT" ]; then echo "Restartowanie Oscam za pomocą $SCRIPT..."; $INIT_SCRIPT restart; FOUND=1; break; fi; done; [ $FOUND -ne 1 ] && echo "Nie znaleziono skryptu startowego Oscam."; sleep 2;'
        run_command_in_background(self.sess, "Restart Oscam", [cmd.strip()])

    def show_uninstall_manager(self):
        try:
            process = subprocess.Popen("opkg list-installed", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            packages = sorted([line.split(' - ')[0] for line in stdout.decode('utf-8', errors='ignore').splitlines() if ' - ' in line and line.split(' - ')[0]])
            
            if not packages:
                 show_message_compat(self.sess, "Brak zainstalowanych pakietów do wyświetlenia.", message_type=MessageBox.TYPE_INFO)
                 return
                 
            def on_package_selected(choice):
                if choice:
                    self.sess.openWithCallback(lambda c: run_command_in_background(self.sess, "Odinstalowywanie: " + choice[0], ["opkg remove " + choice[0]]) if c else None, MessageBox, "Czy na pewno chcesz odinstalować pakiet:\n{}?".format(choice[0]), type=MessageBox.TYPE_YESNO)
            
            list_options = [(p,) for p in packages]
            self.sess.openWithCallback(on_package_selected, ChoiceBox, title="Wybierz pakiet do odinstalowania", list=list_options)
            
        except Exception as e:
            show_message_compat(self.sess, "Błąd Menadżera Deinstalacji:\n{}".format(e), message_type=MessageBox.TYPE_ERROR)

    def install_best_oscam(self, callback=None):
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
                echo "Nie znaleziono odpowiedniego pakietu Oscam w feedach."
                echo "Próbuję instalacji z alternatywnego źródła (Levi45)..."
                wget -q "--no-check-certificate" https://raw.githubusercontent.com/levi-45/Levi45Emulator/main/installer.sh -O - | /bin/sh
            fi
            echo "Instalacja Oscam zakończona."
            sleep 3
        """
        run_command_in_background(self.sess, "Instalator Oscam", [cmd], callback_on_finish=callback)

    def run_super_setup_wizard(self):
        lang = self.lang
        options = [
            (TRANSLATIONS[lang]["sk_option_deps"], "deps_only"),
            (TRANSLATIONS[lang]["sk_option_basic_no_picons"], "install_basic_no_picons"),
            (TRANSLATIONS[lang]["sk_option_full_picons"], "install_with_picons"),
            (TRANSLATIONS[lang]["sk_option_cancel"], "cancel")
        ]
        self.sess.openWithCallback(
            self._super_wizard_selected,
            ChoiceBox,
            title=TRANSLATIONS[lang]["sk_choice_title"],
            list=options
        )

    def _super_wizard_selected(self, choice):
        if not choice or choice[1] == "cancel":
            return

        key, lang = choice[1], self.lang
        steps, message = [], ""
        
        if key == "deps_only":
            steps, message = ["deps"], TRANSLATIONS[lang]["sk_confirm_deps"]
        elif key == "install_basic_no_picons":
            steps, message = ["channel_list", "install_oscam", "reload_settings"], TRANSLATIONS[lang]["sk_confirm_basic"]
        elif key == "install_with_picons":
            steps, message = ["channel_list", "picons", "install_oscam", "reload_settings"], TRANSLATIONS[lang]["sk_confirm_full"]

        if steps:
            original_option_text = TRANSLATIONS[lang].get(f"sk_option_{key}", "Wybrana opcja").split(') ')[-1]
            confirm_message = "Czy na pewno chcesz wykonać akcję:\n'{}'?\n\n(Zależności systemowe zostały już sprawdzone przy starcie wtyczki.)".format(original_option_text)
            
            if key == "deps_only":
                confirm_message = "Czy na pewno chcesz wykonać akcję:\n'{}'?".format(original_option_text)

            self.sess.openWithCallback(
                lambda confirmed: self._wizard_start(steps) if confirmed else None,
                MessageBox, confirm_message,
                type=MessageBox.TYPE_YESNO, title="Potwierdzenie operacji"
            )
            
    def _wizard_start(self, steps):
        channel_list_url, list_name, picon_url = '', 'domyślna lista', ''
        if "channel_list" in steps:
            repo_lists = self.fetched_data_cache.get("repo_lists", [])
            first_valid_list = next((item for item in repo_lists if item[1].startswith("archive:")), None) # Weź tylko listę typu "archive"
            
            if first_valid_list:
                try:
                    list_name = first_valid_list[0].split(' - ')[0]
                    action_str = first_valid_list[1]
                    if action_str.startswith("archive:"):
                        channel_list_url = action_str.split(':', 1)[1]
                except (IndexError, AttributeError): 
                    channel_list_url = '' 
            
            if not channel_list_url:
                s4a_lists = self.fetched_data_cache.get("s4a_lists_full", [])
                bzyk_list = next((item for item in s4a_lists if "bzyk83" in item[0].lower()), None)
                
                if bzyk_list:
                    first_valid_list = bzyk_list
                else:
                    first_valid_list = next((item for item in s4a_lists if item[1] != 'SEPARATOR'), None)

                if first_valid_list:
                    try:
                        list_name = first_valid_list[0].split(' - ')[0]
                        action_str = first_valid_list[1]
                        if action_str.startswith("archive:"):
                            channel_list_url = action_str.split(':', 1)[1]
                    except (IndexError, AttributeError): 
                        channel_list_url = ''

            if not channel_list_url:
                self.sess.open(MessageBox, "BŁĄD KRYTYCZNY: Nie udało się pobrać adresu ŻADNEJ listy kanałów typu 'archive'.", type=MessageBox.TYPE_ERROR); return
                
        if "picons" in steps:
            # Używamy nowej, podzielonej listy
            for name, action in (SYSTEM_TOOLS_PL):
                if name.startswith("Pobierz Picony"):
                    try: 
                        picon_url = action.split(':', 1)[1]; break
                    except (IndexError, AttributeError): 
                        picon_url = ''
            if not picon_url:
                self.sess.open(MessageBox, "Nie udało się odnaleźć adresu picon.", type=MessageBox.TYPE_ERROR); return
        
        self.sess.open(WizardProgressScreen, steps=steps, channel_list_url=channel_list_url, channel_list_name=list_name, picon_url=picon_url)

# === KONIEC KLASY PANEL ===


# === DEFINICJA WTYCZKI ===
def main(session, **kwargs):
    session.open(AIOLoadingScreen)

def Plugins(**kwargs):
    return [PluginDescriptor(name="AIO Panel", description="Panel All-In-One by Paweł Pawełek (v{})".format(VER), where=PluginDescriptor.WHERE_PLUGINMENU, icon="logo.png", fnc=main)]
