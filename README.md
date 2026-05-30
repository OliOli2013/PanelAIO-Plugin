# AIO Panel 12.0.3

AIO Panel dla Enigma2 / Python 2 i Python 3. Wersja 12.0.3 zachowuje bezpieczne, lekkie ładowanie z 12.0.2 i dodaje poprawki bez naruszania pozostałych funkcji wtyczki.

## Najważniejsze zmiany 12.0.3

- dodano w zakładce Softcamy funkcję `oscam.dvbapi - aktualizacja Poland`,
- funkcja korzysta z pliku `oscam.dvbapi.poland` dołączonego do paczki, więc działa offline,
- przed podmianą istniejącego `oscam.dvbapi` tworzona jest kopia zapasowa starego pliku,
- poprawiono Backup Listy Kanałów: lepsze wykrywanie zapisywalnego miejsca, kopia z datą oraz plik `aio_channels_backup.tar.gz` jako ostatnia kopia,
- poprawiono Restore Listy Kanałów: weryfikacja archiwum przed przywróceniem, awaryjna kopia obecnych list i bezpieczne przywracanie przez osobny skrypt, który działa także po zatrzymaniu GUI,
- zachowano poprawkę 12.0.2 ograniczającą ryzyko bootloopa na OpenATV 8 / beta.

## Instalacja z IPK

```sh
opkg remove enigma2-plugin-extensions-panelaio
opkg install /tmp/enigma2-plugin-extensions-panelaio_12.0.3_all.ipk
reboot
```

## Aktualizacja z GitHuba

```sh
wget -qO- https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh | /bin/sh
```

## Struktura repozytorium

- `plugin.py` — lekki i bezpieczny entry point ładowany przy starcie Enigma2,
- `legacy_plugin.py` — pełna logika AIO Panel ładowana dopiero po otwarciu wtyczki,
- `oscam.dvbapi.poland` — lokalny wzorzec dla funkcji aktualizacji Poland,
- `core/`, `ui/`, `data/` — moduły architektury AIO,
- `installer.sh` — aktualizacja z GitHuba.
