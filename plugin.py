# -*- coding: utf-8 -*-
"""
Panel AIO
by Paweł Pawełek | msisystem@t.pl
Wersja 2.0 (finalna, uniwersalna) - poprawiona wersja Super Konfiguratora
"""
from __future__ import print_function
from __future__ import absolute_import
from enigma import eDVBDB
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
import os
import socket
import datetime
import sys
import subprocess
import shutil
import re
import json
from twisted.internet import reactor

# === SEKCJA GLOBALNYCH ZMIENNYCH ===
PLUGIN_PATH = os.path.dirname(os.path.realpath(__file__))
PLUGIN_TMP_PATH = "/tmp/PanelAIO/"
PLUGIN_ICON_PATH = os.path.join(PLUGIN_PATH, "logo.png")
PLUGIN_SELECTION_PATH = os.path.join(PLUGIN_PATH, "selection.png")
PLUGIN_QR_CODE_PATH = os.path.join(PLUGIN_PATH, "Kod_QR_buycoffee.png")
VER = "2.0" # Zachowano wersję 2.0
DATE = str(datetime.date.today())
FOOT = "AIO {} | {} | by Paweł Pawełek | msisystem@t.pl".format(VER, DATE)

# ✅ POPRAWIONE: surowe ciągi (raw strings)
LEGEND_PL = r"\c00ff0000●\c00ffffff PL \c0000ff00●\c00ffffff EN \c00ffff00●\c00ffffff Restart GUI \c000000ff●\c00ffffff Aktualizuj"
LEGEND_EN = r"\c00ff0000●\c00ffffff PL \c0000ff00●\c00ffffff EN \c00ffff00●\c00ffffff Restart GUI \c000000ff●\c00ffffff Update"

# === SEKCJA TŁUMACZEń ===
TRANSLATIONS = {
    "PL": {
        "support_text": "Wesprzyj rozwój wtyczki",
        "update_available_title": "Dostępna nowa wersja!",
        "update_available_msg": """Panel AIO: {latest_ver}
Twoja wersja: {current_ver}
Lista zmian:
{changelog}
Czy chcesz ją teraz zainstalować?""",
        "already_latest": "Używasz najnowszej wersji wtyczki ({ver}).",
        "update_check_error": """Nie można sprawdzić dostępności aktualizacji.
Sprawdź połączenie z internetem.""",
        "update_generic_error": "Wystąpił błąd podczas sprawdzania aktualizacji."
    },
    "EN": {
        "support_text": "Support plugin development",
        "update_available_title": "New version available!",
        "update_available_msg": """Panel AIO: {latest_ver}
Your version: {current_ver}
Changelog:
{changelog}
Do you want to install it now?""",
        "already_latest": "You are using the latest version of the plugin ({ver}).",
        "update_check_error": """Could not check for updates.
Please check your internet connection.""",
        "update_generic_error": "An error occurred while checking for updates."
    }
}
# === KONIEC SEKCJI ===

# === FUNKCje POMOCNICZE ===
def show_message_compat(session, message, message_type=MessageBox.TYPE_INFO, timeout=10, on_close=None):
    from twisted.internet import reactor
    reactor.callLater(0.2, lambda: session.openWithCallback(on_close, MessageBox, message, message_type, timeout=timeout))

def console_screen_open(session, title, cmds_with_args, callback=None, close_on_finish=False):
    cmds_list = cmds_with_args if isinstance(cmds_with_args, list) else [cmds_with_args]
    c_dialog = session.open(Console, title, cmds_list, closeOnSuccess=close_on_finish)
    if callback: c_dialog.onClose.append(callback)

def prepare_tmp_dir():
    if not os.path.exists(PLUGIN_TMP_PATH):
        os.makedirs(PLUGIN_TMP_PATH)

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
    except Exception as e: print("[PanelAIO] Błąd parsowania listy S4aUpdater:", e)
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
        return "Auto"
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
    ("Instalator ServiceApp", "CMD:INSTALL_SERVICEAPP"),
    ("StreamlinkProxy - Instalator", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-streamlinkproxy"),
    ("AJPanel", "bash_raw:wget https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh -O - | /bin/sh"),
    ("E2iPlayer Master - Instalacja/Aktualizacja", "bash_raw:" + E2IPLAYER_INSTALL_CMD),
    ("EPG Import", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh -O - | /bin/bash"),
    ("S4aUpdater", "bash_raw:wget http://s4aupdater.one.pl/instalujs4aupdater.sh -O - | /bin/sh"),
    ("JediMakerXtream", "bash_raw:wget https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh -O - | /bin/sh"),
    ("YouTube", "bash_raw:opkg install https://github.com/Taapat/enigma2-plugin-youtube/releases/download/git1294/enigma2-plugin-extensions-youtube_py3-git1294-cbcf8b0-r0.0.ipk"),
]

SOFTCAM_AND_PLUGINS_EN = [
    ("--- Softcams ---", "SEPARATOR"),
    ("Restart Oscam", "CMD:RESTART_OSCAM"),
    ("Clear Oscam Password", "CMD:CLEAR_OSCAM_PASS"),
    ("oscam.dvbapi - manage", "CMD:MANAGE_DVBAPI"),
    ("Oscam from Feed (Auto)", "CMD:INSTALL_BEST_OSCAM"),
    ("NCam 15.5", "bash_raw:wget https://raw.githubusercontent.com/biko-73/Ncam_EMU/main/installer.sh -O - | /bin/sh"),
    ("--- Online Plugins ---", "SEPARATOR"),
    ("ServiceApp Installer", "CMD:INSTALL_SERVICEAPP"),
    ("StreamlinkProxy - Installer", "bash_raw:opkg update && opkg install enigma2-plugin-extensions-streamlinkproxy"),
    ("AJPanel", "bash_raw:wget https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh -O - | /bin/sh"),
    ("E2iPlayer Master - Install/Update", "bash_raw:" + E2IPLAYER_INSTALL_CMD),
    ("EPG Import", "bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh -O - | /bin/bash"),
    ("S4aUpdater", "bash_raw:wget http://s4aupdater.one.pl/instalujs4aupdater.sh -O - | /bin/sh"),
    ("JediMakerXtream", "bash_raw:wget https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh -O - | /bin/sh"),
    ("YouTube", "bash_raw:opkg install https://github.com/Taapat/enigma2-plugin-youtube/releases/download/git1294/enigma2-plugin-extensions-youtube_py3-git1294-cbcf8b0-r0.0.ipk"),
]

TOOLS_AND_ADDONS_PL = [
    ("--- Konfigurator ---", "SEPARATOR"),
    ("Super Konfigurator (Pierwsza Instalacja)", "CMD:SUPER_SETUP_WIZARD"),
    ("--- Narzędzia Systemowe ---", "SEPARATOR"),
    ("Aktualizacja Wtyczki", "CMD:CHECK_FOR_UPDATES"),
    ("Menadżer Deinstalacji", "CMD:UNINSTALL_MANAGER"),
    ("Instalacja Softcam Feed", "CMD:INSTALL_SOFTCAM_FEED"),
    ("Aktualizuj satellites.xml", "CMD:UPDATE_SATELLITES_XML"),
    ("Pobierz Picony (Transparent)", "archive:https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip"),
    ("Kasuj hasło FTP", "CMD:CLEAR_FTP_PASS"),
    ("Ustaw Hasło FTP", "CMD:SET_SYSTEM_PASSWORD"),
    ("--- Diagnostyka i Czyszczenie ---", "SEPARATOR"),
    ("Test Prędkości Internetu", "CMD:SPEEDTEST_DISPLAY"),
    ("Twoje IP / Ping", "CMD:IP_PING_DISPLAY"),
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
    ("Install Softcam Feed", "CMD:INSTALL_SOFTCAM_FEED"),
    ("Update satellites.xml", "CMD:UPDATE_SATELLITES_XML"),
    ("Download Picons (Transparent)", "archive:https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip"),
    ("Clear FTP Password", "CMD:CLEAR_FTP_PASS"),
    ("Set FTP Password", "CMD:SET_SYSTEM_PASSWORD"),
    ("--- Diagnostics & Cleaning ---", "SEPARATOR"),
    ("Internet Speed Test", "CMD:SPEEDTEST_DISPLAY"),
    ("Your IP / Ping", "CMD:IP_PING_DISPLAY"),
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
            "softcam_feed": self._wizard_step_softcam_feed,
            "install_oscam": self._wizard_step_install_oscam,
            "picons": self._wizard_step_picons,
            "reload_settings": self._wizard_step_reload_settings
        }
        
        func_to_run = step_functions.get(next_step)
        if func_to_run:
            reactor.callLater(0.5, func_to_run)
        else:
            print("[PanelAIO] Nieznany krok w Super Konfiguratorze:", next_step)
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
        install_archive(self.session, title, url, callback_on_finish=self._wizard_run_next_step)

    def _wizard_step_softcam_feed(self):
        title = self._get_wizard_title("Instalacja Softcam Feed")
        console_screen_open(self.session, title, ["wget -O - -q http://updates.mynonpublic.com/oea/feed | bash"], callback=self._wizard_run_next_step, close_on_finish=True)

    def _wizard_step_install_oscam(self):
        title = self._get_wizard_title("Instalacja Oscam")
        cmd = """
            echo "Aktualizuję listę pakietów...";
            opkg update ;
            echo "Wyszukuję najlepszą wersję Oscam w feedach...";
            PKG_NAME=$(opkg list | grep 'oscam' | grep 'ipv4only' | grep -E -m 1 'master|emu|stable' | cut -d ' ' -f 1) ;
            if [ -n "$PKG_NAME" ]; then
                echo "Znaleziono pakiet: $PKG_NAME. Rozpoczynam instalację..." ;
                opkg install $PKG_NAME ;
            else
                echo "Nie znaleziono odpowiedniego pakietu Oscam w feedach.";
                echo "Próbuję instalacji z alternatywnego źródła (Levi45)...";
                wget -q "--no-check-certificate" https://raw.githubusercontent.com/levi45/oscam-emulator/main/installer.sh -O - | /bin/sh;
            fi
        """
        console_screen_open(self.session, title, [cmd], callback=self._wizard_run_next_step, close_on_finish=True)

    def _wizard_step_picons(self):
        title = self._get_wizard_title("Instalacja Picon (Transparent)")
        url = self.wizard_picon_url
        install_archive(self.session, title, url, callback_on_finish=self._wizard_run_next_step)
        
    def _wizard_step_reload_settings(self):
        try:
            eDVBDB.getInstance().reloadServicelist()
            eDVBDB.getInstance().reloadBouquets()
        except Exception as e:
            print("[PanelAIO] Błąd podczas przeładowywania list w wizardzie:", e)
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
    </screen>""".format(PLUGIN_QR_CODE_PATH)

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle(" ")
        self.sess, self.col, self.lang, self.data = session, 'L', 'PL', ([],[],[])
        self["qr_code_small"] = Pixmap()
        self["support_label"] = Label(TRANSLATIONS[self.lang]["support_text"])
        self["title_label"] = Label("Panel AIO " + VER)
        for name in ("headL", "headM", "headR", "legend"): self[name] = Label()
        for name in ("menuL", "menuM", "menuR"): self[name] = MenuList([])
        self["footer"] = Label(FOOT)
        self["act"] = ActionMap(["DirectionActions", "OkCancelActions", "ColorActions", "InfoActions"], {
            "ok": self.run_with_confirmation,
            "cancel": self.close,
            "red": lambda: self.set_lang('PL'),
            "green": lambda: self.set_lang('EN'),
            "yellow": self.restart_gui,
            "blue": self.check_for_updates,
            "info": self.close,
            "up": lambda: self._menu().instance.moveSelection(self._menu().instance.moveUp),
            "down": lambda: self._menu().instance.moveSelection(self._menu().instance.moveDown),
            "left": self.left,
            "right": self.right
        }, -1)
        self.onShown.append(self.initial_setup)

    def initial_setup(self):
        reactor.callLater(0.2, self.check_dependencies)

    # ###########################################
    # ### NOWA, POPRAWIONA WERSJA TEJ FUNKCJI ###
    # ###########################################
    def check_dependencies(self):
        try:
            from shutil import which
        except ImportError:
            # Fallback for older Python versions
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
            # Wszystkie zależności są zainstalowane, ładujemy wtyczkę
            self.set_lang('PL')
            self._focus()
            return

        # Jeśli czegoś brakuje, uruchamiamy uniwersalny instalator
        install_cmds = [
            "echo 'Wykryto brakujące pakiety. Rozpoczynam automatyczną instalację...'",
            "opkg update",
            "opkg install " + " ".join(missing_packages),
            "echo '---------------------------------------------------'",
            "echo 'Instalacja komponentów zakończona!'",
            "echo 'Zalecany jest ręczny restart interfejsu (GUI).'",
            "echo '---------------------------------------------------'",
            "sleep 5"
        ]
        # Używamy callbacku, który tylko załaduje UI wtyczki, BEZ wyświetlania dodatkowych okien
        console_screen_open(self.sess, "Pierwsze uruchomienie: Instalacja zależności", install_cmds, callback=self.on_dependencies_installed_safe, close_on_finish=True)

    def on_dependencies_installed_safe(self, *args):
        # Ten callback jest bezpieczny - po prostu ładuje treść wtyczki po zamknięciu konsoli
        self.set_lang('PL')
        self._focus()
    # ###########################################
    # ###          KONIEC POPRAWEK            ###
    # ###########################################

    def check_for_updates(self):
        repo_base_url = "https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/"
        version_url = repo_base_url + "version.txt"
        changelog_url = repo_base_url + "changelog.txt"
        tmp_version_path = os.path.join(PLUGIN_TMP_PATH, 'version.txt')
        tmp_changelog_path = os.path.join(PLUGIN_TMP_PATH, 'changelog.txt')
        prepare_tmp_dir()
        try:
            cmd_ver = "wget --no-check-certificate -O {} {}".format(tmp_version_path, version_url)
            cmd_log = "wget --no-check-certificate -O {} {}".format(tmp_changelog_path, changelog_url)
            process_ver = subprocess.Popen(cmd_ver, shell=True)
            process_log = subprocess.Popen(cmd_log, shell=True)
            process_ver.wait()
            process_log.wait()
            if os.path.exists(tmp_version_path) and os.path.getsize(tmp_version_path) > 0:
                with open(tmp_version_path, 'r') as f:
                    latest_ver = f.read().strip()
                if latest_ver and latest_ver != VER:
                    changelog_text = "Brak informacji o zmianach."
                    if os.path.exists(tmp_changelog_path) and os.path.getsize(tmp_changelog_path) > 0:
                        with open(tmp_changelog_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        found_version_section = False
                        changes = []
                        for line in lines:
                            line = line.strip()
                            if line == "[{}]".format(latest_ver):
                                found_version_section = True
                                continue
                            if found_version_section:
                                if line.startswith("[") and line.endswith("]"):
                                    break
                                if line:
                                    changes.append(line)
                        if changes:
                            changelog_text = "\n".join(changes)
                    def do_update(result):
                        if result:
                            update_cmd = 'wget -q "--no-check-certificate" https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh -O - | /bin/sh'
                            console_screen_open(self.sess, "Aktualizacja Panelu AIO...", [update_cmd])
                    message = TRANSLATIONS[self.lang]["update_available_msg"].format(
                        latest_ver=latest_ver,
                        current_ver=VER,
                        changelog=changelog_text
                    )
                    self.sess.openWithCallback(do_update, MessageBox, message, title=TRANSLATIONS[self.lang]["update_available_title"], type=MessageBox.TYPE_YESNO)
                else:
                    message = TRANSLATIONS[self.lang]["already_latest"].format(ver=VER)
                    show_message_compat(self.sess, message)
            else:
                show_message_compat(self.sess, TRANSLATIONS[self.lang]["update_check_error"], message_type=MessageBox.TYPE_ERROR)
        except Exception as e:
            print("[PanelAIO] Błąd podczas sprawdzania aktualizacji:", e)
            show_message_compat(self.sess, TRANSLATIONS[self.lang]["update_generic_error"], message_type=MessageBox.TYPE_ERROR)

    def get_lists_from_repo(self):
        manifest_url = "https://raw.githubusercontent.com/OliOli2013/PanelAIO-Lists/main/manifest.json"
        tmp_json_path = os.path.join(PLUGIN_TMP_PATH, 'manifest.json')
        prepare_tmp_dir()
        try:
            cmd = "wget --no-check-certificate -q -T 15 -O {} {}".format(tmp_json_path, manifest_url)
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.wait()
            if not (os.path.exists(tmp_json_path) and os.path.getsize(tmp_json_path) > 0):
                return [("Błąd pobierania list (Repo)", "SEPARATOR")]
        except Exception as e:
            print("[PanelAIO] Błąd pobierania manifest.json:", e)
            return [("Błąd krytyczny (Repo)", "SEPARATOR")]
        lists_menu = []
        try:
            with open(tmp_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for item in data:
                menu_title = "{} - {} ({})".format(item.get('name', 'Brak nazwy'), item.get('author', ''), item.get('version', ''))
                action = "archive:{}".format(item.get('url', ''))
                if item.get('url'):
                    lists_menu.append((menu_title, action))
        except Exception as e:
            print("[PanelAIO] Błąd przetwarzania pliku manifest.json:", e)
            return [("Błąd formatu pliku (Repo)", "SEPARATOR")]
        if not lists_menu:
            return [("Brak list w repozytorium", "SEPARATOR")]
        return lists_menu

    def run_with_confirmation(self):
        try:
            name, action = self.data[{'L':0,'M':1,'R':2}[self.col]][self._menu().getSelectedIndex()]
        except (IndexError, KeyError, TypeError):
            return
        if action == "SEPARATOR":
            return
        actions_no_confirm = ["CMD:IP_PING_DISPLAY", "CMD:SPEEDTEST_DISPLAY", "CMD:FREE_SPACE_DISPLAY", "CMD:UNINSTALL_MANAGER", "CMD:MANAGE_DVBAPI", "CMD:CHECK_FOR_UPDATES", "CMD:SUPER_SETUP_WIZARD", "CMD:UPDATE_SATELLITES_XML", "CMD:INSTALL_SERVICEAPP"]
        if any(action.startswith(prefix) for prefix in actions_no_confirm):
            self.execute_action(name, action)
        else:
            self.sess.openWithCallback(
                lambda ret: self.execute_action(name, action) if ret else None,
                MessageBox, "Czy na pewno chcesz wykonać akcję:\n'{}'?".format(name), type=MessageBox.TYPE_YESNO
            )

    def execute_action(self, name, action):
        title = name
        if action.startswith("bash_raw:"):
            console_screen_open(self.sess, title, [action.split(':', 1)[1]])
        elif action.startswith("archive:"):
            install_archive(self.sess, title, action.split(':', 1)[1], callback_on_finish=self.reload_settings_python)
        elif action.startswith("CMD:"):
            command_key = action.split(':', 1)[1]
            if command_key == "SUPER_SETUP_WIZARD": self.run_super_setup_wizard()
            elif command_key == "CHECK_FOR_UPDATES": self.check_for_updates()
            elif command_key == "UPDATE_SATELLITES_XML":
                script_path = os.path.join(PLUGIN_PATH, "update_satellites_xml.sh")
                console_screen_open(self.sess, title, ["bash " + script_path], callback=self.reload_settings_python)
            elif command_key == "INSTALL_SERVICEAPP":
                cmd = "opkg update && opkg install enigma2-plugin-systemplugins-serviceapp exteplayer3 gstplayer && opkg install uchardet --force-reinstall"
                console_screen_open(self.sess, title, [cmd])
            elif command_key == "SPEEDTEST_DISPLAY": self.run_speed_test()
            elif command_key == "IP_PING_DISPLAY": self.show_ip_and_ping()
            elif command_key == "INSTALL_BEST_OSCAM": self.install_best_oscam()
            elif command_key == "MANAGE_DVBAPI": self.manage_dvbapi()
            elif command_key == "UNINSTALL_MANAGER": self.show_uninstall_manager()
            elif command_key == "INSTALL_SOFTCAM_FEED": self.install_softcam_feed()
            elif command_key == "CLEAR_OSCAM_PASS": self.clear_oscam_password()
            elif command_key == "CLEAR_FTP_PASS": self.clear_ftp_password()
            elif command_key == "SET_SYSTEM_PASSWORD": self.set_system_password()
            elif command_key == "RESTART_OSCAM": self.restart_oscam()
            elif command_key == "FREE_SPACE_DISPLAY": self.show_free_space()
            elif command_key == "CLEAR_TMP_CACHE": console_screen_open(self.sess, title, ["rm -rf " + PLUGIN_TMP_PATH + "*"])
            elif command_key == "CLEAR_RAM_CACHE": console_screen_open(self.sess, title, ["sync; echo 3 > /proc/sys/vm/drop_caches"])

    def _menu(self):
        return {'L':self["menuL"], 'M':self["menuM"], 'R':self["menuR"]}[self.col]

    def _focus(self):
        self["menuL"].selectionEnabled(self.col=='L'); self["menuM"].selectionEnabled(self.col=='M')
        self["menuR"].selectionEnabled(self.col=='R')

    def left(self): self.col = {'M':'L','R':'M'}.get(self.col,self.col); self._focus()
    def right(self): self.col = {'L':'M','M':'R'}.get(self.col,self.col); self._focus()
    def restart_gui(self): self.sess.open(TryQuitMainloop, 3)

    def reload_settings_python(self, *args):
        try:
            db = eDVBDB.getInstance()
            db.reloadServicelist()
            db.reloadBouquets()
        except Exception as e:
            print("[PanelAIO] Błąd podczas przeładowywania list:", e)
            show_message_compat(self.sess, "Wystąpił błąd podczas przeładowywania list.", message_type=MessageBox.TYPE_ERROR)

    def install_softcam_feed(self, callback=None, close_on_finish=False):
        console_screen_open(self.sess, "Instalacja Feeda Softcam", ["wget -O - -q http://updates.mynonpublic.com/oea/feed | bash"], callback=callback, close_on_finish=close_on_finish)

    def set_lang(self, lang):
        self.lang = lang
        repo_lists = self.get_lists_from_repo()
        s4a_lists_full = get_s4aupdater_lists_dynamic()
        keywords_to_remove = ['bzyk', 'jakitaki']
        s4a_lists_filtered = [
            item for item in s4a_lists_full
            if not any(keyword in item[0].lower() for keyword in keywords_to_remove)
        ]
        final_channel_lists = repo_lists + s4a_lists_filtered
        best_oscam_version = get_best_oscam_version_info()
        if lang == 'PL':
            softcam_menu = list(SOFTCAM_AND_PLUGINS_PL)
            tools_menu = list(TOOLS_AND_ADDONS_PL)
            oscam_text = "Oscam z Feeda ({})"
        else:
            softcam_menu = list(SOFTCAM_AND_PLUGINS_EN)
            tools_menu = list(TOOLS_AND_ADDONS_EN)
            oscam_text = "Oscam from Feed ({})"
        for i, (name, action) in enumerate(softcam_menu):
            if action == "CMD:INSTALL_BEST_OSCAM":
                softcam_menu[i] = (oscam_text.format(best_oscam_version), action)
                break
        self.data = (final_channel_lists, softcam_menu, tools_menu)
        for i, menu_widget in enumerate((self["menuL"], self["menuM"], self["menuR"])):
            menu_widget.setList([str(item[0]) for item in self.data[i]])
        for i, head_widget in enumerate((self["headL"], self["headM"], self["headR"])):
            head_widget.setText(COL_TITLES[lang][i])
        self["legend"].setText(LEGEND_PL if lang == 'PL' else LEGEND_EN)
        self["support_label"].setText(TRANSLATIONS[self.lang]["support_text"])
        self._focus()

    def clear_oscam_password(self):
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
                    new_lines = [line for line in lines if not line.strip().lower().startswith("httppwd")]
                    if len(new_lines) < len(lines):
                        with open(conf_path, "w") as f: f.writelines(new_lines)
                        found = True
            if found:
                show_message_compat(self.sess, "Hasło Oscam zostało skasowane we wszystkich znalezionych konfiguracjach.")
            else:
                show_message_compat(self.sess, "Nie znaleziono hasła Oscam w żadnym pliku konfiguracyjnym.")
        except Exception as e:
            show_message_compat(self.sess, "Błąd krytyczny: {}".format(e), message_type=MessageBox.TYPE_ERROR)

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
        if choice is None:
            show_message_compat(self.sess, "Anulowano.", message_type=MessageBox.TYPE_INFO)
            return
        if choice[1] == "custom":
            self.sess.openWithCallback(
                self.on_custom_dvbapi_url_entered,
                InputBox,
                title="Podaj własny URL do pliku oscam.dvbapi",
                text="https://raw.githubusercontent.com/picons/oscam-configs/main/oscam.dvbapi"
            )
        elif choice[1] == "clear":
            self.sess.openWithCallback(
                self.do_clear_dvbapi,
                MessageBox,
                """Czy na pewno chcesz skasować zawartość pliku oscam.dvbapi?
Spowoduje to usunięcie wszystkich priorytetów i ignorowanych kanałów.""",
                type=MessageBox.TYPE_YESNO
            )
        else:
            self.process_dvbapi_download(choice[1])

    def on_custom_dvbapi_url_entered(self, url):
        if url:
            self.process_dvbapi_download(url)
        else:
            show_message_compat(self.sess, "Anulowano.", message_type=MessageBox.TYPE_INFO)

    def process_dvbapi_download(self, url):
        cmd = """
#!/bin/sh
URL="{url}"
echo "Rozpoczynam aktualizację oscam.dvbapi z $(echo $URL | cut -d'/' -f3)..."
CONFIG_DIRS=$(find /etc/tuxbox/config -name oscam.conf -exec dirname {{}} \\; | sort -u)
[ -z "$CONFIG_DIRS" ] && CONFIG_DIRS="/etc/tuxbox/config"
SUCCESS=0
for DIR in $CONFIG_DIRS; do
    echo "-> Przetwarzam: $DIR"
    [ ! -d "$DIR" ] && mkdir -p "$DIR"
    [ -f "$DIR/oscam.dvbapi" ] && cp "$DIR/oscam.dvbapi" "$DIR/oscam.dvbapi.bak"
    if wget -q --timeout=30 --tries=3 --no-check-certificate "$URL" -O "$DIR/oscam.dvbapi.tmp"; then
        if grep -q "P:" "$DIR/oscam.dvbapi.tmp"; then
            mv "$DIR/oscam.dvbapi.tmp" "$DIR/oscam.dvbapi"
            echo "   Sukces: Poprawny plik dvbapi"
            SUCCESS=1
        else
            echo "   Błąd: Nieprawidłowy format pliku (brak linii z 'P:')"
            rm -f "$DIR/oscam.dvbapi.tmp"
        fi
    else
        echo "   Błąd: Pobieranie nieudane (URL: $URL)"
        [ -f "$DIR/oscam.dvbapi.bak" ] && mv "$DIR/oscam.dvbapi.bak" "$DIR/oscam.dvbapi"
    fi
done
if [ $SUCCESS -eq 1 ]; then
    echo "Aktualizacja zakończona. Restartowanie Oscam..."
    for i in softcam.oscam oscam softcam; do
        [ -f "/etc/init.d/$i" ] && /etc/init.d/$i restart && break
    done
else
    echo "Aktualizacja nie powiodła się!"
    echo "Możesz spróbować ręcznie pobrać plik z:"
    echo "{url}"
fi
sleep 2
""".format(url=url)
        console_screen_open(self.sess, "Aktualizacja oscam.dvbapi", [cmd])

    def do_clear_dvbapi(self, confirmed):
        if confirmed:
            cmd = """
#!/bin/sh
echo "Kasowanie zawartości oscam.dvbapi..."
CONFIG_DIRS=$(find /etc/tuxbox/config -name oscam.conf -exec dirname {} \\; | sort -u)
[ -z "$CONFIG_DIRS" ] && CONFIG_DIRS="/etc/tuxbox/config"
SUCCESS=0
for DIR in $CONFIG_DIRS; do
    echo "-> Przetwarzam: $DIR"
    DVBAPI_PATH="$DIR/oscam.dvbapi"
    if [ -f "$DVBAPI_PATH" ]; then
        cp "$DVBAPI_PATH" "$DVBAPI_PATH.bak"
        echo "" > "$DVBAPI_PATH"
        echo "   Sukces: Zawartość pliku skasowana"
        SUCCESS=1
    else
        echo "   Informacja: Plik $DVBAPI_PATH nie istnieje, nie ma czego kasować."
    fi
done
if [ $SUCCESS -eq 1 ]; then
    echo "Kasowanie zakonczone. Restartowanie Oscam..."
    for i in softcam.oscam oscam softcam; do
        [ -f "/etc/init.d/$i" ] && /etc/init.d/$i restart && break
    done
else
    echo "Kasowanie nie powiodło się lub plik nie istnieje!"
fi
sleep 2
"""
            console_screen_open(self.sess, "Kasowanie oscam.dvbapi", [cmd])
        else:
            show_message_compat(self.sess, "Anulowano. Plik oscam.dvbapi nie został skasowany.", message_type=MessageBox.TYPE_INFO)

    def run_speed_test(self):
        cmd = """
            echo "Testowanie prędkości...";
            SPEED=$(wget -O /dev/null http://speedtest.tele2.net/10MB.zip 2>&1 | grep -o -E '[0-9.]+ [KM]B/s' | tail -1);
            echo "Prędkość pobierania: $SPEED";
            sleep 2;
        """
        console_screen_open(self.sess, "Test prędkości", [cmd])

    def show_ip_and_ping(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except:
            ip = "Brak połączenia"
        cmd = """
            echo "Twój adres IP: {ip}";
            PING=$(ping -c 4 google.com | grep -E 'rtt min/avg/max/mdev' | cut -d'=' -f2);
            echo "Średni ping: $PING";
            sleep 2;
        """.format(ip=ip)
        console_screen_open(self.sess, "IP i Ping", [cmd])

    def clear_ftp_password(self):
        console_screen_open(self.sess, "Kasowanie hasła FTP", ["passwd -d root"])

    def set_system_password(self):
        def onPasswordEntered(password):
            if password:
                console_screen_open(self.sess, "Ustawianie Hasła", ["(echo {}; echo {}) | passwd".format(password, password)])
            else:
                show_message_compat(self.sess, "Anulowano. Hasło nie zostało zmienione.", message_type=MessageBox.TYPE_WARNING)
        self.sess.openWithCallback(onPasswordEntered, InputBox, title="Wpisz nowe hasło dla konta root:", windowTitle="Ustaw Hasło FTP", text="")

    def show_free_space(self):
        console_screen_open(self.sess, "Wolne miejsce", ["df -h"])

    def restart_oscam(self):
        cmd = """
            echo "Szukam aktywnego skryptu startowego Oscam...";
            FOUND=0;
            for SCRIPT in softcam.oscam oscam softcam; do
                INIT_SCRIPT="/etc/init.d/$SCRIPT";
                if [ -f "$INIT_SCRIPT" ]; then
                    echo "Znaleziono skrypt: $INIT_SCRIPT";
                    echo "Restartowanie...";
                    $INIT_SCRIPT restart;
                    echo "Polecenie restartu wysłane.";
                    FOUND=1;
                    break;
                fi;
            done;
            if [ $FOUND -eq 0 ]; then
                echo "Nie znaleziono żadnego znanego skryptu startowego Oscam.";
                echo "Restart nie powiódł się.";
            fi;
            sleep 2;
        """
        console_screen_open(self.sess, "Restart Oscam", [cmd.strip()])

    def show_uninstall_manager(self):
        try:
            process = subprocess.Popen("opkg list-installed", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            if process.returncode != 0:
                show_message_compat(self.sess, "Błąd pobierania listy pakietów.", message_type=MessageBox.TYPE_ERROR); return
            decoded_stdout = stdout.decode('utf-8', errors='ignore')
            packages = [line.split(' - ')[0] for line in decoded_stdout.splitlines() if ' - ' in line]
            packages.sort()
            def on_package_selected(choice):
                if choice:
                    package_name = choice[0]
                    def do_uninstall(confirmed):
                        if confirmed:
                            cmd = "opkg remove {}".format(package_name)
                            console_screen_open(self.sess, "Odinstalowywanie: " + package_name, [cmd])
                    self.sess.openWithCallback(do_uninstall, MessageBox, "Czy na pewno chcesz odinstalować pakiet:\n{}?".format(package_name), type=MessageBox.TYPE_YESNO)
            self.sess.open(ChoiceBox, title="Wybierz pakiet do odinstalowania", list=[(p,) for p in packages], keys=[''], skin_name="ChoiceBox_List")
        except Exception as e:
            show_message_compat(self.sess, "Błąd Menadżera Deinstalacji:\n{}".format(e), message_type=MessageBox.TYPE_ERROR)

    def install_best_oscam(self, callback=None, close_on_finish=False):
        cmd = """
            echo "Aktualizuję listę pakietów...";
            opkg update ;
            echo "Wyszukuję najlepszą wersję Oscam w feedach...";
            PKG_NAME=$(opkg list | grep 'oscam' | grep 'ipv4only' | grep -E -m 1 'master|emu|stable' | cut -d ' ' -f 1) ;
            if [ -n "$PKG_NAME" ]; then
                echo "Znaleziono pakiet: $PKG_NAME. Rozpoczynam instalację..." ;
                opkg install $PKG_NAME ;
            else
                echo "Nie znaleziono odpowiedniego pakietu Oscam w feedach.";
                echo "Próbuję instalacji z alternatywnego źródła (Levi45)...";
                wget -q "--no-check-certificate" https://raw.githubusercontent.com/levi45/oscam-emulator/main/installer.sh -O - | /bin/sh;
            fi
        """
        console_screen_open(self.sess, "Inteligentny Instalator Oscam", [cmd], callback=callback, close_on_finish=close_on_finish)

    def run_super_setup_wizard(self):
        options = [
            ("1) Zainstaluj tylko zależności (wget, tar, unzip)", "deps_only"),
            ("2) Podstawowa Konfiguracja (z piconami)", "install_no_picons"),
            ("3) Pełna Konfiguracja (z piconami)", "install_with_picons"),
            ("Anuluj", "cancel")
        ]
        self.sess.openWithCallback(
            self._super_wizard_selected,
            ChoiceBox,
            title="Super Konfigurator - Wybierz opcję",
            list=options
        )

    def _super_wizard_selected(self, choice):
        if not choice or choice[1] == "cancel":
            show_message_compat(self.sess, "Anulowano.")
            return

        key = choice[1]
        steps = []
        message = ""

        if key == "deps_only":
            steps = ["deps"]
            message = "Czy na pewno chcesz zainstalować tylko podstawowe zależności systemowe?"
        elif key == "install_no_picons":
            steps = ["deps", "channel_list", "softcam_feed", "install_oscam", "picons", "reload_settings"]
            message = "Rozpocznie się podstawowa konfiguracja systemu.\nZostaną wykonane następujące kroki:\n\n- Instalacja zależności\n- Instalacja listy kanałów\n- Instalacja Softcam Feed\n- Instalacja Oscam\n- Instalacja Piconów\n\nCzy chcesz kontynuować?"
        elif key == "install_with_picons":
            steps = ["deps", "channel_list", "softcam_feed", "install_oscam", "picons", "reload_settings"]
            message = "Rozpocznie się pełna konfiguracja systemu.\nZostaną wykonane następujące kroki:\n\n- Instalacja zależności\n- Instalacja listy kanałów\n- Instalacja Softcam Feed\n- Instalacja Oscam\n- Instalacja Piconów (duży plik)\n\nCzy chcesz kontynuować?"

        if steps:
            self.sess.openWithCallback(
                lambda confirmed: self._wizard_start(steps) if confirmed else None,
                MessageBox, message, type=MessageBox.TYPE_YESNO, title="Potwierdzenie operacji"
            )
            
    def _wizard_start(self, steps):
        channel_list_url = ''
        list_name = 'domyślna lista'
        picon_url = ''

        if "channel_list" in steps:
            repo_lists = self.get_lists_from_repo()
            if repo_lists and repo_lists[0][1] != 'SEPARATOR':
                try:
                    list_name = repo_lists[0][0].split(' - ')[0]
                    channel_list_url = repo_lists[0][1].split(':', 1)[1]
                except (IndexError, AttributeError):
                    channel_list_url = '' 
            
            if not channel_list_url:
                self.sess.open(MessageBox, "Nie udało się pobrać adresu listy kanałów. Sprawdź połączenie z internetem i spróbuj ponownie.", type=MessageBox.TYPE_ERROR)
                return

        if "picons" in steps:
            for name, action in TOOLS_AND_ADDONS_PL:
                if name.startswith("Pobierz Picony"):
                    try:
                        picon_url = action.split(':', 1)[1]
                        break
                    except (IndexError, AttributeError):
                        picon_url = ''
            
            if not picon_url:
                self.sess.open(MessageBox, "Nie udało się odnaleźć adresu picon w konfiguracji wtyczki.", type=MessageBox.TYPE_ERROR)
                return
        
        self.sess.open(WizardProgressScreen, 
                          steps=steps, 
                          channel_list_url=channel_list_url,
                          channel_list_name=list_name,
                          picon_url=picon_url)

def main(session, **kwargs):
    session.open(Panel)

def Plugins(**kwargs):
    return [PluginDescriptor(name="Panel AIO", description="Panel All-In-One by Paweł Pawełek (v{})".format(VER), where = PluginDescriptor.WHERE_PLUGINMENU, icon = "logo.png", fnc = main)]
