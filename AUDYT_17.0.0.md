# AIO Panel 17.0.0 — audyt i zakres weryfikacji

Data: 4 października 2026. Poprawiona paczka po zgłoszeniu błędów skórek i list. Autor wtyczki: Paweł Pawełek.
Repozytorium: https://github.com/OliOli2013/PanelAIO-Plugin
Baza kodu: commit `5268dfbdbac0c93b842639717b37368c38e55495`.

## Wynik

Przygotowano wersję 17.0.0, pakiet IPK, dodatkowy pakiet DEB i kompletną zawartość repozytorium. Usunięto opisane poniżej wykryte błędy. To audyt kodu, pakietów i scenariuszy błędów w środowisku Linux, a nie certyfikacja działania każdego przycisku na wszystkich tunerach. Nie ma podstaw do deklaracji, że usunięto wszystkie możliwe błędy.

Odnaleziono wcześniejszy plik `enigma2-plugin-extensions-panelaio_16.0.3_all(2).ipk` (399722 B) oraz `panelaio(1).log`. Do analizy bajtów użyto pakietu 16.0.3 z repozytorium, również 399722 B. Nie porównywano bajtów pliku z wcześniejszej rozmowy, więc zgodność rozmiaru nie jest dowodem identyczności.

Pakiet bazowy z repozytorium ma SHA-256 `726131e2335a7bd36e71c6c226b9a92e480f40aa7c6f8ad2f4c18e2ae86ce400`. Kod HEAD i zawartość tego IPK różniły się w czterech plikach: `installer.sh`, `data/requested_installers.py`, `safe_ipk_install.sh`, `changelog.txt`. Dlatego nową paczkę zbudowano z jednej spójnej wersji źródeł.

## Wykryte problemy i zmiany

| Obszar | Wykryty problem | Zmiana w 17.0.0 |
|---|---|---|
| Zmiana hasła | Log z tunera: `chpasswd` zakończył się kodem 139. | Gdy chpasswd zawiedzie, próba przez passwd z terminalem PTY. Hasło nie trafia do argumentów procesu ani logów; prywatny plik jest usuwany także przy błędzie. Odrzucane są znaki mogące utworzyć dodatkowy rekord. Przyczyny awarii binarnego chpasswd nie ustalono. |
| Sancho/S4a | Log potwierdza HTTP 200 z ZIP-em o rozmiarze 0 B. | Pełne pobranie i kontrola archiwum przed wyświetleniem: puste odpowiedzi i uszkodzone paczki są ukrywane. Panel nie może odtworzyć danych, których serwer nie udostępnia. Nie podmieniono list Sancho/Conrado na listy innych autorów. |
| E2iPlayer | Potok wget do sh może zwrócić 0 mimo błędu wget. Skrypt źródłowy korzysta także z interaktywnego terminala i pytania o restart. | Instalacja przez feed obrazu i kontrola statusu pakietu. Feed dobiera ABI/zależności; jego wersja może być starsza niż GitHub. Gdy pakietu brak, panel podaje błąd zamiast zgłaszać instalację. |
| Aktualizacja panelu | Bootstrap zależny od wget/curl; zawsze staging w /tmp; obsługa tylko opkg. | Dodano pobieranie helpera przez Python, próbę IPv4, wybór stagingu /tmp lub zamontowanego HDD/USB, sprawdzanie wolnego flash i DEB/dpkg. Zachowano weryfikację SHA-256, nazwy, wersji, payloadu i statusu instalacji. |
| Walidacja aktualizacji | Walidator payloadu ograniczał kontrolę do wersji 16.0.2/16.0.3. | Kontrola zawartości AIO działa także dla 17.0.0; wymagane są nowe moduły. |
| Wynik instalacji IPK | Sprawdzano tylko obecność nazwy pakietu — stara wersja mogła już istnieć. | Kontrola oczekiwanej wersji oraz statusu `install ok installed`. |
| Instalatory skórek | Osobna ścieżka wykonywała polecenia bez wspólnej walidacji; domyślny wzorzec nazwy nie uwzględniał `skins`. | Ścieżka IPK przez walidator, dopuszczona właściwa kategoria pakietów. Jihad pobierany jako pakiet zamiast skryptu z wymuszaniem zależności. |
| xDreamy | Skrypt usuwał bieżący skin przed pobraniem nowego. | Instalacja jego IPK przez kontrolowane pobieranie, bez wstępnego usuwania aktywnego skinu. |
| Fury FHD | Link wskazywał wtyczkę FuryBiss, nie skórkę. | Poprawna nazwa i przeniesienie do wtyczek. Lokalny instalator dobiera pakiet FuryBiss do CPU i wersji Pythona, bez usuwania starej wersji i wymuszania restartu. |
| Restart z zewnętrznych skryptów | JediMakerXtream, ChocholousekPicons, CIEFP i FootOnSat zawierały zatrzymanie/restart Enigmy, blokowany przez walidator. | Te instalacje kierowane są do feedu obrazu. PiconUpdater ma neutralizowaną jedną konkretną, sprawdzoną instrukcję killall. IPTV Dream otrzymuje `--no-restart`; MyUpdater nie dostaje opcjonalnego `--restart`. |
| Powłoka | Skrypt z shebangiem bash mógł być uruchomiony jako sh. | Runner rozpoznaje bash, sprawdza dostępność i składnię wybranej powłoki. |
| Pobieranie w core/network | Puste/ucięte dane mogły zostać przyjęte; równoległe get_text używały jednej nazwy pliku; pliki częściowe pozostawały po błędzie. | Kontrola liczby bajtów, unikalne pliki, sprzątanie, zachowanie poprzedniego pliku przy błędzie. Kontrola długości także w Pythonowym downloaderze shellowym. |
| Timeout procesu | TimeoutExpired w Pythonie 3 nie kończył procesu. | Proces jest zabijany i odbierany przed zwróceniem błędu. |
| Listy kanałów | Błąd cp wybranych plików był ignorowany. Sygnał przerwania mógł usunąć backup bez rollbacku. | Propagowanie błędów kopii, rollback przy sygnale/wyjściu i zachowanie kopii, jeżeli przywrócenie zawiedzie. |
| Python 2 | Dodatkowe etykiety są Unicode; na starym MenuList mogą nie wyświetlać się prawidłowo. | Przed przekazaniem zakładek konwersja do typu odpowiedniego dla danej wersji Pythona. Shell preferuje interpreter uruchamiający Enigmę, jeśli panel go przekazał. |
| Timer | Połączenie timeout.connect nie miało zachowanej referencji. | Referencja jest zachowana. |
| Testy i CI | Testy aktualizacji używały pakietu 16.0.2, CI sprawdzało artefakt 16.0.0. | Testy pakietu 17.0.0, poprawiona emulacja opkg/status i aktualny artefakt w CI. |

## Katalog dodatków

24 definicje instalacji z feedu obrazu: 20 nowych oraz 4 zastępujące wcześniejsze zewnętrzne instalatory. Pięć definicji skórek jest filtrowanych według rzeczywistych indeksów tunera; pozostałe znalezione pakiety skórek są dodawane dynamicznie. Są to użyteczne narzędzia do typowych zadań, nie ranking popularności — brak wiarygodnych statystyk liczby instalacji.

- Nagrywanie i multimedia: AutoTimer, Enhanced Movie Center, MovieCut, MovieRetitle.
- Pliki i obsługa: DreamExplorer, File Commander, OpenWebif, Transcoding Setup, PermanentClock, VirtualZap, Weather Plugin.
- EPG i napisy: EPGRefresh, EPGSearch, Jedi EPG Xtream, SubsSupport.
- Skórki: Metrix ATV/SPA, PLi HD, PLi HD FullNight, Umbra, Full HD Glass17 wyłącznie jeśli ich rzeczywiste pakiety są dostępne. Dodatkowo pozostałe skórki znalezione w feedzie danego obrazu.
- Zmieniona metoda dotychczasowej instalacji: JediMakerXtream, ChocholousekPicons, CIEFP OSCam Editor, FootOnSat.

Dostępność pakietów sprawdzana jest na tunerze po odświeżeniu jego feedów. Nie dodano feedu innego obrazu ani pakietu z obcego modelu. Jeżeli dodatku brak, instalacja kończy się komunikatem „Unavailable in this image feed”. Transcoding Setup nie zapewni transkodowania na tunerze bez odpowiedniego sprzętu. Skórki nie są aktywowane automatycznie.

FTP to sposób przesłania pliku, a nie interpreter poleceń. Polecenia instalacyjne wykonuje się przez SSH/Telnet/PuTTY po przesłaniu pliku do /tmp.

## Źródła sprawdzone w internecie

Podczas audytu 24 istniejące adresy instalatorów zwróciły HTTP 200 i niepuste dane. Rejestr: `SOURCE_AUDIT.json`. To potwierdza dostępność samego skryptu w chwili sprawdzenia; nie potwierdza działania wszystkich jego dalszych pobrań ani instalacji na tunerze.

Główne źródła doboru dodatków:

- OpenPLi/enigma2-plugins: https://github.com/OpenPLi/enigma2-plugins
- AutoTimer: https://github.com/oe-alliance-plugins/AutoTimer
- XStreamity: https://github.com/kiddac/XStreamity
- Bouquet Maker Xtream: https://github.com/kiddac/Bouquet_Maker_Xtream
- E2iPlayer i zalecenie użycia feedu: https://github.com/oe-mirrors/e2iplayer/blob/python3/README.md
- MetrixHD: https://github.com/openatv/MetrixHD
- Rzeczywiste definicje pakietów skórek: https://github.com/oe-alliance/oe-alliance-core/tree/6.0/meta-oe/recipes-distros/openatv/plugins

## Testy

- Python 3: kompilacja modułów, walidacja pakietu i autotest payloadu.
- Python 2: kompilacja na zbudowanym interpreterze CPython 2.7.18 oraz autotest źródeł i stagingu pakietu. Nie jest to test działania GUI ani sieci na starym obrazie.
- Skrypty: sprawdzenie składni przez `/bin/sh -n`.
- 48 testów unittest: 46 wykonanych z powodzeniem, 2 pominięte historyczne porównania do niedostarczonej bazy 16.0.0.
- Symulacje aktualizatora: poprawna instalacja, zapasowy adres Release, brak artefaktu, zła suma, błąd opkg, pozorny sukces bez zmiany wersji, błędna baza pakietów i błędna wersja plików.
- Zgodność nowego installer.sh z walidatorem znajdującym się w IPK 16.0.3.
- Awaria chpasswd 139, fallback passwd z PTY, timeout oraz odrzucenie wielowierszowego hasła.
- Puste i ucięte pobranie: stary plik pozostaje, pliki częściowe usunięte.
- Brak dodatku w feedzie: brak próby instalacji, zwolniona blokada.
- Błąd kopiowania nowego lamedb: poprzednia lista kanałów odzyskana bajt w bajt.
- Struktura DEB sprawdzona przez dpkg-deb; nie wykonywano instalacji DEB na urządzeniu DreamOS.

## Pozostałe ograniczenia i testy na sprzęcie

Nie testowano fizycznych tunerów, pilota, ekranu, restartów GUI, Wi-Fi ani konfiguracji sprzętowej. Nie można zagwarantować zgodności ze wszystkimi odmianami Enigma2. IPK jest dla obrazów z opkg; dodatkowy DEB dla obrazów korzystających z dpkg. DEB rozszerza instalację panelu i aktualizację, lecz nie oznacza, że wszystkie wcześniejsze funkcje zależne od opkg/feedów są zgodne z DreamOS.

Zachowano dotychczasowe filtry Python 2 oraz VTi/Hyperion dla funkcji, których autor wcześniej nie wspierał. Nie są to funkcje naprawione i przetestowane w tych obrazach. Nadal istnieją historyczne instalatory z własną logiką pobierania, zależnościami i sposobem raportowania błędów; poprawność pobrania ich skryptu nie jest pełną weryfikacją późniejszej instalacji. Starsze obrazy muszą mieć działający TLS, aktualne certyfikaty i poprawną datę. Nie wyłączono globalnie kontroli certyfikatów.

Skrypt aktualizacji wybiera staging na zamontowanym HDD/USB, ale nie powiększa flash. Przy faktycznym braku miejsca lub uszkodzonym menedżerze pakietów zgłasza przyczynę zamiast wymuszać instalację. Błąd aktualizacji na konkretnym modelu wymaga jego logu — bez niego nie można stwierdzić, że ten przypadek został rozwiązany.

Przed oznaczeniem wydania jako sprawdzonego na tunerach należy wykonać: aktualizację 16.0.3 → 17.0.0 z panelu na jednym obrazie Py2 i jednym Py3, restart i otwarcie wszystkich zakładek, instalację dodatku i skinu z dostępnego feedu, backup/restore list oraz próbę na modelu ze zgłaszanym błędem aktualizacji. Dla DreamOS potrzebny jest osobny test DEB i obsługiwanych funkcji.

## Poprawki po zgłoszeniu z 4 października 2026

Zdjęcia z OpenATV 8.0.1 / h7 pokazały błędne nazwy w dodanym katalogu: metrixhd, pli-fullhd/pli-fhd, simple-ten-eighty oraz hdglass17/16 nie występowały w feedzie. To błąd doboru pakietów w poprzedniej paczce. Nowe definicje używają m.in. enigma2-plugin-skins-metrix-atv, enigma2-plugin-skins-pli-hd-fullnight-4atv oraz enigma2-plugin-skins-umbra. Dostępność jest odczytywana przez opkg list i list-installed lub apt-cache dumpavail w wątku ładowania. Niedostępne definicje nie pojawiają się w menu. Pozostałe rzeczywiste pakiety skórek z feedu są dodawane automatycznie. Instalator ponownie odświeża feed i sprawdza nazwę, a po instalacji stan pakietu. Historyczne zewnętrzne instalatory są oddzielną ścieżką i nie mają takiej gwarancji doboru do obrazu.

AIO / Aktualizacje jest ostatnią kategorią w obu językach.

Każde otwarcie panelu sprawdza archiwa list, które spełniają wcześniejsze filtry wieku/autorów. Maksymalnie cztery pobrania równolegle, 12 s timeout operacji i 60 s budżetu kontroli. Pobranie musi być niepuste, kompletne względem Content-Length (jeśli podane), mniejsze od 16 MiB. ZIP/TAR: limit 12000 wpisów, 64 MiB rozwiniętych danych, kontrola ścieżek, typów, pełny odczyt wszystkich plików i CRC ZIP; wymagane dane lamedb/lamedb5 lub bukiety z #SERVICE. Nic nie jest rozpakowywane do konfiguracji tunera. Pliki tymczasowe są usuwane. Błąd/timeout ukrywa pozycję, nie zmienia kanałów. Jest to kontrola archiwum i rozpoznawalności danych, nie test odbioru wszystkich usług satelitarnych.

Adres sprawdzany jest raz w danym otwarciu; nie ma trwałego pozytywnego cache zależnego od daty. Zmiana daty Conrado/Sancho nie omija kontroli. Poprawna paczka powróci przy kolejnym otwarciu. Deduplikacja list następuje po weryfikacji, więc uszkodzony wpis z repozytorium nie zasłania poprawnego odpowiednika S4a. Starsze linki GitHub /raw/ są pobierane bezpośrednio z raw.githubusercontent.com, co eliminuje dodatkowy redirect.

Próba sieciowa 2026-10-04: sześć rzeczywistych archiwów repozytorium przeszło kontrolę. Conrado 00conrado-13.zip oraz Sancho 00lista-13.zip odrzucono za pustą odpowiedź HTTP; w wyniku widoczne były tylko 6/8 poprawnych pozycji. Dowód szczegółowy: LIVE_LIST_CHECK.json.

Nowe testy obejmują pusty plik, HTML, obce archiwum, poprawne ZIP i TAR, błędne CRC, traversal, przerwane pobranie, termin kontroli, deduplikację adresu, ponowną kontrolę bez cache oraz wybór rzeczywistych pakietów skórek. Dodatkowo wykonano na CPython 2.7.18 rzeczywistą kontrolę ZIP i filtrowanie wyników; kompilacja całego pakietu i self-test zakończyły się powodzeniem na Python 2 i 3. Nie wykonano instalacji na fizycznym h7 — pozytywny test instalatora skórek używa kontrolowanego emulatora poleceń opkg.

Numer nadal 17.0.0. Do ponownej instalacji tej wersji należy użyć opkg --force-reinstall i uruchomić GUI ponownie. SHA256SUMS.txt opisuje nową paczkę; cały komplet plików trzeba podmienić jednym commitem.
