# AIO Panel 14.0.1

AIO Panel is a universal Enigma2 toolbox for receivers running Python 2 or Python 3. Version 14.0.1 is the stabilized release of the 14.x line. It retains the adaptive dashboard and all existing functions while consolidating fixes for picons, channel-list installation, S4aUpdater and Super Configurator.

## Main areas

- channel lists and bouquet installation,
- Softcam and Oscam tools,
- online plugin installers,
- first-installation configurator,
- system tools, feed and repository management,
- channel-list and Oscam backup/restore,
- skins, diagnostics, cleanup and security tools,
- plugin update and compatibility information.

## Modern interface

- separate layouts for compact, HD and Full HD desktops,
- PNG pictograms independent of receiver font and emoji support,
- category navigation, central action list and a live details panel,
- CPU, RAM, flash, network, image and Python information,
- automatic Polish interface on Polish Enigma2 systems and English on other languages,
- manual language switching: Red — Polish, Green — English,
- Yellow — restart GUI, Blue — AIO Panel update, INFO — support QR.

## E2 Doctor

E2 Doctor is available in Online Plugins and is installed with:

```sh
wget -q -O - https://raw.githubusercontent.com/OliOli2013/E2-Doctor-Plugin/main/installer.sh | /bin/sh
```

Because E2 Doctor requires Python 3, the entry is hidden automatically on Python 2 images.

## Online installation

```sh
wget -q -O - https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh | /bin/sh
```

The installer does not force an automatic reboot.

Author: **by Paweł Pawełek**  
Contact: **aio-iptv@wp.pl**
