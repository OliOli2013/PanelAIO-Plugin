# AIO Panel – HD Satelit (hds2), od wersji 18.2.1

Autor pierwotnego projektu: **Paweł Pawełek / AIO Team**. Licencja: **GPL-3.0**.
Repozytorium: https://github.com/OliOli2013/PanelAIO-Plugin

## Organizacja wydań

Standardowe AIO Panel pozostaje bez zmian. Narzędzie `tools/build_hdsatelit_ci.py` bierze pakiet **standardowy IPK** z `release/`, sprawdza jego numer względem `version.txt` i `control/control`, rozpakowuje go do katalogu tymczasowego i na tej kopii nakłada profil `hds2`.

Tworzy następujące pliki:

- `dist-hdsatelit/enigma2-plugin-extensions-panelaio_<wersja>+hds2_all.ipk`
- `dist-hdsatelit/enigma2-plugin-extensions-panelaio_<wersja>+hds2_all.deb`
- `dist-hdsatelit/aio-panel-hdsatelit-source.zip`
- `dist-hdsatelit/SHA256SUMS.txt`

Oryginalny `tools/build_hdsatelit.py` i `tools/test_hdsatelit.py` pozostają w repozytorium bez zmian. Nowy generator jest dodatkową ścieżką budowania dla CI. Nie wprowadza modyfikacji do standardowej wtyczki.

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

## GitHub Actions

Workflow `.github/workflows/aio-hdsatelit.yml` można uruchomić ręcznie (`Actions` → `AIO Panel HD Satelit hds2 - pakiety feed` → `Run workflow`). Przy nowych stabilnych tagach `X.Y.Z` lub `vX.Y.Z` startuje automatycznie. Sprawdza tag i źródła, buduje pakiety, uruchamia dwa niezależne zestawy testów oraz udostępnia paczkę artefaktów w danym przebiegu Actions.

**Nie publikuje automatycznie nowej wersji na feed HD Satelit** ani nie wysyła do publicznego GitHub Releases. Najpierw pobierz i zweryfikuj artefakty, a następnie opublikuj w odpowiednim wydaniu GitHub lub przekaż opiekunom HD Satelit. Do BitBake/OpenEmbedded przekazuj **`aio-panel-hdsatelit-source.zip`**, nie niezmodyfikowany kod standardowej edycji.

## Zgodność wersji

Generator ma rygorystyczne punkty weryfikacji. Jeżeli przy kolejnej wersji zmienią się ścieżki instalacji lub aktualizatora, budowanie **zostanie przerwane**, zamiast wydać pakiet naruszający politykę HD Satelit. Jest to celowe. Zmian nie wolno omijać przez usunięcie zabezpieczeń.

## Uwaga dla obrazów HD Satelit

Pakiet zachowuje zależność `Depends: enigma2` z wydania standardowego. W starszym obrazie HD Satelit 0.7.2 zgłaszano brak dostarczenia tego pakietu; zespół HD Satelit zapowiadał `RPROVIDES: enigma2` w wersji 0.7.3. Właściwą zgodność zależności należy sprawdzić w aktualnej wersji obrazu. Nie instaluj z `--force-depends`.

Przed dystrybucją wymagana jest próba na rzeczywistym odbiorniku HD Satelit (instalacja, uruchomienie, nawigacja, OSCam/feed, picony, skin gallery, aktualizacja OPKG i restart GUI). Statyczne testy nie zastępują testu sprzętowego.
