# AIO Panel 18.0.0 — instrukcja aktualizacji przez GitKrakena

## Zakres

Ta paczka zawiera **pełny kod źródłowy wtyczki** AIO Panel 18.0.0, nie tylko nowy katalog projektów. Jest to konieczne, gdyż gałąź `main` na GitHub zawiera obecnie 17.0.3 i nie ma wszystkich zmian SAT-only z wydania 17.0.4-r3 TEST.

Aktualizacji przez GitKraken nie wykonuje się w katalogu tunera. Operację przeprowadź w lokalnym klonie repozytorium `OliOli2013/PanelAIO-Plugin`.

### Krok 1 — przygotowanie

Zapisz/commituj lokalne niezapisane zmiany przed podmianą. W terminalu GitKrakena przejdź do katalogu repozytorium (podmień ścieżkę):

```bash
cd "$HOME/PanelAIO-Plugin"
git status
git pull --ff-only origin main
```

Jeżeli `git pull --ff-only` odmówi działania z uwagi na lokalne zmiany, **nie używaj** `git reset --hard`: najpierw je zachowaj.

### Krok 2 — nadpisanie plików 18.0.0

Dostosuj ścieżkę do ZIP w katalogu Pobrane:

```bash
unzip -o "$HOME/Pobrane/AIO_Panel_18.0.0_GITKRAKEN_PELNE_ZRODLA.zip" -d .
chmod +x build_ipk.sh
```

Archiwum zawiera pliki w układzie repozytorium. Nie usuwaj pozostałych plików repozytorium. Zobacz zmiany w GitKraken (`git diff --stat`).

### Krok 3 — weryfikacja i budowanie IPK + DEB

```bash
python3 core/python_syntax_check.py .
python3 core/selftest.py .
python3 tests/test_release_18.py .
./build_ipk.sh
sha256sum -c SHA256SUMS.txt
```

Wyniki znajdziesz w `release/`:

- `enigma2-plugin-extensions-panelaio_18.0.0_all.ipk`
- `enigma2-plugin-extensions-panelaio_18.0.0_all.deb`

`dpkg-deb` musi być dostępne na komputerze budującym. Uruchamianie testów nie instaluje wtyczki na tunerze.

### Krok 4 — commit i push

Zobacz zmiany, zatwierdź wszystkie pliki projektu (bez `release/`, jeśli ignorowane w `.gitignore`):

```bash
git status
git add -A
git commit -m "release: AIO Panel 18.0.0 - SAT-only, Moje projekty, OSCam"
git push origin main
```

W GitHub Releases utwórz tag `v18.0.0` i dołącz **osobno** pakiety IPK/DEB i plik SHA256SUMS.txt. `git push` sam nie tworzy wydania GitHub Releases.

## Instalacja na tunerze

- Obrazy OPKG: `opkg install /tmp/enigma2-plugin-extensions-panelaio_18.0.0_all.ipk`
- Obrazy DPKG: `dpkg -i /tmp/enigma2-plugin-extensions-panelaio_18.0.0_all.deb`

Po instalacji zrestartuj GUI Enigma2. Przed aktualizacją listy wykonaj kopię `/etc/enigma2/`.

## Ważne

- Aktualizacja SAT zachowuje istniejące DVB-T/T2, DVB-C, FAVOURITES oraz IPTV. Nie przywraca sama usług uszkodzonych przed instalacją.
- Levi45 jest pokazywany według oficjalnego źródła `levi-45/Levi45Emulator` (potwierdzone 11968, Emu r803). Jeśli aktualny odczyt nie działa, panel pokazuje tę wersję z dopiskiem daty ostatniej weryfikacji.
- OSCam-Emu z feedu jest innym sposobem instalacji. Wyświetlana wersja pochodzi z feedu danego tunera; nie wolno jej utożsamiać z Levi45.
- Udał się test r3 na Ustym 4K Pro w zakresie FAVOURITES; nowe menu 18.0.0 **nie było testowane na fizycznym tunerze**.
- Nie przeprowadzono wykonawczych testów Pythona 2 — sprawdzono składnię i zgodność kodu w dostępnym środowisku Pythona 3.
