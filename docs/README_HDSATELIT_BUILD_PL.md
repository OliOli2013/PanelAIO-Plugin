# AIO Panel — edycja HD Satelit

**Autor: Paweł Pawełek | AIO Team**
Repozytorium źródłowe: https://github.com/OliOli2013/PanelAIO-Plugin

## Cel

Jeden kod AIO Panel, dwa warianty wydania. Nowy skrypt `tools/build_hdsatelit.py` tworzy oddzielną edycję do oficjalnego feedu HD Satelit. **Nie modyfikuje bazowego repozytorium, jego plików, głównych wersji IPK/DEB ani działającego tunera.**

Wariant HD Satelit wyklucza pobieranie SoftCam.Key, instalację narzędzi FuryBiss/BISS i samodzielną aktualizację AIO Panel przez GitHub. W rewizji hds2 nie instaluje również zewnętrznego feedu Softcam przez HTTP, nie uruchamia go z instalatora OSCam ani SuperKonfiguratora oraz nie oferuje instalatorów Jihad FHD i Adult XXX. W rewizji hds2 nie instaluje również zewnętrznego feedu Softcam przez HTTP, nie uruchamia go z instalatora OSCam ani SuperKonfiguratora oraz nie oferuje instalatorów Jihad FHD i Adult XXX. Zabezpieczenia są w menu, dyspozytorze akcji, klasach wykonujących kod, Python CLI i skryptach powłoki. Aktualizacje samego AIO Panel mają przebiegać przez OPKG/feed HD Satelit. W menedżerze aktualizacji innych wtyczek dozwolone pozostają aktualizacje przez OPKG.

**OSCam z istniejących repozytoriów systemu, SuperKonfigurator, listy kanałów, picony, EPG i pozostałe dozwolone funkcje zostają.** Instalator OSCam nie wykonuje już `--force-overwrite` i nie dodaje zewnętrznego feedu. W plikach zachowane są autorstwo i tekst licencji GPL v3.

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
6. `git status --short`, `git diff --check`, następnie Commit (w GitKraken), Push na GitHub. Proponowana wiadomość commit: `AIO Panel HD Satelit hds2: disable external Softcam feed, Jihad and Adult XXX`.
7. Twórcom przekaż link do zatwierdzonego commita lub taga. Budują z głównych źródeł; nie potrzebują osobnej, ręcznie utrzymywanej kopii panelu.

## Wyniki budowania

- `dist-hdsatelit/enigma2-plugin-extensions-panelaio_18.0.0+hds2_all.ipk`
- `dist-hdsatelit/enigma2-plugin-extensions-panelaio_18.0.0+hds2_all.deb`
- `dist-hdsatelit/aio-panel-hdsatelit-source.zip` — źródła po zastosowaniu profilu HD Satelit, do audytu i BitBake
- `dist-hdsatelit/SHA256SUMS.txt` — kontrola sum

## Test na SF8008

Na próbę skopiuj testowy plik IPK do `/tmp` tunera. Zadbaj o backup `/etc/enigma2` i zachowanie slotu z działającym systemem. Zainstaluj:

```sh
opkg install /tmp/enigma2-plugin-extensions-panelaio_18.0.0+hds2_all.ipk
```

Jeżeli OPKG zgłasza brak `enigma2`, obraz 0.7.2 nadal potrzebuje zgodnego pakietu `Provides: enigma2`; w wersji 0.7.3 twórcy zapowiedzieli poprawkę `RPROVIDES`. **Nie używaj `--force-depends`.**

W GUI sprawdź brak opcji pobierania kluczy, FuryBiss, Softcam – Installer, Jihad FHD i Adult XXX, wyłączenie samodzielnej aktualizacji z GitHub, zachowanie OSCam i SuperKonfiguratora, kopii, list, piconów, EPG i diagnostyki. Dodatkowo sprawdź, czy nie pojawiają się błędy przy wyjściu z wtyczki i ponownym uruchomieniu.

Testy statyczne i budowy hds2 przeszły na kodzie AIO Panel 18.0.0. **Fizycznych testów tej edycji jeszcze nie wykonano.**

## Ważne

- Plik `aio-panel-hdsatelit-source.zip` to już przekształcona edycja; do kolejnych budowań używaj oryginalnego repozytorium z `tools/build_hdsatelit.py`.
- Nie publikuj wariantu jako oficjalnego bez zgody HD Satelit i ich testów feedu.
- Po zmianach źródła w następnych wersjach skrypt zatrzyma budowanie, gdy nie odnajdzie wymaganych punktów bezpieczeństwa. Należy wówczas przejrzeć nowe ścieżki pobierania i aktualizacji.
- Skrypt nie ogranicza uprawnień systemowych samodzielnego użytkownika root. Nie jest mechanizmem kontroli dostępu w Linux; wyłącza funkcje oferowane przez wydawany pakiet AIO Panel.

### Dodatkowe wymagania HD Satelit — hds2

Wyłącznie w generowanym wariancie HD Satelit usunięto instalator zewnętrznego feedu Softcam HTTP, jego automatyczne uruchamianie w instalatorze OSCam oraz odpowiadający mu krok SuperKonfiguratora. Usunięto też instalatory Jihad FHD i Adult XXX oraz powiązane wpisy w rejestrze zaufanych skryptów. Instalowanie OSCam z repozytoriów już skonfigurowanych w systemie pozostaje dostępne, bez automatycznego dodawania feedów i bez obejścia konfliktów pakietów przez `--force-overwrite`.

**Uwaga:** zmiana wydania AIO Panel nie usuwa z odbiornika repozytoriów, które mogły zostać dodane wcześniej przez pełną wersję lub inne narzędzia. Przed publikacją HD Satelit powinien zweryfikować stan `/etc/opkg/` na testowym odbiorniku. Skrypt celowo nie kasuje istniejących konfiguracji OPKG bez wiedzy właściciela.
