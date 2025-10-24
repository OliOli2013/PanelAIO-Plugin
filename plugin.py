# -*- coding: utf-8 -*-
"""
Panel AIO
by Paweł Pawełek | msisystem@t.pl
Wersja 2.4 (stabilność aktualizacji v5 - info w konsoli)
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
    network = iNetworkInformation() # Dla nowszych obrazów
except ImportError:
    network = None
    try:
        from Components.Network import Network # Dla starszych obrazów
        iNetworkInfo = Network()
    except ImportError:
        iNetworkInfo = None # Jeśli żaden nie działa

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

# === SEKCJA GLOBALNYCH ZMIENNYCH ===
PLUGIN_PATH = os.path.dirname(os.path.realpath(__file__))
PLUGIN_TMP_PATH = "/tmp/PanelAIO/"
PLUGIN_ICON_PATH = os.path.join(PLUGIN_PATH, "logo.png")
PLUGIN_SELECTION_PATH = os.path.join(PLUGIN_PATH, "selection.png")
PLUGIN_QR_CODE_PATH = os.path.join(PLUGIN_PATH, "Kod_QR_buycoffee.png")
VER = "2.4"
DATE = str(datetime.date.today())
FOOT = "AIO {} | {} | by Paweł Pawełek | msisystem@t.pl".format(VER, DATE)

LEGEND_PL = r"\c00ff0000●\c00ffffff PL \c0000ff00●\c00ffffff EN \c00ffff00●\c00ffffff Restart GUI \c000000ff●\c00ffffff Aktualizuj"
LEGEND_EN = r"\c00ff0000●\c00ffffff PL \c0000ff00●\c00ffffff EN \c00ffff00●\c00ffffff Restart GUI \c000000ff●\c00ffffff Update"

# === SEKCJA TŁUMACZEń ===
TRANSLATIONS = {
    "PL": {
        "support_text": "Wesprzyj rozwój wtyczki",
        "update_available_title": "Dostępna nowa wersja!",
        "update_available_msg": """Dostępna jest nowa wersja AIO Panel: {latest_ver}
Twoja wersja: {current_ver}

Lista zmian:
{changelog}
Czy chcesz ją teraz zainstalować?""",
        "already_latest": "Używasz najnowszej wersji wtyczki ({ver}).",
        "update_check_error": "Nie można sprawdzić dostępności aktualizacji.\nSprawdź połączenie z internetem.",
        "update_generic_error": "Wystąpił błąd podczas sprawdzania aktualizacji.",
        "loading_text": "Ładowanie...",
        "loading_error_text": "Błąd wczytywania danych",
        "sk_wizard_title": "Super Konfigurator (Pierwsza Instalacja)",
        "sk_choice_title": "Super Konfigurator - Wybierz opcję",
        "sk_option_deps": "1) Zainstaluj tylko zależności (wget, tar, unzip)",
        "sk_option_basic_no_picons": "2) Podstawowa Konfiguracja (bez Picon)",
        "sk_option_full_picons": "3) Pełna Konfiguracja (z Piconami)",
        "sk_option_cancel": "Anuluj",
        "sk_confirm_deps": "Czy na pewno chcesz zainstalować tylko podstawowe zależności systemowe?",
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
Do you want to install it now?""",
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
# === KONIEC SEKCJI ===

# === FUNKCje POMOCNICZE ===
def show_message_compat(session, message, message_type=MessageBox.TYPE_INFO, timeout=10, on_close=None):
    # Używamy callLater, aby uniknąć problemów z modalnością
    reactor.callLater(0.2, lambda: session.openWithCallback(on_close, MessageBox, message, message_type, timeout=timeout))

def console_screen_open(session, title, cmds_with_args, callback=None, close_on_finish=False):
    cmds_list = cmds_with_args if isinstance(cmds_with_args, list) else [cmds_with_args]
    # Używamy callLater (nawet z minimalnym opóźnieniem), aby dać pętli zdarzeń szansę
    # na przetworzenie zamknięcia poprzedniego okna przed otwarciem konsoli.
    def open_console():
        try:
            # Dla aktualizacji *nie* ustawiamy callbacku
            effective_callback = None if title == "Aktualizacja AIO Panel..." else callback
            c_dialog = session.open(Console, title, cmds_list, closeOnSuccess=close_on_finish)
            if effective_callback:
                c_dialog.onClose.append(effective_callback)

        except Exception as e:
            print("[AIO Panel] Błąd otwierania konsoli:", e)
            show_message_compat(session, "Błąd podczas uruchamiania konsoli:\n{}".format(e), MessageBox.TYPE_ERROR)
            # Jeśli był callback (i nie była to aktualizacja), spróbuj go wywołać
            if callback and title != "Aktualizacja AIO Panel...":
                try: callback()
                except: pass
    reactor.callLater(0.1, open_console)


def prepare_tmp_dir():
    if not os.path.exists(PLUGIN_TMP_PATH):
        try:
            os.makedirs(PLUGIN_TMP_PATH)
        except OSError as e:
            print("[AIO Panel] Error creating tmp dir:", e)

def install_archive(session, title, url, callback_on_finish=None):
    if not url.endswith((".zip", ".tar.gz", ".tgz", ".ipk")):
        show_message_compat(session, "Nieobsługiwany format archiwum!", message_type=MessageBox.TYPE_ERROR)
        if callback_on_finish: callback_on_finish()
        return
    archive_type = "zip" if url.endswith(".zip") else ("tar.gz" if url.endswith((".tar.gz", ".tgz")) else "ipk")
    prepare_tmp_dir()
    tmp_archive_path = os.path.join(PLUGIN_TMP_PATH, os.path.basename(url))
    download_cmd = "wget --no-check-certificate -O \"{}\" \"{}\"".format(tmp_archive_path, url)

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
        install_script_path = os.path.join(PLUGIN_PATH, "install_archive_script.sh")
        # Sprawdzenie czy plik istnieje, bo może go nie być
        if not fileExists(install_script_path):
             show_message_compat(session, "Brak pliku install_archive_script.sh!", message_type=MessageBox.TYPE_ERROR)
             if callback_on_finish: callback_on_finish()
             return
        chmod_cmd = "chmod +x \"{}\"".format(install_script_path)
        full_command = "{} && {} && {} \"{}\" \"{}\"".format(download_cmd, chmod_cmd, install_script_path, tmp_archive_path, archive_type)

    console_screen_open(session, title, [full_command], callback=callback_on_finish, close_on_finish=True)

def get_s4aupdater_lists_dynamic():
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

def get_best_oscam_version_info():
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
# === KONIEC FUNKCJI POMOCNICZYCH ===

# === DEFINICJE MENU ===
E2IPLAYER_INSTALL_CMD = "bash -c 'if ! opkg list-installed | grep -q ppanel; then echo \"Instalowanie zależności PPanel...\"; wget http://downloads.openpli.org/feeds/openpli-9-release/3rd-party/ppanel_2.2_all.ipk -P /tmp && opkg install /tmp/ppanel_2.2_all.ipk; fi && echo \"Uruchamianie głównego instalatora E2iPlayer...\"; wget -q \"https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh\" -O - | /bin/sh'"

SOFTCAM_AND_PLUGINS_PL = [
    ("--- Softcamy ---", "SEPARATOR"),
    ("Restart Oscam", "CMD:RESTART_OSCAM"),
    ("Kasuj hasło Oscam", "CMD:CLEAR_OSCAM_PASS"),
    ("oscam.dvbapi - zarządzaj", "CMD:MANAGE_DVBAPI"),
    ("Oscam z Feeda (Auto)", "CMD:INSTALL_BEST_OSCAM"),
    ("NCam 15.5", "bash_raw:wget https://raw.githubusercontent.com/biko-73/Ncam_EMU/main/installer.sh -O - | /bin/sh"),
    ("--- Wtyczki Online ---", "SEPARATOR"),
    ("XStreamity - Instalator", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-xstreamity"),
    ("ServiceApp - Instalator", "CMD:INSTALL_SERVICEAPP"),
    ("StreamlinkProxy - Instalator", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-streamlinkproxy"),
    ("AJPanel - Instalator", "bash_raw:wget https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh -O - | /bin/sh"),
    ("E2iPlayer Master - Instalacja/Aktualizacja", "bash_raw:" + E2IPLAYER_INSTALL_CMD),
    ("EPG Import - Instalator", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh -O - | /bin/bash"),
    ("S4aUpdater - Instalator", "bash_raw:wget http://s4aupdater.one.pl/instalujs4aupdater.sh -O - | /bin/sh"),
    ("JediMakerXtream - Instalator", "bash_raw:wget https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh -O - | /bin/sh"),
    ("YouTube - Instalator", "bash_raw:opkg install https://github.com/Taapat/enigma2-plugin-youtube/releases/download/git1294/enigma2-plugin-extensions-youtube_py3-git1294-cbcf8b0-r0.0.ipk"),
]

SOFTCAM_AND_PLUGINS_EN = [
    ("--- Softcams ---", "SEPARATOR"),
    ("Restart Oscam", "CMD:RESTART_OSCAM"),
    ("Clear Oscam Password", "CMD:CLEAR_OSCAM_PASS"),
    ("oscam.dvbapi - manage", "CMD:MANAGE_DVBAPI"),
    ("Oscam from Feed (Auto)", "CMD:INSTALL_BEST_OSCAM"),
    ("NCam 15.5", "bash_raw:wget https://raw.githubusercontent.com/biko-73/Ncam_EMU/main/installer.sh -O - | /bin/sh"),
    ("--- Online Plugins ---", "SEPARATOR"),
    ("XStreamity - Installer", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-xstreamity"),
    ("ServiceApp - Installer", "CMD:INSTALL_SERVICEAPP"),
    ("StreamlinkProxy - Installer", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-streamlinkproxy"),
    ("AJPanel - Installer", "bash_raw:wget https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh -O - | /bin/sh"),
    ("E2iPlayer Master - Install/Update", "bash_raw:" + E2IPLAYER_INSTALL_CMD),
    ("EPG Import - Installer", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh -O - | /bin/bash"),
    ("S4aUpdater - Installer", "bash_raw:wget http://s4aupdater.one.pl/instalujs4aupdater.sh -O - | /bin/sh"),
    ("JediMakerXtream - Installer", "bash_raw:wget https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh -O - | /bin/sh"),
    ("YouTube - Installer", "bash_raw:opkg install https://github.com/Taapat/enigma2-plugin-youtube/releases/download/git1294/enigma2-plugin-extensions-youtube_py3-git1294-cbcf8b0-r0.0.ipk"),
]

TOOLS_AND_ADDONS_PL = [
    ("--- Konfigurator ---", "SEPARATOR"),
    ("Super Konfigurator (Pierwsza Instalacja)", "CMD:SUPER_SETUP_WIZARD"),
    ("--- Narzędzia Systemowe ---", "SEPARATOR"),
    ("Aktualizacja Wtyczki", "CMD:CHECK_FOR_UPDATES"),
    ("Menadżer Deinstalacji", "CMD:UNINSTALL_MANAGER"),
    # ("Instalacja Softcam Feed", "CMD:INSTALL_SOFTCAM_FEED"), # USUNIĘTE
    ("Aktualizuj satellites.xml", "CMD:UPDATE_SATELLITES_XML"),
    ("Pobierz Picony (Transparent)", "archive:https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip"),
    ("Kasuj hasło FTP", "CMD:CLEAR_FTP_PASS"),
    ("Ustaw Hasło FTP", "CMD:SET_SYSTEM_PASSWORD"),
    ("--- Diagnostyka i Czyszczenie ---", "SEPARATOR"),
    ("Diagnostyka Sieci", "CMD:NETWORK_DIAGNOSTICS"),
    ("Wolne miejsce (dysk/flash)", "CMD:FREE_SPACE_DISPLAY"),
    ("Wyczyść Pamięć Tymczasową", "CMD:CLEAR_TMP_CACHE"),
    ("Wyczyść Pamięć RAM", "CMD:CLEAR_RAM_CACHE"),
]

TOOLS_AND_ADDONS_EN = [
    ("--- Configurator ---", "SEPARATOR"),
    ("Super Setup Wizard (First Installation)", "CMD:SUPER_SETUP_WIZARD"),
    ("--- System Tools ---", "SEPARATOR"),
    ("Update Plugin", "CMD:CHECK_FOR_UPDATES"),
    ("Uninstallation Manager", "CMD:UNINSTALL_MANAGER"),
    # ("Install Softcam Feed", "CMD:INSTALL_SOFTCAM_FEED"), # REMOVED
    ("Update satellites.xml", "CMD:UPDATE_SATELLITES_XML"),
    ("Download Picons (Transparent)", "archive:https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip"),
    ("Clear FTP Password", "CMD:CLEAR_FTP_PASS"),
    ("Set FTP Password", "CMD:SET_SYSTEM_PASSWORD"),
    ("--- Diagnostics & Cleaning ---", "SEPARATOR"),
    ("Network Diagnostics", "CMD:NETWORK_DIAGNOSTICS"),
    ("Free Space (disk/flash)", "CMD:FREE_SPACE_DISPLAY"),
    ("Clear Temporary Cache", "CMD:CLEAR_TMP_CACHE"),
    ("Clear RAM Cache", "CMD:CLEAR_RAM_CACHE"),
]

COL_TITLES = {"PL": ("Listy Kanałów", "Softcam i Wtyczki", "Narzędzia i Dodatki"), "EN": ("Channel Lists", "Softcam & Plugins", "Tools & Extras")}
# === KONIEC DEFINICJI MENU ===
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
        cmd = "opkg update; opkg install wget tar unzip --force-reinstall; exit 0"
        console_screen_open(self.session, title, [cmd], callback=self._wizard_run_next_step, close_on_finish=True)

    def _wizard_step_channel_list(self):
        title = self._get_wizard_title("Instalacja listy '{}'".format(self.wizard_channel_list_name))
        url = self.wizard_channel_list_url
        install_archive(self.session, title, url, callback=self._wizard_run_next_step)

    def _wizard_step_install_oscam(self):
        title = self._get_wizard_title("Instalacja Softcam Feed + Oscam")
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
        console_screen_open(self.session, title, [cmd], callback=self._wizard_run_next_step, close_on_finish=True)

    def _wizard_step_picons(self):
        title = self._get_wizard_title("Instalacja Picon (Transparent)")
        url = self.wizard_picon_url
        install_archive(self.session, title, url, callback=self._wizard_run_next_step)
        
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

class Panel(Screen):
    skin = """
    <screen name='PanelAIO' position='center,center' size='1260,680' title=' '>
        <widget name='qr_code_small' position='15,25' size='110,110' pixmap="{}" alphatest='blend' />
        <widget name="support_label" position="135,25" size="400,110" font="Regular;24" halign="left" valign="center" foregroundColor="green" />
        <widget name="title_label" position="630,25" size="615,40" font="Regular;32" halign="right" valign="center" transparent="1" />
        <widget name='headL' position='15,150'  size='500,30'  font='Regular;26' halign='center' foregroundColor='cyan' />
        <widget name='menuL' position='15,190'  size='500,410' itemHeight='40' font='Regular;22' scrollbarMode='showOnDemand' selectionPixmap='selection.png'/>
        <widget name='headM' position='530,150' size='350,30'  font='Regular;26' halign='center' foregroundColor='cyan' />
        <widget name='menuM' position='530,190'  size='350,410' itemHeight='40' font='Regular;22' scrollbarMode='showOnDemand' selectionPixmap='selection.png'/>
        <widget name='headR' position='895,150' size='350,30'  font='Regular;26' halign='center' foregroundColor='cyan' />
        <widget name='menuR' position='895,190'  size='350,410' itemHeight='40' font='Regular;22' scrollbarMode='showOnDemand' selectionPixmap='selection.png'/>
        <widget name='legend' position='15,620'  size='1230,28'  font='Regular;20' halign='center'/>
        <widget name='footer' position='center,645' size='1230,28' font='Regular;16' halign='center' foregroundColor='lightgrey'/>
        <widget name="loading_label" position="center,center" size="800,300" font="Regular;32" halign="center" valign="center" transparent="1" zPosition="10" />
    </screen>""".format(PLUGIN_QR_CODE_PATH)

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle(" ")
        self.sess, self.col, self.lang, self.data = session, 'L', 'PL', ([],[],[])
        self["qr_code_small"] = Pixmap()
        self["support_label"] = Label(TRANSLATIONS[self.lang]["support_text"])
        self["title_label"] = Label("AIO Panel " + VER)
        for name in ("headL", "headM", "headR", "legend", "loading_label"): self[name] = Label()
        for name in ("menuL", "menuM", "menuR"): self[name] = MenuList([])
        self["footer"] = Label(FOOT)
        self["act"] = ActionMap(["DirectionActions", "OkCancelActions", "ColorActions", "InfoActions"], {
            "ok": self.run_with_confirmation,
            "cancel": self.close,
            "red": lambda: self.set_language('PL'),
            "green": lambda: self.set_language('EN'),
            "yellow": self.restart_gui,
            "blue": self.check_for_updates_manual,
            "info": self.close,
            "up": lambda: self._menu().instance.moveSelection(self._menu().instance.moveUp),
            "down": lambda: self._menu().instance.moveSelection(self._menu().instance.moveDown),
            "left": self.left,
            "right": self.right
        }, -1)
        self.onShown.append(self.initial_setup)
        self.update_info = None
        self.data_loaded = False
        self.fetched_data_cache = None
        self.update_prompt_shown = False
        self.wait_message_box = None

    def initial_setup(self):
        reactor.callLater(0.2, self.check_dependencies)
        
    def check_dependencies(self):
        try:
            from shutil import which
        except ImportError:
            def which(cmd):
                path = os.getenv('PATH')
                for p in path.split(os.path.pathsep):
                    p = os.path.join(p, cmd)
                    if os.path.exists(p) and os.access(p, os.X_OK):
                        return p
                return None
        required_packages = ['curl', 'tar', 'unzip']
        missing_packages = [pkg for pkg in required_packages if not which(pkg)]
        if not missing_packages:
            self.load_plugin_data()
            return
        install_cmds = [
            "echo 'Wykryto brakujące pakiety. Rozpoczynam automatyczną instalację...'",
            "opkg update",
            "opkg install " + " ".join(missing_packages),
            "echo 'Instalacja komponentów zakończona! Zalecany restart GUI.'",
            "sleep 5"
        ]
        console_screen_open(self.sess, "Pierwsze uruchomienie: Instalacja zależności", install_cmds, callback=self.on_dependencies_installed_safe, close_on_finish=True)

    def on_dependencies_installed_safe(self, *args):
        self.load_plugin_data()

    def load_plugin_data(self):
        # Pokaż ekran ładowania i ukryj menu
        self["loading_label"].setText(TRANSLATIONS[self.lang]["loading_text"])
        self["loading_label"].show()
        for name in ("menuL", "menuM", "menuR", "headL", "headM", "headR"): self[name].hide()
        
        # Uruchom pobieranie danych w osobnym wątku
        thread = Thread(target=self._fetch_all_data_thread, args=(self.lang,))
        thread.start()

    def _fetch_all_data_thread(self, lang):
        # Ta funkcja działa w tle
        fetched_data = {}
        try:
            fetched_data['repo_lists'] = self.get_lists_from_repo()
        except Exception as e:
            print("[AIO Panel] Błąd pobierania list repo:", e)
            fetched_data['repo_lists'] = [(TRANSLATIONS[lang]["loading_error_text"], "SEPARATOR")]
        try:
            fetched_data['s4a_lists_full'] = get_s4aupdater_lists_dynamic()
        except Exception as e:
            print("[AIO Panel] Błąd pobierania list S4a:", e)
            fetched_data['s4a_lists_full'] = []
        try:
            fetched_data['best_oscam_version'] = get_best_oscam_version_info()
        except Exception as e:
            print("[AIO Panel] Błąd pobierania wersji Oscam:", e)
            fetched_data['best_oscam_version'] = "Error"
        
        # Wywołaj funkcję w głównym wątku, aby zaktualizować GUI
        reactor.callFromThread(self._on_data_fetched, lang, fetched_data)

    def _on_data_fetched(self, lang, fetched_data):
        # Ta funkcja działa w głównym wątku
        self["loading_label"].hide()
        self.data_loaded = True # Ustaw flagę, że dane załadowane
        
        repo_lists = fetched_data['repo_lists']
        s4a_lists_full = fetched_data['s4a_lists_full']
        best_oscam_version = fetched_data['best_oscam_version']
        
        keywords_to_remove = ['bzyk', 'jakitaki']
        s4a_lists_filtered = [item for item in s4a_lists_full if not any(keyword in item[0].lower() for keyword in keywords_to_remove)]
        final_channel_lists = repo_lists + s4a_lists_filtered
        
        softcam_menu = list(SOFTCAM_AND_PLUGINS_PL if lang == 'PL' else SOFTCAM_AND_PLUGINS_EN)
        tools_menu = list(TOOLS_AND_ADDONS_PL if lang == 'PL' else TOOLS_AND_ADDONS_EN)

        for i, (name, action) in enumerate(softcam_menu):
            if action == "CMD:INSTALL_BEST_OSCAM":
                oscam_text = "Oscam z Feeda ({})" if lang == 'PL' else "Oscam from Feed ({})"
                softcam_menu[i] = (oscam_text.format(best_oscam_version), action)
        
        for i, (name, action) in enumerate(tools_menu):
            if action == "CMD:SUPER_SETUP_WIZARD":
                tools_menu[i] = (TRANSLATIONS[lang]["sk_wizard_title"], action)

        self.data = (final_channel_lists, softcam_menu, tools_menu)
        self.set_lang_headers_and_legends()
        self.populate_menus()
        
        # Pokaż menu
        for name in ("menuL", "menuM", "menuR", "headL", "headM", "headR"): self[name].show()

        self._focus()
        
        # Sprawdź aktualizacje PO załadowaniu interfejsu
        if not self.update_prompt_shown: # Sprawdź tylko przy pierwszym załadowaniu
             # Opóźnienie, aby uniknąć kolizji z ładowaniem danych
            reactor.callLater(1.5, self.check_for_updates_on_start)

    def check_for_updates_on_start(self):
        # Sprawdź tylko raz przy starcie, a nie przy każdej zmianie języka
        if self.update_prompt_shown:
            return
        self.update_prompt_shown = True # Ustaw flagę
        thread = Thread(target=self.fetch_update_info_in_background)
        thread.start()

    def fetch_update_info_in_background(self):
        try:
            update_info = self.perform_update_check_silent()
            if update_info:
                # Wywołaj ask_for_update w głównym wątku
                reactor.callFromThread(self.ask_for_update, update_info)
        except Exception as e:
            print("[AIO Panel] Błąd automatycznego sprawdzania aktualizacji:", e)
            
    def set_language(self, lang):
        self.lang = lang
        self.data_loaded = False # Resetuj flagę przed ładowaniem
        self.load_plugin_data() # Użyj nowej, wątkowej metody ładowania
        
    def set_lang_headers_and_legends(self):
        for i, head_widget in enumerate((self["headL"], self["headM"], self["headR"])):
            head_widget.setText(COL_TITLES[self.lang][i])
        self["legend"].setText(LEGEND_PL if self.lang == 'PL' else LEGEND_EN)
        self["support_label"].setText(TRANSLATIONS[self.lang]["support_text"])
        
    def populate_menus(self):
        for i, menu_widget in enumerate((self["menuL"], self["menuM"], self["menuR"])):
            data_list = self.data[i]
            if data_list:
                menu_widget.setList([str(item[0]) for item in data_list])
            else:
                 # Wyświetl błąd tylko jeśli dane *już* zostały załadowane (uniknięcie migotania)
                 if self.data_loaded:
                    menu_widget.setList([(TRANSLATIONS[self.lang]["loading_error_text"],)])
                 else:
                     menu_widget.setList([]) # Pusta lista podczas ładowania


    def _clean_version(self, v):
        # Wyszukuje pierwszy znak, który nie jest cyfrą ani kropką, i obcina resztę
        match = re.search(r'[^0-9.]', v)
        if match:
            v = v[:match.start()]
        return v.strip('.')

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
            # Używamy subprocess.call dla pewności, że komendy się zakończą
            subprocess.call(cmd_ver, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.call(cmd_log, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if os.path.exists(tmp_version_path) and os.path.getsize(tmp_version_path) > 0:
                with open(tmp_version_path, 'r') as f:
                    latest_ver_str = f.read().strip()
                
                if not latest_ver_str:
                    print("[AIO Panel] Pobrany plik version.txt jest pusty.")
                    return None
                    
                # === NOWA LOGIKA PORÓWNYWANIA WERSJI ===
                clean_ver = self._clean_version(VER)
                clean_latest_ver = self._clean_version(latest_ver_str)
                
                is_update = False
                try:
                    # Dodatkowe zabezpieczenie przed pustymi stringami po czyszczeniu
                    if not clean_ver or not clean_latest_ver:
                         raise ValueError("Jedna z wersji jest pusta po czyszczeniu")
                         
                    current_ver_tuple = tuple(map(int, (clean_ver.split('.'))))
                    latest_ver_tuple = tuple(map(int, (clean_latest_ver.split('.'))))
                    
                    # Sprawdź czy wersja na serwerze jest > niż lokalna
                    if latest_ver_tuple > current_ver_tuple:
                        is_update = True
                except (ValueError, TypeError) as e:
                     print("[AIO Panel] Błąd parsowania wersji: {} vs {} ({} vs {}). Błąd: {}. Używam prostego porównania.".format(VER, latest_ver_str, clean_ver, clean_latest_ver, e))
                     # Fallback do prostego porównania, jeśli parsowanie zawiedzie LUB wersje są puste
                     if latest_ver_str != VER and latest_ver_str: # Sprawdź też czy latest_ver_str nie jest pusty
                        is_update = True
                         
                if is_update:
                    print("[AIO Panel] Znaleziono nową wersję: {} (bieżąca: {})".format(latest_ver_str, VER))
                    changelog_text = "Brak informacji o zmianach."
                    if os.path.exists(tmp_changelog_path) and os.path.getsize(tmp_changelog_path) > 0:
                        try:
                            with open(tmp_changelog_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                            found_version_section, changes = False, []
                            # Użyj oryginalnego stringu z pliku version.txt do znalezienia sekcji w changelogu
                            search_tag = "[{}]".format(latest_ver_str)
                            for line in lines:
                                line = line.strip()
                                if line == search_tag:
                                    found_version_section = True
                                    continue
                                if found_version_section:
                                    if line.startswith("[") and line.endswith("]"): break # Następna sekcja wersji
                                    if line: changes.append(line)
                            if changes: changelog_text = "\n".join(changes)
                        except Exception as e:
                             print("[AIO Panel] Błąd odczytu changelog.txt:", e)
                    # Zwróć oryginalny string z pliku version.txt
                    return {'latest_ver': latest_ver_str, 'changelog': changelog_text}
                else:
                    print("[AIO Panel] Brak nowej wersji ({} <= {}).".format(latest_ver_str, VER))
                    
            else:
                 print("[AIO Panel] Nie udało się pobrać pliku version.txt lub jest pusty.")

        except Exception as e:
            print("[AIO Panel] Silent update check failed (Exception):", e)
        return None

    def check_for_updates_manual(self):
        info = self.perform_update_check_silent()
        if info:
            self.ask_for_update(info)
        else:
            show_message_compat(self.sess, TRANSLATIONS[self.lang]["already_latest"].format(ver=VER))

    def ask_for_update(self, update_info):
        if not update_info: return
        # Nie ustawiamy tutaj flagi update_prompt_shown, aby ręczne sprawdzenie działało zawsze
        self.update_info = update_info
        message = TRANSLATIONS[self.lang]["update_available_msg"].format(
            latest_ver=update_info['latest_ver'],
            current_ver=VER,
            changelog=update_info['changelog']
        )
        # Używamy callLater, aby uniknąć problemów z modalnością
        reactor.callLater(0.2, lambda: self.sess.openWithCallback(
            self.do_update, MessageBox, message,
            type=MessageBox.TYPE_YESNO
        ))

    def do_update(self, confirmed):
        if confirmed:
            # Użyjemy reactor.callLater z większym opóźnieniem dla bezpieczeństwa
            reactor.callLater(0.5, self._start_update_console)
        else:
            self.update_info = None

    def _start_update_console(self):
        # Komenda aktualizacji z wyraźnymi komunikatami w konsoli i bez automatycznego zamykania
        update_cmd = (
            'echo "[AIO] Rozpoczynam aktualizację z GitHub..."; '
            'echo "[AIO] Pobieram installer.sh..."; '
            'wget "--no-check-certificate" https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh -O - '
            '| /bin/sh; '
            'RET=$?; echo "[AIO] Kod zakończenia: $RET"; '
            'echo "-----------------------------------------------------"; '
            'echo " AKTUALIZACJA ZAKOŃCZONA."; '
            'echo ""; '
            'echo " ABY ZMIANY WESZŁY W ŻYCIE,"; '
            'echo " WYMAGANY JEST RESTART INTERFEJSU GUI"; '
            'echo " (użyj ŻÓŁTEGO przycisku w Panelu AIO)"; '
            'echo ""; '
            'echo " NACIŚNIJ OK LUB EXIT, ABY ZAMKNĄĆ TĘ KONSOLĘ"; '
            'echo "-----------------------------------------------------"'
        )
        # Otwieramy konsolę bez callbacku i BEZ auto-zamykania (użytkownik zamyka OK/EXIT)
        console_screen_open(self.sess, "Aktualizacja AIO Panel...", [update_cmd], callback=None, close_on_finish=False)
        # Usunęliśmy wywołanie show_manual_restart_after_update_info stąd

    # Usunęliśmy funkcję show_manual_restart_after_update_info
    
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
            steps, message = ["deps", "channel_list", "install_oscam", "reload_settings"], TRANSLATIONS[lang]["sk_confirm_basic"]
        elif key == "install_with_picons":
            steps, message = ["deps", "channel_list", "install_oscam", "picons", "reload_settings"], TRANSLATIONS[lang]["sk_confirm_full"]

        if steps:
            self.sess.openWithCallback(
                lambda confirmed: self._wizard_start(steps) if confirmed else None,
                MessageBox, message, type=MessageBox.TYPE_YESNO, title="Potwierdzenie operacji"
            )
            
    def _wizard_start(self, steps):
        channel_list_url, list_name, picon_url = '', 'domyślna lista', ''
        if "channel_list" in steps:
            # Upewnij się, że lista jest pobierana ponownie, a nie z cache
            try:
                repo_lists = self.get_lists_from_repo()
            except Exception as e:
                print("[AIO Panel] Błąd pobierania list w _wizard_start:", e)
                self.sess.open(MessageBox, "Nie udało się pobrać listy dostępnych list kanałów.", type=MessageBox.TYPE_ERROR); return

            if repo_lists and repo_lists[0][1] != 'SEPARATOR':
                try:
                    list_name = repo_lists[0][0].split(' - ')[0]
                    channel_list_url = repo_lists[0][1].split(':', 1)[1]
                except (IndexError, AttributeError): channel_list_url = ''
            if not channel_list_url:
                self.sess.open(MessageBox, "Nie udało się pobrać adresu domyślnej listy kanałów.", type=MessageBox.TYPE_ERROR); return
        if "picons" in steps:
            # Szukaj w aktualnej liście menu (PL lub EN)
            current_tools_menu = TOOLS_AND_ADDONS_PL if self.lang == 'PL' else TOOLS_AND_ADDONS_EN
            for name, action in current_tools_menu:
                 # Bardziej elastyczne dopasowanie nazwy
                if ("picon" in name.lower() or "picony" in name.lower()) and action.startswith("archive:"):
                    try: picon_url = action.split(':', 1)[1]; break
                    except (IndexError, AttributeError): picon_url = ''
            if not picon_url:
                self.sess.open(MessageBox, "Nie udało się odnaleźć adresu picon.", type=MessageBox.TYPE_ERROR); return
        self.sess.open(WizardProgressScreen, steps=steps, channel_list_url=channel_list_url, channel_list_name=list_name, picon_url=picon_url)


    def run_with_confirmation(self):
        try:
            name, action = self.data[{'L':0,'M':1,'R':2}[self.col]][self._menu().getSelectedIndex()]
        except (IndexError, KeyError, TypeError): return
        if action == "SEPARATOR": return
        actions_no_confirm = ["CMD:NETWORK_DIAGNOSTICS", "CMD:FREE_SPACE_DISPLAY", "CMD:UNINSTALL_MANAGER", "CMD:MANAGE_DVBAPI", "CMD:CHECK_FOR_UPDATES", "CMD:SUPER_SETUP_WIZARD", "CMD:UPDATE_SATELLITES_XML", "CMD:INSTALL_SERVICEAPP"]
        if any(action.startswith(prefix) for prefix in actions_no_confirm):
            self.execute_action(name, action)
        else:
             # Użyj callLater dla MessageBox potwierdzenia
             reactor.callLater(0.1, lambda: self.sess.openWithCallback(
                lambda ret: self.execute_action(name, action) if ret else None,
                MessageBox, "Czy na pewno chcesz wykonać akcję:\n'{}'?".format(name), type=MessageBox.TYPE_YESNO
             ))
    
    def execute_action(self, name, action):
        title = name
        # Zdefiniuj callback, który zostanie wywołany po zamknięciu konsoli (poza aktualizacją)
        post_install_callback = lambda: self.show_manual_restart_message(name)

        if action.startswith("bash_raw:"):
            console_screen_open(self.sess, title, [action.split(':', 1)[1]], callback=post_install_callback, close_on_finish=True)
        elif action.startswith("archive:"):
            # Dla list kanałów używamy innego callbacku
             if "picon" not in title.lower(): # Zakładamy, że reszta to listy
                 install_archive(self.sess, title, action.split(':', 1)[1], callback_on_finish=self.reload_settings_python)
             else: # Dla piconów tylko pokazujemy wiadomość
                 install_archive(self.sess, title, action.split(':', 1)[1], callback_on_finish=lambda: show_message_compat(self.sess, "Picony zainstalowane.", timeout=5))
        elif action.startswith("CMD:"):
            command_key = action.split(':', 1)[1]
            if command_key == "SUPER_SETUP_WIZARD": self.run_super_setup_wizard()
            elif command_key == "CHECK_FOR_UPDATES": self.check_for_updates_manual()
            elif command_key == "NETWORK_DIAGNOSTICS": self.run_network_diagnostics()
            elif command_key == "UPDATE_SATELLITES_XML":
                script_path = os.path.join(PLUGIN_PATH, "update_satellites_xml.sh")
                 # Sprawdzenie czy plik istnieje
                if not fileExists(script_path):
                     show_message_compat(self.sess, "Brak pliku update_satellites_xml.sh!", message_type=MessageBox.TYPE_ERROR); return
                console_screen_open(self.sess, title, ["bash " + script_path], callback=self.reload_settings_python, close_on_finish=True)
            elif command_key == "INSTALL_SERVICEAPP":
                cmd = "opkg update && opkg install enigma2-plugin-systemplugins-serviceapp exteplayer3 gstplayer && opkg install uchardet --force-reinstall"
                console_screen_open(self.sess, title, [cmd], callback=post_install_callback, close_on_finish=True)
            elif command_key == "INSTALL_BEST_OSCAM":
                self.install_best_oscam(callback=post_install_callback, close_on_finish=True)
            elif command_key == "MANAGE_DVBAPI": self.manage_dvbapi()
            elif command_key == "UNINSTALL_MANAGER": self.show_uninstall_manager()
            elif command_key == "CLEAR_OSCAM_PASS": self.clear_oscam_password()
            elif command_key == "CLEAR_FTP_PASS": self.clear_ftp_password()
            elif command_key == "SET_SYSTEM_PASSWORD": self.set_system_password()
            elif command_key == "RESTART_OSCAM": self.restart_oscam()
            elif command_key == "FREE_SPACE_DISPLAY": self.show_free_space()
            elif command_key == "CLEAR_TMP_CACHE": console_screen_open(self.sess, title, ["rm -rf " + PLUGIN_TMP_PATH + "*"], close_on_finish=True)
            elif command_key == "CLEAR_RAM_CACHE": console_screen_open(self.sess, title, ["sync; echo 3 > /proc/sys/vm/drop_caches"], close_on_finish=True)

    def run_network_diagnostics(self):
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
                wget -O "{script_path}" https://raw.githubusercontent.com/sivel/speedtest-cli/master/speedtest.py &>/dev/null
                chmod +x "{script_path}"
            fi
            
            # Poprawka dla Pythona 3 (ignorowanie ostrzeżeń)
            python3 -W ignore "{script_path}" --simple > "{output_file}" 2>/dev/null || python -W ignore "{script_path}" --simple > "{output_file}" 2>/dev/null
            EXIT_CODE=$?
            
            if [ $EXIT_CODE -eq 0 ] && [ -s "{output_file}" ]; then
                PING_SPEEDTEST=$(grep 'Ping:' "{output_file}" | awk '{{print $2" "$3}}' || echo "{na}")
                DOWNLOAD_SPEED=$(grep 'Download:' "{output_file}" | awk '{{print $2" "$3}}' || echo "{na}")
                UPLOAD_SPEED=$(grep 'Upload:' "{output_file}" | awk '{{print $2" "$3}}' || echo "{na}")
            else
                echo " "
                echo "*** {error_msg} (kod: $EXIT_CODE) ***"
                PING_SPEEDTEST="{na}"
                DOWNLOAD_SPEED="{na}"
                UPLOAD_SPEED="{na}"
            fi
            
            rm -f "{output_file}" "{script_path}" # Czyścimy też skrypt

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
        
    def _menu(self):
        return {'L':self["menuL"], 'M':self["menuM"], 'R':self["menuR"]}[self.col]

    def _focus(self):
        self["menuL"].selectionEnabled(self.col=='L'); self["menuM"].selectionEnabled(self.col=='M')
        self["menuR"].selectionEnabled(self.col=='R')

    def left(self): self.col = {'M':'L','R':'M'}.get(self.col,self.col); self._focus()
    def right(self): self.col = {'L':'M','M':'R'}.get(self.col,self.col); self._focus()
    def restart_gui(self): self.sess.open(TryQuitMainloop, 3)
    
    def show_manual_restart_message(self, name_unused=None, *args): # Dodano name_unused i *args
        message = "Operacja zakończona.\n\nAby zmiany odniosły skutek, zrestartuj GUI (żółty przycisk)."
        # Używamy bezpiecznego show_message_compat
        show_message_compat(self.sess, message, timeout=10)

    def reload_settings_python(self, *args):
        try:
            db = eDVBDB.getInstance()
            db.reloadServicelist()
            db.reloadBouquets()
            message = "Lista kanałów została przeładowana.\nZalecany restart GUI (żółty przycisk)."
            show_message_compat(self.sess, message, timeout=8)
        except Exception as e:
            print("[AIO Panel] Błąd podczas przeładowywania list:", e)
            show_message_compat(self.sess, "Wystąpił błąd podczas przeładowywania list.", message_type=MessageBox.TYPE_ERROR)

    # Usunięto install_softcam_feed
    
    def clear_oscam_password(self):
        cmd_find = "find /etc/tuxbox/config -name oscam.conf -exec dirname {} \\; | sort -u"
        try:
            process = subprocess.Popen(cmd_find, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            config_dirs = [line.strip() for line in stdout.decode('utf-8').splitlines() if line.strip()]
            if not config_dirs: config_dirs.append("/etc/tuxbox/config") # Domyślna ścieżka
            
            # Dodaj /etc/tuxbox/config jeśli nie znaleziono nic innego, a istnieje
            if not config_dirs and os.path.isdir("/etc/tuxbox/config"):
                config_dirs.append("/etc/tuxbox/config")
                
            found = False
            modified = False # Flaga czy cokolwiek zmieniono
            for d in config_dirs:
                conf_path = os.path.join(d, "oscam.conf")
                if fileExists(conf_path):
                    found = True # Znaleziono przynajmniej jeden plik oscam.conf
                    try:
                        with open(conf_path, "r", encoding='utf-8', errors='ignore') as f: lines = f.readlines()
                        # Używamy re do bardziej elastycznego sprawdzania httppwd
                        new_lines = [line for line in lines if not re.match(r"^\s*httppwd\s*=", line.strip(), re.IGNORECASE)]
                        if len(new_lines) < len(lines):
                            with open(conf_path, "w", encoding='utf-8', errors='ignore') as f: f.writelines(new_lines)
                            modified = True
                            print("[AIO Panel] Usunięto httppwd z:", conf_path)
                    except Exception as e:
                         print("[AIO Panel] Błąd przetwarzania {}: {}".format(conf_path, e))

            if modified:
                show_message_compat(self.sess, "Hasło Oscam WebIf zostało skasowane.")
                # Dodatkowo restartujemy Oscama po zmianie
                self.restart_oscam()
            elif found:
                 show_message_compat(self.sess, "Nie znaleziono linii 'httppwd' w plikach oscam.conf.")
            else:
                show_message_compat(self.sess, "Nie znaleziono pliku oscam.conf w oczekiwanych lokalizacjach.")
        except Exception as e:
            show_message_compat(self.sess, "Błąd podczas kasowania hasła Oscam: {}".format(e), message_type=MessageBox.TYPE_ERROR)


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
        # Bardziej rozbudowana komenda bash dla pewności
        cmd = '''
URL="{url}"
echo "Szukam katalogów konfiguracyjnych Oscam..."
CONFIG_DIRS=$(find /etc/tuxbox/config /usr/keys /var/keys -maxdepth 2 -name oscam.conf -exec dirname {{}} \\; 2>/dev/null | sort -u)

# Dodaj domyślne ścieżki, jeśli istnieją, a nie zostały znalezione przez find
for DPATH in /etc/tuxbox/config /usr/keys /var/keys; do
    if [ -d "$DPATH" ] && ! echo "$CONFIG_DIRS" | grep -q "$DPATH"; then
        CONFIG_DIRS="$CONFIG_DIRS"$'\n'"$DPATH"
    fi
done

# Jeśli nadal nic, użyj /etc/tuxbox/config jako absolutnego fallbacku
if [ -z "$CONFIG_DIRS" ]; then
    echo "Nie znaleziono istniejących konfiguracji, używam /etc/tuxbox/config"
    CONFIG_DIRS="/etc/tuxbox/config"
    mkdir -p "$CONFIG_DIRS" # Utwórz, jeśli nie istnieje
fi

echo "Przetwarzam katalogi:"
echo "$CONFIG_DIRS"
echo ""

SUCCESS=0
for DIR in $CONFIG_DIRS; do
    if [ -z "$DIR" ]; then continue; fi
    echo "Próba w katalogu: $DIR"
    DVBAPI_PATH="$DIR/oscam.dvbapi"
    DVBAPI_BAK="$DIR/oscam.dvbapi.bak"
    DVBAPI_TMP="$DIR/oscam.dvbapi.tmp"
    
    # Kopia zapasowa, jeśli plik istnieje
    if [ -f "$DVBAPI_PATH" ]; then
        echo "   Tworzę kopię zapasową: $DVBAPI_BAK"
        cp "$DVBAPI_PATH" "$DVBAPI_BAK"
    fi
    
    echo "   Pobieram plik z URL..."
    wget -q --no-check-certificate --timeout=30 -O "$DVBAPI_TMP" "$URL"
    WGET_RET=$?
    
    if [ $WGET_RET -eq 0 ] && [ -s "$DVBAPI_TMP" ]; then
        echo "   Pobieranie udane. Sprawdzam zawartość..."
        # Bardziej liberalne sprawdzenie - czy plik nie jest HTMLem i ma > 10 znaków
        if ! grep -qi '<html' "$DVBAPI_TMP" && [ $(wc -c < "$DVBAPI_TMP") -gt 10 ]; then
            echo "   Zawartość wygląda OK. Zastępuję plik."
            mv "$DVBAPI_TMP" "$DVBAPI_PATH"
            rm -f "$DVBAPI_BAK" # Usuń backup jeśli się udało
            SUCCESS=1
        else
            echo "   BŁĄD: Pobrany plik wygląda na nieprawidłowy (np. HTML) lub jest za krótki."
            rm -f "$DVBAPI_TMP"
            # Przywróć backup, jeśli istniał
            if [ -f "$DVBAPI_BAK" ]; then mv "$DVBAPI_BAK" "$DVBAPI_PATH"; fi
        fi
    else
        echo "   BŁĄD: Pobieranie nie powiodło się (kod: $WGET_RET) lub plik jest pusty."
        rm -f "$DVBAPI_TMP"
        # Przywróć backup, jeśli istniał
        if [ -f "$DVBAPI_BAK" ]; then mv "$DVBAPI_BAK" "$DVBAPI_PATH"; fi
    fi
    echo ""
done

if [ $SUCCESS -eq 1 ]; then
    echo "Plik oscam.dvbapi został zaktualizowany."
    echo "Restartuję Oscam..."
    for i in softcam.oscam oscam softcam; do
        INIT_SCRIPT="/etc/init.d/$i"
        if [ -f "$INIT_SCRIPT" ]; then
            echo "   Znaleziono skrypt: $INIT_SCRIPT. Restartuję..."
            $INIT_SCRIPT restart
            break
        fi
    done
else
    echo "Nie udało się zaktualizować pliku oscam.dvbapi w żadnym katalogu."
fi
sleep 3
'''.format(url=url)
        console_screen_open(self.sess, "Aktualizacja oscam.dvbapi", [cmd], close_on_finish=True)


    def do_clear_dvbapi(self, confirmed):
        if confirmed:
            cmd = '''
echo "Szukam katalogów konfiguracyjnych Oscam..."
CONFIG_DIRS=$(find /etc/tuxbox/config /usr/keys /var/keys -maxdepth 2 -name oscam.conf -exec dirname {} \\; 2>/dev/null | sort -u)
# Dodaj domyślne ścieżki, jeśli istnieją
for DPATH in /etc/tuxbox/config /usr/keys /var/keys; do [ -d "$DPATH" ] && ! echo "$CONFIG_DIRS" | grep -q "$DPATH" && CONFIG_DIRS="$CONFIG_DIRS"$'\n'"$DPATH"; done
if [ -z "$CONFIG_DIRS" ]; then CONFIG_DIRS="/etc/tuxbox/config"; fi

echo "Przetwarzam katalogi:"
echo "$CONFIG_DIRS"

CLEARED=0
for DIR in $CONFIG_DIRS; do
    if [ -z "$DIR" ]; then continue; fi
    DVBAPI_PATH="$DIR/oscam.dvbapi"
    if [ -f "$DVBAPI_PATH" ]; then
        echo "   Czyszczę plik: $DVBAPI_PATH"
        # Opcjonalnie: zrób backup przed wyczyszczeniem
        # cp "$DVBAPI_PATH" "$DVBAPI_PATH.bak_$(date +%Y%m%d_%H%M%S)"
        echo "" > "$DVBAPI_PATH"
        CLEARED=1
    fi
done

if [ $CLEARED -eq 1 ]; then
    echo "Plik(i) oscam.dvbapi został(y) wyczyszczony."
    echo "Restartuję Oscam..."
    for i in softcam.oscam oscam softcam; do
        INIT_SCRIPT="/etc/init.d/$i"
        if [ -f "$INIT_SCRIPT" ]; then $INIT_SCRIPT restart; break; fi
    done
else
    echo "Nie znaleziono pliku oscam.dvbapi do wyczyszczenia."
fi
sleep 3
'''
            console_screen_open(self.sess, "Kasowanie oscam.dvbapi", [cmd], close_on_finish=True)

    def clear_ftp_password(self):
        # Sprawdźmy najpierw, czy user root istnieje
        cmd = "if grep -q '^root:' /etc/passwd; then passwd -d root && echo 'Hasło FTP (root) zostało skasowane.'; else echo 'Użytkownik root nie istnieje w /etc/passwd.'; fi; sleep 3"
        console_screen_open(self.sess, "Kasowanie hasła FTP", [cmd], close_on_finish=True)


    def set_system_password(self):
        # Używamy InputBox do pobrania hasła
        self.sess.openWithCallback(
            self._set_system_password_execute,
            InputBox,
            title="Nowe hasło dla użytkownika root:",
            text="",
            type=InputBox.TYPE_PASSWORD
        )

    def _set_system_password_execute(self, password):
        # Sprawdzamy czy hasło nie jest puste
        if password is None or password == "":
             show_message_compat(self.sess, "Anulowano ustawianie hasła.", MessageBox.TYPE_INFO, timeout=5)
             return
        # Używamy printf dla bezpieczeństwa (unika problemów ze znakami specjalnymi w echo)
        # Dodajemy sprawdzenie, czy user root istnieje
        cmd = 'if grep -q "^root:" /etc/passwd; then (printf "%s\\n%s\\n" "{pw}" "{pw}") | passwd root && echo "Hasło dla root zostało ustawione."; else echo "Użytkownik root nie istnieje."; fi; sleep 3'.format(pw=password.replace('"', '\\"')) # Podwójne cudzysłowy w haśle
        console_screen_open(self.sess, "Ustawianie Hasła", [cmd], close_on_finish=True)


    def show_free_space(self):
        console_screen_open(self.sess, "Wolne miejsce", ["df -h"], close_on_finish=False) # Pozostaw otwarte

    def restart_oscam(self):
        cmd = 'FOUND=0; for SCRIPT in softcam.oscam oscam softcam; do INIT_SCRIPT="/etc/init.d/$SCRIPT"; if [ -f "$INIT_SCRIPT" ]; then echo "Restartuję $SCRIPT..."; $INIT_SCRIPT restart; FOUND=1; break; fi; done; [ $FOUND -ne 1 ] && echo "Nie znaleziono skryptu startowego Oscam."; echo "Zakończono."; sleep 2;'
        console_screen_open(self.sess, "Restart Oscam", [cmd.strip()], close_on_finish=True)


    def show_uninstall_manager(self):
        try:
            # Używamy bardziej niezawodnego sposobu listowania pakietów
            cmd = "opkg list-installed | cut -d ' ' -f 1 | sort"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                 raise OSError("Błąd opkg: {}".format(stderr.decode('utf-8', errors='ignore')))
                 
            packages = [line.strip() for line in stdout.decode('utf-8', errors='ignore').splitlines() if line.strip()]
            if not packages:
                 show_message_compat(self.sess, "Nie znaleziono zainstalowanych pakietów.", MessageBox.TYPE_INFO); return

            # Tworzymy listę krotek dla ChoiceBox
            package_list = [(p,) for p in packages]

            self.sess.openWithCallback(
                 self.on_package_selected_for_uninstall,
                 ChoiceBox,
                 title="Wybierz pakiet do odinstalowania",
                 list=package_list
            )
        except Exception as e:
            print("[AIO Panel] Błąd Menadżera Deinstalacji:", e)
            show_message_compat(self.sess, "Błąd Menadżera Deinstalacji:\n{}".format(e), message_type=MessageBox.TYPE_ERROR)

    def on_package_selected_for_uninstall(self, choice):
         if choice:
             package_name = choice[0]
             self.sess.openWithCallback(
                 lambda confirmed: self._execute_uninstall(package_name) if confirmed else None,
                 MessageBox,
                 "Czy na pewno chcesz odinstalować pakiet:\n{}?".format(package_name),
                 type=MessageBox.TYPE_YESNO
             )

    def _execute_uninstall(self, package_name):
         # Dodajemy flagę --force-remove dla pewności
         cmd = "opkg remove --force-remove {}".format(package_name)
         console_screen_open(self.sess, "Odinstalowywanie: " + package_name, [cmd], callback=self.show_manual_restart_message, close_on_finish=True)


    def install_best_oscam(self, callback=None, close_on_finish=False):
        # Nowa, połączona komenda
        cmd = """
            echo "Instalowanie/Aktualizowanie Softcam Feed..."
            wget -O - -q http://updates.mynonpublic.com/oea/feed | bash
            echo "Aktualizuję listę pakietów..."
            opkg update
            echo "Wyszukuję najlepszą wersję Oscam w feedach..."
            # Szukamy bardziej ogólnie, ale priorytetyzujemy ipv4only
            PKG_IPV4=$(opkg list | grep 'oscam.*ipv4only' | grep -E -m 1 'master|emu|stable' | cut -d ' ' -f 1)
            PKG_ANY=$(opkg list | grep '^oscam' | grep -E -m 1 'master|emu|stable' | cut -d ' ' -f 1)

            if [ -n "$PKG_IPV4" ]; then
                PKG_NAME="$PKG_IPV4"
            elif [ -n "$PKG_ANY" ]; then
                 PKG_NAME="$PKG_ANY"
            else
                 PKG_NAME=""
            fi
            
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
        console_screen_open(self.sess, "Instalator Oscam", [cmd], callback=callback, close_on_finish=close_on_finish)

    def get_lists_from_repo(self):
        manifest_url = "https://raw.githubusercontent.com/OliOli2013/PanelAIO-Lists/main/manifest.json"
        tmp_json_path = os.path.join(PLUGIN_TMP_PATH, 'manifest.json')
        prepare_tmp_dir()
        try:
            cmd = "wget --no-check-certificate -q -T 20 -O {} {}".format(tmp_json_path, manifest_url)
            # Używamy subprocess.call dla pewności, że komenda się zakończy
            ret_code = subprocess.call(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if ret_code != 0:
                 print("[AIO Panel] Wget error downloading manifest (code {})".format(ret_code))
                 raise IOError("wget failed with code {}".format(ret_code))
            if not (os.path.exists(tmp_json_path) and os.path.getsize(tmp_json_path) > 0):
                print("[AIO Panel] Błąd pobierania manifest.json: plik pusty lub nie istnieje")
                raise IOError("Downloaded manifest file is empty or missing")
        except Exception as e:
            print("[AIO Panel] Błąd pobierania manifest.json (wyjątek):", e)
            # Zwróć pustą listę zamiast rzucać wyjątek dalej, aby uniknąć crashu w GUI
            return []
            
        lists_menu = []
        try:
            with open(tmp_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Sprawdź czy data jest listą
            if isinstance(data, list):
                for item in data:
                    # Sprawdź czy item jest słownikiem i ma klucz 'url'
                    if isinstance(item, dict) and item.get('url'):
                        menu_title = "{} - {} ({})".format(item.get('name', 'Brak nazwy'), item.get('author', 'Anonim'), item.get('version', 'b/d'))
                        action = "archive:{}".format(item['url'])
                        lists_menu.append((menu_title, action))
            else:
                 print("[AIO Panel] Błąd: manifest.json nie zawiera listy.")
                 
        except json.JSONDecodeError as e:
             print("[AIO Panel] Błąd dekodowania pliku manifest.json:", e)
        except Exception as e:
            print("[AIO Panel] Błąd przetwarzania pliku manifest.json:", e)
        
        # Zawsze zwracaj listę, nawet jeśli jest pusta
        if not lists_menu:
             print("[AIO Panel] Nie znaleziono poprawnych list w manifest.json")
        return lists_menu


def main(session, **kwargs):
    session.open(Panel)

def Plugins(**kwargs):
    return [PluginDescriptor(name="AIO Panel", description="Panel All-In-One by Paweł Pawełek (v{})".format(VER), where = PluginDescriptor.WHERE_PLUGINMENU, icon = "logo.png", fnc = main)]
