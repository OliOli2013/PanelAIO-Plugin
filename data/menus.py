# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

"""Static menu payloads separated from the legacy monolith.

This file contains all section definitions moved out into a dedicated data module,
so future refactors can work against a stable menu registry instead of scraping the
legacy implementation.
"""

SOFTCAM_AND_PLUGINS_PL = [('\\c00FFD200--- Softcamy ---\\c00ffffff', 'SEPARATOR'), ('🔄 Restart Oscam', 'CMD:RESTART_OSCAM'), ('🧹 Kasuj hasło Oscam', 'CMD:CLEAR_OSCAM_PASS'), ('⚙️ oscam.dvbapi - kasowanie zawartości', 'CMD:MANAGE_DVBAPI'), ('🔄 Aktualizuj oscam.srvid/srvid2', 'CMD:UPDATE_SRVID'), ('🔑 Aktualizuj SoftCam.Key (Online)', 'CMD:INSTALL_SOFTCAMKEY_ONLINE'), ('📥 Softcam - Instalator', 'CMD:INSTALL_SOFTCAM_SCRIPT'), ('📥 Oscam Feed - Instalator (Auto)', 'CMD:INSTALL_BEST_OSCAM'), ('📥 NCam (Feed - najnowszy)', 'CMD:INSTALL_NCAM_FEED'), ('\\c00FFD200--- Wtyczki Online ---\\c00ffffff', 'SEPARATOR'), ('📺 XStreamity - Instalator', 'bash_raw:opkg update && opkg install enigma2-plugin-extensions-xstreamity'), ('📺 IPTV Dream - Instalator', 'CMD:INSTALL_IPTV_DREAM'), ('⚙️ ServiceApp - Instalator', 'CMD:INSTALL_SERVICEAPP'), ('📦 Konfiguracja IPTV - zależności', 'CMD:IPTV_DEPS'), ('⚙️ StreamlinkProxy - Instalator', 'bash_raw:opkg update && opkg install enigma2-plugin-extensions-streamlinkproxy'), ('🛠 AJPanel - Instalator', 'bash_raw:wget https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh -O - | /bin/sh'), ('▶️ E2iPlayer Master - Instalacja/Aktualizacja', "bash_raw:wget -q 'https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh' -O - | /bin/sh"), ('📅 EPG Import - Instalator', 'bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh -O - | /bin/bash'), ('📺 Simple IPTV EPG - Instalator', 'bash_raw:wget -qO - https://raw.githubusercontent.com/OliOli2013/SimpleIPTV_EPG/main/installer.sh | /bin/sh'), ('📻 NeoRadio Online - Instalator', 'bash_raw:wget -O /tmp/neoradio.ipk https://github.com/OliOli2013/NeoRadio/releases/latest/download/enigma2-plugin-extensions-neoradio_all.ipk && opkg install /tmp/neoradio.ipk && killall -9 enigma2'), ('🔄 S4aUpdater - Instalator', 'bash_raw:wget http://s4aupdater.one.pl/instalujs4aupdater.sh -O - | /bin/sh'), ('🔄 MyUpdater v5.1 - Instalator', 'bash_raw:wget -q -O - https://raw.githubusercontent.com/OliOli2013/MyUpdater-Plugin/main/installer.sh | sh'), ('📺 JediMakerXtream - Instalator', 'bash_raw:wget https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh -O - | /bin/sh'), ('▶️ YouTube - Instalator', 'bash_raw:opkg install https://github.com/Taapat/enigma2-plugin-youtube/releases/download/git1294/enigma2-plugin-extensions-youtube_py3-git1294-cbcf8b0-r0.0.ipk'), ('📦 J00zeks Feed (Repo Installer)', 'CMD:INSTALL_J00ZEK_REPO'), ('📺 E2Kodi v2 - Instalator (j00zek)', 'CMD:INSTALL_E2KODI'), ('🖼️ Picon Updater - Instalator (Picony)', 'bash_raw:wget -qO - https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh | /bin/sh'), ('🖼️ ChocholousekPicons - Instalator', "bash_raw:wget -qO- --no-check-certificate 'https://github.com/s3n0/e2plugins/raw/master/ChocholousekPicons/online-setup' | bash -s install"), ('🔑 CIEFP Oscam Editor - Instalator', "bash_raw:wget -q --no-check-certificate 'https://raw.githubusercontent.com/ciefp/CiefpOscamEditor/main/installer.sh' -O - | /bin/sh"), ('📺 e-stralker - Instalator (feed)', 'bash_raw:opkg update && (opkg install enigma2-plugin-extensions-estalker || opkg install enigma2-plugin-extensions-e-stralker || opkg install enigma2-plugin-extensions-e-stalker || (PKG=$(opkg list | awk \'BEGIN{IGNORECASE=1} $1 ~ /^enigma2-plugin-extensions-estalker$/ {print $1; exit}\'); [ -z \\"$PKG\\" ] && PKG=$(opkg list | awk \'BEGIN{IGNORECASE=1} $1 ~ /estalker/ {print $1; exit}\'); [ -z \\"$PKG\\" ] && PKG=$(opkg list | awk \'BEGIN{IGNORECASE=1} $1 ~ /stalker/ {print $1; exit}\'); [ -n \\"$PKG\\" ] && opkg install $PKG || (echo \'Nie znaleziono EStalker w feedach (opkg).\'; exit 1)))'), ('▶️ VAVOO - Instalator', 'bash_raw:wget -q "--no-check-certificate" https://raw.githubusercontent.com/Belfagor2005/vavoo/main/installer.sh -O - | /bin/sh'), ('📺 TV Garden - Instalator', 'bash_raw:wget -q --no-check-certificate "https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/installer.sh" -O - | /bin/sh'), ('🔎 Simple ZOOM Panel - Instalator', 'bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/SimpleZooomPanel/main/installer.sh -O - | /bin/sh'), ('⚽ FootOnsat - Instalator', 'bash_raw:wget https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh -O - | /bin/sh')]


SOFTCAM_AND_PLUGINS_EN = [('\\c00FFD200--- Softcams ---\\c00ffffff', 'SEPARATOR'), ('🔄 Restart Oscam', 'CMD:RESTART_OSCAM'), ('🧹 Clear Oscam Password', 'CMD:CLEAR_OSCAM_PASS'), ('⚙️ oscam.dvbapi - clear file', 'CMD:MANAGE_DVBAPI'), ('🔄 Update oscam.srvid/srvid2', 'CMD:UPDATE_SRVID'), ('🔑 Update SoftCam.Key (Online)', 'CMD:INSTALL_SOFTCAMKEY_ONLINE'), ('📥 Softcam - Installer', 'CMD:INSTALL_SOFTCAM_SCRIPT'), ('📥 Oscam Feed - Installer (Auto)', 'CMD:INSTALL_BEST_OSCAM'), ('📥 NCam (Feed - latest)', 'CMD:INSTALL_NCAM_FEED'), ('\\c00FFD200--- Online Plugins ---\\c00ffffff', 'SEPARATOR'), ('📺 XStreamity - Installer', 'bash_raw:opkg update && opkg install enigma2-plugin-extensions-xstreamity'), ('📺 IPTV Dream - Installer', 'CMD:INSTALL_IPTV_DREAM'), ('⚙️ ServiceApp - Installer', 'CMD:INSTALL_SERVICEAPP'), ('📦 IPTV Configuration - dependencies', 'CMD:IPTV_DEPS'), ('⚙️ StreamlinkProxy - Installer', 'bash_raw:opkg update && opkg install enigma2-plugin-extensions-streamlinkproxy'), ('🛠 AJPanel - Installer', 'bash_raw:wget https://raw.githubusercontent.com/AMAJamry/AJPanel/main/installer.sh -O - | /bin/sh'), ('▶️ E2iPlayer Master - Install/Update', "bash_raw:wget -q 'https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh' -O - | /bin/sh"), ('📅 EPG Import - Installer', 'bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer.sh -O - | /bin/bash'), ('📺 Simple IPTV EPG - Installer', 'bash_raw:wget -qO - https://raw.githubusercontent.com/OliOli2013/SimpleIPTV_EPG/main/installer.sh | /bin/sh'), ('📻 NeoRadio Online - Installer', 'bash_raw:wget -O /tmp/neoradio.ipk https://github.com/OliOli2013/NeoRadio/releases/latest/download/enigma2-plugin-extensions-neoradio_all.ipk && opkg install /tmp/neoradio.ipk && killall -9 enigma2'), ('🔄 S4aUpdater - Installer', 'bash_raw:wget http://s4aupdater.one.pl/instalujs4aupdater.sh -O - | /bin/sh'), ('🔄 MyUpdater v5.1 - Installer', 'bash_raw:wget -q -O - https://raw.githubusercontent.com/OliOli2013/MyUpdater-Plugin/main/installer.sh | sh'), ('📺 JediMakerXtream - Installer', 'bash_raw:wget https://raw.githubusercontent.com/biko-73/JediMakerXtream/main/installer.sh -O - | /bin/sh'), ('▶️ YouTube - Installer', 'bash_raw:opkg install https://github.com/Taapat/enigma2-plugin-youtube/releases/download/git1294/enigma2-plugin-extensions-youtube_py3-git1294-cbcf8b0-r0.0.ipk'), ('📦 J00zeks Feed (Repo Installer)', 'CMD:INSTALL_J00ZEK_REPO'), ('📺 E2Kodi v2 - Installer (j00zek)', 'CMD:INSTALL_E2KODI'), ('🖼️ Picon Updater - Installer (Picons)', 'bash_raw:wget -qO - https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh | /bin/sh'), ('🖼️ ChocholousekPicons - Installer', "bash_raw:wget -qO- --no-check-certificate 'https://github.com/s3n0/e2plugins/raw/master/ChocholousekPicons/online-setup' | bash -s install"), ('🔑 CIEFP Oscam Editor - Installer', "bash_raw:wget -q --no-check-certificate 'https://raw.githubusercontent.com/ciefp/CiefpOscamEditor/main/installer.sh' -O - | /bin/sh"), ('📺 e-stralker - Installer (feed)', 'bash_raw:opkg update && (opkg install enigma2-plugin-extensions-estalker || opkg install enigma2-plugin-extensions-e-stralker || opkg install enigma2-plugin-extensions-e-stalker || (PKG=$(opkg list | awk \'BEGIN{IGNORECASE=1} $1 ~ /^enigma2-plugin-extensions-estalker$/ {print $1; exit}\'); [ -z \\"$PKG\\" ] && PKG=$(opkg list | awk \'BEGIN{IGNORECASE=1} $1 ~ /estalker/ {print $1; exit}\'); [ -z \\"$PKG\\" ] && PKG=$(opkg list | awk \'BEGIN{IGNORECASE=1} $1 ~ /stalker/ {print $1; exit}\'); [ -n \\"$PKG\\" ] && opkg install $PKG || (echo \'EStalker not found in feeds (opkg).\'; exit 1)))'), ('▶️ VAVOO - Installer', 'bash_raw:wget -q "--no-check-certificate" https://raw.githubusercontent.com/Belfagor2005/vavoo/main/installer.sh -O - | /bin/sh'), ('📺 TV Garden - Installer', 'bash_raw:wget -q --no-check-certificate "https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/installer.sh" -O - | /bin/sh'), ('🔎 Simple ZOOM Panel - Installer', 'bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/SimpleZooomPanel/main/installer.sh -O - | /bin/sh'), ('⚽ FootOnsat - Installer', 'bash_raw:wget https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh -O - | /bin/sh')]


SYSTEM_TOOLS_PL = [('\\c00FFD200--- Konfigurator ---\\c00ffffff', 'SEPARATOR'), ('✨ Super Konfigurator (Pierwsza Instalacja)', 'CMD:SUPER_SETUP_WIZARD'), ('👁️ Widoczność w menu tunera (ON/OFF)', 'CMD:TOGGLE_MENU_VISIBILITY'), ('\\c00FFD200--- Narzędzia Systemowe ---\\c00ffffff', 'SEPARATOR'), ('🗑️ Menadżer Deinstalacji', 'CMD:UNINSTALL_MANAGER'), ('🔎 Sprawdź aktualizacje zainstalowanych wtyczek', 'CMD:PLUGIN_UPDATE_MANAGER'), ('📡 Aktualizuj satellites.xml', 'CMD:UPDATE_SATELLITES_XML'), ('🖼️ Pobierz Picony (Transparent)', 'archive:https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip'), ('📊 Monitor Systemowy', 'CMD:SYSTEM_MONITOR'), ('📄 Przeglądarka Logów', 'CMD:LOG_VIEWER'), ('⏰ Menedżer Cron', 'CMD:CRON_MANAGER'), ('🔌 Menedżer Usług', 'CMD:SERVICE_MANAGER'), ('ℹ️ Informacje o Systemie', 'CMD:SYSTEM_INFO'), ('\\c00FFD200--- Feedy / Repozytoria ---\\c00ffffff', 'SEPARATOR'), ('🌐 Menedżer Feedów / Repozytoriów', 'CMD:FEED_MANAGER'), ('\\c00FFD200--- Naprawa i Backup ---\\c00ffffff', 'SEPARATOR'), ('🛠 Tryb Naprawy po Instalacji', 'CMD:POSTINSTALL_REPAIR'), ('💾 Backup Listy Kanałów', 'CMD:BACKUP_LIST'), ('💾 Backup Konfiguracji Oscam', 'CMD:BACKUP_OSCAM'), ('♻️ Restore Listy Kanałów', 'CMD:RESTORE_LIST'), ('♻️ Restore Konfiguracji Oscam', 'CMD:RESTORE_OSCAM')]


SYSTEM_TOOLS_EN = [('\\c00FFD200--- Configurator ---\\c00ffffff', 'SEPARATOR'), ('✨ Super Setup Wizard (First Installation)', 'CMD:SUPER_SETUP_WIZARD'), ('👁️ Show in receiver menu (ON/OFF)', 'CMD:TOGGLE_MENU_VISIBILITY'), ('\\c00FFD200--- System Tools ---\\c00ffffff', 'SEPARATOR'), ('🗑️ Uninstallation Manager', 'CMD:UNINSTALL_MANAGER'), ('🔎 Check updates for installed plugins', 'CMD:PLUGIN_UPDATE_MANAGER'), ('📡 Update satellites.xml', 'CMD:UPDATE_SATELLITES_XML'), ('🖼️ Download Picons (Transparent)', 'archive:https://github.com/OliOli2013/PanelAIO-Plugin/raw/main/Picony.zip'), ('📊 System Monitor', 'CMD:SYSTEM_MONITOR'), ('📄 Log Viewer', 'CMD:LOG_VIEWER'), ('⏰ Cron Manager', 'CMD:CRON_MANAGER'), ('🔌 Service Manager', 'CMD:SERVICE_MANAGER'), ('ℹ️ System Information', 'CMD:SYSTEM_INFO'), ('\\c00FFD200--- Feeds / Repositories ---\\c00ffffff', 'SEPARATOR'), ('🌐 Feed / Repository Manager', 'CMD:FEED_MANAGER'), ('\\c00FFD200--- Repair & Backup ---\\c00ffffff', 'SEPARATOR'), ('🛠 Post-Install Repair Mode', 'CMD:POSTINSTALL_REPAIR'), ('💾 Backup Channel List', 'CMD:BACKUP_LIST'), ('💾 Backup Oscam Config', 'CMD:BACKUP_OSCAM'), ('♻️ Restore Channel List', 'CMD:RESTORE_LIST'), ('♻️ Restore Oscam Config', 'CMD:RESTORE_OSCAM')]


SKINS_PL = [('🎨 Algare FHD - Instalator', 'bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/popking159/skins/refs/heads/main/aglarepli/installer.sh -O - | /bin/sh'), ('🎨 Fury FHD - Instalator', 'bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh -O - | /bin/sh'), ('🎨 Luka FHD - Instalator', 'bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/popking159/skins/refs/heads/main/lukapli/installer.sh -O - | /bin/sh'), ('🎨 Maxy FHD - Instalator', 'bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/popking159/skins/refs/heads/main/maxyatv/installer.sh -O - | /bin/sh'), ('🎨 XDreamy - Instalator', 'bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Insprion80/Skins/main/xDreamy/installer.sh -O - | /bin/sh')]


SKINS_EN = [('🎨 Algare FHD - Installer', 'bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/popking159/skins/refs/heads/main/aglarepli/installer.sh -O - | /bin/sh'), ('🎨 Fury FHD - Installer', 'bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh -O - | /bin/sh'), ('🎨 Luka FHD - Installer', 'bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/popking159/skins/refs/heads/main/lukapli/installer.sh -O - | /bin/sh'), ('🎨 Maxy FHD - Installer', 'bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/popking159/skins/refs/heads/main/maxyatv/installer.sh -O - | /bin/sh'), ('🎨 XDreamy - Installer', 'bash_raw:wget -q --no-check-certificate https://raw.githubusercontent.com/Insprion80/Skins/main/xDreamy/installer.sh -O - | /bin/sh')]


DIAGNOSTICS_PL = [('\\c00FFD200--- Informacje i Aktualizacje ---\\c00ffffff', 'SEPARATOR'), ('ℹ️ Informacje o AIO Panel', 'CMD:SHOW_AIO_INFO'), ('🔄 Aktualizacja Wtyczki', 'CMD:CHECK_FOR_UPDATES'), ('\\c00FFD200--- AIO Extra ---\\c00ffffff', 'SEPARATOR'), ('⭐ AIO Szybki Start / Polecane', 'CMD:AIO_QUICKSTART'), ('🧪 Test zgodności systemu', 'CMD:COMPATIBILITY_CHECK'), ('💡 Tip dnia AIO', 'CMD:SHOW_AIO_TIP'), ('📜 Lokalny changelog', 'CMD:LOCAL_CHANGELOG'), ('\\c00FFD200--- Diagnostyka ---\\c00ffffff', 'SEPARATOR'), ('🌐 Diagnostyka Sieci', 'CMD:NETWORK_DIAGNOSTICS'), ('💾 Wolne miejsce (dysk/flash)', 'CMD:FREE_SPACE_DISPLAY'), ('\\c00FFD200--- Czyszczenie i Bezpieczeństwo ---\\c00ffffff', 'SEPARATOR'), ('⏱️ Auto RAM Cleaner (Konfiguruj)', 'CMD:SETUP_AUTO_RAM'), ('🧹 Wyczyść Pamięć Tymczasową', 'CMD:CLEAR_TMP_CACHE'), ('🧹 Smart Cleanup (TMP/LOG/CACHE)', 'CMD:SMART_CLEANUP'), ('🧹 Wyczyść Pamięć RAM', 'CMD:CLEAR_RAM_CACHE'), ('🔑 Kasuj hasło FTP', 'CMD:CLEAR_FTP_PASS'), ('🔑 Ustaw Hasło FTP', 'CMD:SET_SYSTEM_PASSWORD')]


DIAGNOSTICS_EN = [('\\c00FFD200--- Info & Updates ---\\c00ffffff', 'SEPARATOR'), ('ℹ️ About AIO Panel', 'CMD:SHOW_AIO_INFO'), ('🔄 Update Plugin', 'CMD:CHECK_FOR_UPDATES'), ('\\c00FFD200--- AIO Extras ---\\c00ffffff', 'SEPARATOR'), ('⭐ AIO Quick Start / Recommended', 'CMD:AIO_QUICKSTART'), ('🧪 System compatibility check', 'CMD:COMPATIBILITY_CHECK'), ('💡 AIO tip of the day', 'CMD:SHOW_AIO_TIP'), ('📜 Local changelog', 'CMD:LOCAL_CHANGELOG'), ('\\c00FFD200--- Diagnostics ---\\c00ffffff', 'SEPARATOR'), ('🌐 Network Diagnostics', 'CMD:NETWORK_DIAGNOSTICS'), ('💾 Free Space (disk/flash)', 'CMD:FREE_SPACE_DISPLAY'), ('\\c00FFD200--- Cleaning & Security ---\\c00ffffff', 'SEPARATOR'), ('⏱️ Auto RAM Cleaner (Setup)', 'CMD:SETUP_AUTO_RAM'), ('🧹 Clear Temporary Cache', 'CMD:CLEAR_TMP_CACHE'), ('🧹 Smart Cleanup (TMP/LOG/CACHE)', 'CMD:SMART_CLEANUP'), ('🧹 Clear RAM Cache', 'CMD:CLEAR_RAM_CACHE'), ('🔑 Clear FTP Password', 'CMD:CLEAR_FTP_PASS'), ('🔑 Set FTP Password', 'CMD:SET_SYSTEM_PASSWORD')]



SECTION_GROUPS = {
    'PL': [
        ('softcams_plugins', SOFTCAM_AND_PLUGINS_PL),
        ('system_tools', SYSTEM_TOOLS_PL),
        ('skins', SKINS_PL),
        ('diagnostics', DIAGNOSTICS_PL),
    ],
    'EN': [
        ('softcams_plugins', SOFTCAM_AND_PLUGINS_EN),
        ('system_tools', SYSTEM_TOOLS_EN),
        ('skins', SKINS_EN),
        ('diagnostics', DIAGNOSTICS_EN),
    ],
}

def strip_color_codes(value):
    import re
    value = value or ''
    return re.sub(r'\\c[0-9A-Fa-f]{8}', '', value)

def clean_section_title(raw_title):
    value = strip_color_codes(raw_title).replace('—', '-')
    value = value.strip().strip('-').strip()
    value = value.lstrip('-').rstrip('-').strip()
    return value

def split_sections(items, fallback_title):
    sections = []
    current_title = None
    current_items = []
    for name, action in items:
        if action == 'SEPARATOR':
            if current_title is not None and current_items:
                sections.append((current_title, current_items))
            current_title = clean_section_title(name) or fallback_title
            current_items = []
            continue
        if current_title is None:
            current_title = fallback_title
        current_items.append((name, action))
    if current_title is not None and current_items:
        sections.append((current_title, current_items))
    return sections

def build_static_tabs(lang='PL'):
    lang = 'PL' if lang == 'PL' else 'EN'
    tab_defs = []
    for key, items in SECTION_GROUPS[lang]:
        if key == 'skins':
            fallback = 'Skins / Skórki' if lang == 'PL' else 'Skins'
        elif key == 'softcams_plugins':
            fallback = 'Softcamy / Wtyczki' if lang == 'PL' else 'Softcams / Plugins'
        elif key == 'system_tools':
            fallback = 'Narzędzia systemowe' if lang == 'PL' else 'System tools'
        else:
            fallback = 'Informacje / Diagnostyka' if lang == 'PL' else 'Info / Diagnostics'
        tab_defs.extend(split_sections(items, fallback))
    return tab_defs
