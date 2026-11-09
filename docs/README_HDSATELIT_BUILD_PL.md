# AIO Panel — edycja HD Satelit

**Autor: Paweł Pawełek | AIO Team**
Repozytorium źródłowe: https://github.com/OliOli2013/PanelAIO-Plugin

## Cel

Jeden kod AIO Panel, dwa warianty wydania. Nowy skrypt `tools/build_hdsatelit.py` tworzy oddzielną edycję do oficjalnego feedu HD Satelit. **Nie modyfikuje bazowego repozytorium, jego plików, głównych wersji IPK/DEB ani działającego tunera.**

Wariant HD Satelit wyklucza pobieranie SoftCam.Key, instalację narzędzi FuryBiss/BISS i samodzielną aktualizację AIO Panel przez GitHub. Zabezpieczenia są w menu, dyspozytorze akcji, klasach wykonujących kod, Python CLI i skryptach powłoki. Aktualizacje samego AIO Panel mają przebiegać przez OPKG/feed HD Satelit. W menedżerze aktualizacji innych wtyczek dozwolone pozostają aktualizacje przez OPKG.

**OSCam, SuperKonfigurator, listy kanałów, picony, EPG i pozostałe dozwolone funkcje zostają.** W plikach zachowane są autorstwo i tekst licencji GPL v3.

To nie jest gwarancja, że zewnętrzna, osobno instalowana wtyczka nigdy nie będzie obsługiwała kluczy: AIO Panel nie kontroluje kodu obcych programów.

## Instalacja nowych narzędzi w repozytorium przez GitKraken

1. Otwórz lokalne repozytorium `PanelAIO-Plugin` w GitKraken.
2. Otwórz Terminal i sprawdź `git status --short` — zabezpiecz niezapisane zmiany przed rozpoczęciem.
3. Rozpakuj ZIP z paczką narzędzi. Skopiuj katalogi `tools` i `docs` z jej folderu `DO_REPOZYTORIUM` do katalogu głównego repozytorium. **Nie kopiuj testowego IPK do źródeł i nie zamieniaj `runtime.py` w standardowej wersji.**
4. Uruchom kontrolę i budowanie:

```sh
python3 tools/build_hdsatelit.py --edition hdsatelit --source . --out dist-hdsatelit
python3 tools/test_hdsatelit.py --out dist-hdsatelit
```

Wymagane: Python 3.8+, `ar`, `/bin/sh`, opcjonalnie `dpkg-deb` dla formatu DEB.

5. Aby uniknąć publikacji wyników budowania w repozytorium, dodaj do `.gitignore` wpis `dist-hdsatelit/` (jeśli go brakuje).
6. `git status --short`, `git diff --check`, następnie Commit (w GitKraken), Push na GitHub. Proponowana wiadomość commit: `AIO Panel: add HD Satelit feed build profile with no key downloads or self-update`.
7. Twórcom przekaż link do zatwierdzonego commita lub taga. Budują z głównych źródeł; nie potrzebują osobnej, ręcznie utrzymywanej kopii panelu.

## Wyniki budowania

- `dist-hdsatelit/enigma2-plugin-extensions-panelaio_18.0.0+hds1_all.ipk`
- `dist-hdsatelit/enigma2-plugin-extensions-panelaio_18.0.0+hds1_all.deb`
- `dist-hdsatelit/aio-panel-hdsatelit-source.zip` — źródła po zastosowaniu profilu HD Satelit, do audytu i BitBake
- `dist-hdsatelit/SHA256SUMS.txt` — kontrola sum

## Test na SF8008

Na próbę skopiuj testowy plik IPK do `/tmp` tunera. Zadbaj o backup `/etc/enigma2` i zachowanie slotu z działającym systemem. Zainstaluj:

```sh
opkg install /tmp/enigma2-plugin-extensions-panelaio_18.0.0+hds1_all.ipk
```

Jeżeli OPKG zgłasza brak `enigma2`, obraz 0.7.2 nadal potrzebuje zgodnego pakietu `Provides: enigma2`; w wersji 0.7.3 twórcy zapowiedzieli poprawkę `RPROVIDES`. **Nie używaj `--force-depends`.**

W GUI sprawdź brak opcji pobierania kluczy i FuryBiss, wyłączenie samodzielnej aktualizacji z GitHub, zachowanie OSCam i SuperKonfiguratora, kopii, list, piconów, EPG i diagnostyki. Dodatkowo sprawdź, czy nie pojawiają się błędy przy wyjściu z wtyczki i ponownym uruchomieniu.

Testy statyczne i budowy przeszły na kodzie AIO Panel 18.0.0. **Fizycznych testów tej edycji jeszcze nie wykonano.**

## Ważne

- Plik `aio-panel-hdsatelit-source.zip` to już przekształcona edycja; do kolejnych budowań używaj oryginalnego repozytorium z `tools/build_hdsatelit.py`.
- Nie publikuj wariantu jako oficjalnego bez zgody HD Satelit i ich testów feedu.
- Po zmianach źródła w następnych wersjach skrypt zatrzyma budowanie, gdy nie odnajdzie wymaganych punktów bezpieczeństwa. Należy wówczas przejrzeć nowe ścieżki pobierania i aktualizacji.
- Skrypt nie ogranicza uprawnień systemowych samodzielnego użytkownika root. Nie jest mechanizmem kontroli dostępu w Linux; wyłącza funkcje oferowane przez wydawany pakiet AIO Panel.
