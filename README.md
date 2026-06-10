# AIO Panel 12.0.4

AIO Panel dla Enigma2 / Python 2 i Python 3. Wersja 12.0.4 jest aktualizacją stabilizacyjną po zgłoszeniach użytkowników dotyczących restartów, bootloopów oraz problemów na obrazach Python 2.

## Najważniejsze zmiany 12.0.4

- wyłączono zadania startowe wykonywane przy uruchamianiu GUI,
- zablokowano oczywiste instalatory Python 3 na obrazach Python 2,
- dodano potwierdzenie przed uruchamianiem zewnętrznych instalatorów, domyślnie ustawione na NIE,
- AIO Panel nie wymusza już automatycznego restartu GUI/odbiornika po instalatorach z menu,
- instalator GitHub nie wykonuje już automatycznego rebootu po aktualizacji,
- dodano czyszczenie starej lokalizacji `Extensions/PanelAIO` oraz plików `pyc/pyo`,
- zachowano funkcję `oscam.dvbapi - aktualizacja Poland`,
- zachowano poprawki Backup/Restore list kanałów z 12.0.3.

## Instalacja z IPK

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-panelaio_12.0.4_all.ipk
reboot
```

## Awaryjne usunięcie starej wersji

```sh
init 4
opkg remove enigma2-plugin-extensions-panelaio 2>/dev/null
rm -rf /usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO
rm -rf /usr/lib/enigma2/python/Plugins/Extensions/PanelAIO
find /usr/lib/enigma2/python/Plugins -type d -name __pycache__ -exec rm -rf {} \; 2>/dev/null
find /usr/lib/enigma2/python/Plugins -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null
sync
init 3
```

## Pliki

- `plugin.py` — lekki entry point bez zadań startowych,
- `legacy_plugin.py` — pełna logika AIO Panel ładowana dopiero po otwarciu,
- `oscam.dvbapi.poland` — lokalny wzorzec dla funkcji aktualizacji Poland,
- `installer.sh` — bezpieczny instalator GitHub bez wymuszonego rebootu.
