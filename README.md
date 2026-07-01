# AIO Panel 13.0.1

AIO Panel dla Enigma2 — pakiet funkcji do list kanałów, softcamów, wtyczek online, konfiguracji, narzędzi systemowych, skinów, backupu i diagnostyki.

## Zmiany w wersji 13.0.1

- Zmieniono instalator skina **Fury FHD** na nowe polecenie:

```sh
wget -q "--no-check-certificate" https://raw.githubusercontent.com/islam-2412/IPKS/refs/heads/main/fury/installer.sh -O - | /bin/sh
```

- Usunięto z menu pozycję **Czyszczenie niedziałających wtyczek**.
- Zaktualizowano lokalny plik **oscam.dvbapi.poland** używany przez funkcję **oscam.dvbapi - aktualizacja Poland**.
- Ustawiono instalator **PP Channel Sync** na polecenie:

```sh
wget -q -O - https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main/installer.sh | /bin/sh
```

- Pozostałe funkcje zostały zachowane bez zmian względem wersji 13.0.0.

## Instalacja IPK

Wgraj paczkę do katalogu `/tmp`, a następnie wykonaj:

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-panelaio_13.0.1_all.ipk
```

Po instalacji wykonaj ręczny restart GUI.

## Repozytorium

```text
https://github.com/OliOli2013/PanelAIO-Plugin
```

Autor: Paweł Pawełek  
Kontakt: aio-iptv@wp.pl
