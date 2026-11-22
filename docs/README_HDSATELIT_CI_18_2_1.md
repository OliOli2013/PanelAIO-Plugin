# AIO Panel – HD Satelit (hds2), od wersji 18.2.1

Autor pierwotnego projektu: **Paweł Pawełek / AIO Team**. Licencja: **GPL-3.0**.
Repozytorium: https://github.com/OliOli2013/PanelAIO-Plugin

## Organizacja wydań

Narzędzie `tools/build_hdsatelit_ci.py` bierze pakiet **standardowy IPK** z `release/`, sprawdza jego numer względem `version.txt` i `control/control`, rozpakowuje go do katalogu tymczasowego i na tej kopii nakłada profil `hds2`. Nie zmienia wejściowego IPK. Po zmianie kodu zbuduj aktualny IPK przed generowaniem wariantu hds2; skrypt odrzuca domyślny IPK z niezgodnym kodem lub skryptem instalacyjnym.

Tworzy następujące pliki:

- `dist-hdsatelit/enigma2-plugin-extensions-panelaio_<wersja>+hds2_all.ipk`
- `dist-hdsatelit/enigma2-plugin-extensions-panelaio_<wersja>+hds2_all.deb`
- `dist-hdsatelit/aio-panel-hdsatelit-source.zip`
- `dist-hdsatelit/SHA256SUMS.txt`

W CI i OpenEmbedded korzystaj z `tools/build_hdsatelit_ci.py`. `tools/build_hdsatelit.py` pozostaje starszą ścieżką budowania bezpośrednio z repozytorium.

## Wytyczne HD Satelit

W edycji HD Satelit nie ma działania instalatora zewnętrznego feedu Softcam HTTP, aktualizacji SoftCam.Key, FuryBiss, Jihad FHD i Adult XXX. Brak również samodzielnej aktualizacji AIO Panel z GitHub (także po wcześniejszym rozpoczęciu operacji). Aktualizacja pakietu powinna odbywać się przez OPKG i feed obrazu HD Satelit. Zachowano OSCam instalowany tylko z istniejących repozytoriów obrazu, SuperKonfigurator bez dodawania feedu, listy kanałów, skórki, picony, EPG, backup i diagnostykę.

To ograniczenia wydawanej wtyczki, nie mechanizm powstrzymujący użytkownika root przed instalacją innych programów.

## Budowanie lokalne (terminal GitKrakena)

```bash
cd "$HOME/PanelAIO-Plugin" # lub lokalna ścieżka repozytorium
python3 tools/build_hdsatelit_ci.py --source . --out dist-hdsatelit
python3 tools/test_hdsatelit.py --out dist-hdsatelit
python3 tools/test_hdsatelit_ci.py --out dist-hdsatelit
(cd dist-hdsatelit && sha256sum --check SHA256SUMS.txt)
```

Wymagania: Linux, Python 3.8+, `ar`, `dpkg-deb`, `sha256sum`, `/bin/sh`. Dane w `release/` muszą odpowiadać wersji z `version.txt`. Wariant hds2 nie nadpisuje standardowych IPK/DEB i nie modyfikuje katalogów tunera.

## Tylko źródła: OpenEmbedded / BitBake

```bash
python3 tools/build_hdsatelit_ci.py --source . --source-only --out dist-hdsatelit-source
(cd dist-hdsatelit-source && sha256sum --check SHA256SUMS.txt)
```

Ten tryb zapisuje wyłącznie `aio-panel-hdsatelit-source.zip` i `SHA256SUMS.txt`, nakłada i sprawdza ten sam profil co pełny build. Wymaga Python 3.8+, `ar`, `/bin/sh` i **gotowego wejściowego standardowego IPK**, ale nie uruchamia `dpkg-deb` ani nie buduje IPK/DEB. Do odtworzenia profilu z archiwalnego wejścia można jawnie wskazać `--standard-ipk /ścieżka/do/standardowego.ipk`; wersja wejścia musi nadal odpowiadać `version.txt`. Jeśli podasz starszy plik z tym samym numerem, poprawki z bieżącego checkoutu nie trafią do eksportu.

Jeżeli recepta sama pakuje drzewo, nie przejmuje automatycznie skryptów ani metadanych z `control/`. Nie pomijaj przy kopiowaniu `AIO_PACKAGE_SOURCES.txt`. Jeśli recepta zmienia zestaw skryptów, wygeneruj manifest ponownie na finalnym drzewie pakietu. Przejście ze starej nazwy wymaga w metadanych recepty odpowiedników `Provides`, `Replaces` i `Conflicts` (`RPROVIDES`, `RREPLACES`, `RCONFLICTS`) dla `enigma2-plugin-systemplugins-panelaio`.

## GitHub Actions

Workflow `.github/workflows/aio-hdsatelit.yml` można uruchomić ręcznie (`Actions` → `AIO Panel HD Satelit hds2 - pakiety feed` → `Run workflow`). Przy nowych stabilnych tagach `X.Y.Z` lub `vX.Y.Z` startuje automatycznie. Sprawdza tag i źródła, buduje pakiety, uruchamia dwa niezależne zestawy testów oraz udostępnia paczkę artefaktów w danym przebiegu Actions.

**Nie publikuje automatycznie nowej wersji na feed HD Satelit** ani nie wysyła do publicznego GitHub Releases. Najpierw pobierz i zweryfikuj artefakty, a następnie opublikuj w odpowiednim wydaniu GitHub lub przekaż opiekunom HD Satelit. Do BitBake/OpenEmbedded przekazuj **`aio-panel-hdsatelit-source.zip`**, nie niezmodyfikowany kod standardowej edycji.

Tag źródłowy `hds2-18.2.1` jest przeznaczony dla oryginalnego commita feedu `16f348418de708cfca03b19b6f5f575ebe2f06f5`. Nie przypinaj do niego kolejnych poprawek. Prefiks `hds2-` nie pasuje też do wyzwalaczy stabilnych wydań z tego historycznego commita.

## Zgodność wersji

Generator ma rygorystyczne punkty weryfikacji. Jeżeli przy kolejnej wersji zmienią się ścieżki instalacji lub aktualizatora, budowanie **zostanie przerwane**, zamiast wydać pakiet naruszający politykę HD Satelit. Jest to celowe. Zmian nie wolno omijać przez usunięcie zabezpieczeń.

## Uwaga dla obrazów HD Satelit

Pakiet zachowuje zależność `Depends: enigma2` z wydania standardowego. W starszym obrazie HD Satelit 0.7.2 zgłaszano brak dostarczenia tego pakietu; zespół HD Satelit zapowiadał `RPROVIDES: enigma2` w wersji 0.7.3. Właściwą zgodność zależności należy sprawdzić w aktualnej wersji obrazu. Nie instaluj z `--force-depends`.

Przed dystrybucją wymagana jest próba na rzeczywistym odbiorniku HD Satelit (instalacja, uruchomienie, nawigacja, OSCam/feed, picony, skin gallery, aktualizacja OPKG i restart GUI). Statyczne testy nie zastępują testu sprzętowego.

Nowe pakiety używają listy należących do pakietu plików `.py` i `.sh` przy kontroli składni. Obce pliki pozostawione po ręcznej instalacji nie wpływają na jej wynik. Jeśli po rozpakowaniu nadal istnieje ręczna kopia `Extensions/PanelAIO`, skrypt po walidacji przenosi ją do unikalnego katalogu `/var/backups/panelaio-legacy.*`. Wykonaj dodatkowy backup **przed** migracją starego pakietu: menedżer pakietów może sam usunąć jego pliki przed `postinst`.

Próg `preinst` pozostaje na poziomie 14 MiB. Przed decyzją o obniżeniu zmierz wolne miejsce na partycji wtyczek przed i w trakcie aktualizacji oraz uwzględnij miejsce na kopię. To, że IPK jest mniejszy od progu, nie oznacza, że tyle samo wystarczy do aktualizacji.
