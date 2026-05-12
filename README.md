# AIO Panel 12.0.1

AIO Panel dla Enigma2 / Python 2 i Python 3. Wersja 12.0.1 naprawia błąd ładowania wtyczki po wersji 12.0.4 oraz dodatkowo wzmacnia zgodność wyglądu z zewnętrznymi skinami.

## Najważniejsze zmiany wersji 12.0.1

- Naprawiono błąd: `name 'SOFTCAM_AND_PLUGINS_PL' is not defined`.
- Zabezpieczono `data/menus.py`, aby błąd importu nie wyłączał całej wtyczki w menu Enigma2.
- Wymuszono własną nazwę ekranu `PanelAIO`, aby skiny zewnętrzne nie podmieniały widoku przez ogólną nazwę `Panel`.
- Podniesiono `zPosition` ekranu głównego do 99.
- Wymieniono grafiki zaznaczenia na pełne, nieprzezroczyste PNG bez kanału alpha, aby aktywna funkcja była czytelna.
- Instalator TvMad Pro E2 nadal pozostaje całkowicie usunięty.

## Zachowane zmiany z poprzednich wersji

- Listy Bzyk83, JakiTaki, Anom i Paweł Pawełek są pobierane tylko z repozytorium PanelAIO-Lists.
- Listy starsze niż 2026 są ukrywane.
- Zachowano sortowanie list od najnowszej na górze.
- Dodano instalator Bouquet Maker Xtream.
- Poprawiono Backup/Restore Listy Kanałów.
- Czyszczenie niedziałających wtyczek usuwa wadliwe katalogi całkowicie.

## Instalacja z IPK

```sh
opkg remove enigma2-plugin-extensions-panelaio
opkg install /tmp/enigma2-plugin-extensions-panelaio_12.0.1_all.ipk
killall -9 enigma2
```

## Aktualizacja z GitHuba

```sh
wget -qO- https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh | /bin/sh
```

## Układ repozytorium

- `plugin.py` — entry point wtyczki
- `legacy_plugin.py` — główna logika i zgodność runtime
- `core/` — helpery systemowe, sieciowe i bezpieczeństwa
- `ui/` — ekrany i most do architektury modułowej
- `data/` — menu, tłumaczenia i skiny
- `installer.sh` — aktualizacja z GitHuba
