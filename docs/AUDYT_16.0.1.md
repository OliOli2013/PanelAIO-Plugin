# AIO Panel 16.0.0 — audyt i poprawka 16.0.1

Data: 8 września 2026. Autor projektu: Paweł Pawełek.

## Materiał i zakres

Podstawą jest zapisana paczka `enigma2-plugin-extensions-panelaio_16.0.0_all(4).ipk` oraz repozytorium `OliOli2013/PanelAIO-Plugin` z commitu `191bc4d5709bab19a2487a96bc7b2ba2ad4d8372`. Plik runtime.py w paczce i w repozytorium jest identyczny. Poprawka pozostaje w linii 16.x.

Przegląd objął wejście plugin.py, runtime.py, nawigację i interfejs, moduły core/data/ui, uruchamianie zadań, pobieranie i walidację, instalator AIO, skrypty pomocnicze, kontrolę paczek, preinst/postinst/postrm i budowanie IPK. Zweryfikowano składnię 37 modułów produkcyjnych Python i 23 plików shell oraz pliki JSON. Przejrzano przepływy instalacji, kopii, przywracania i funkcji systemowych; zachowano istniejące polecenia instalatorów innych wtyczek.

To audyt kodu i testy w środowisku roboczym. Nie był dostępny rzeczywisty tuner ani log użytkownika z nieudaną aktualizacją. Poniższe błędy są odtworzone albo wynikają bezpośrednio z kodu, ale nie stanowią dowodu, że każdy zgłaszający użytkownik ma tę samą przyczynę.

## Ustalenia i poprawki

| Problem | Skutek | Poprawka |
|---|---|---|
| Walidator 16.0.0 odrzuca własny installer.sh przez fragment komentarza przypominający potok wget do sh | Aktualizator może zakończyć się przed uruchomieniem instalacji | Nowy installer.sh przechodzi NIEZMIENIONY walidator starej paczki; nie osłabiano globalnej walidacji pozostałych instalatorów |
| version.txt zawiera 16.0.0, control 16.0.0-r1, a nazwa paczki znów 16.0.0 | Hotfix w tej samej wersji nie jest rozpoznawany jako nowszy | Jednolita wersja 16.0.1 w plikach, IPK i metadanych |
| Ręczne sprawdzenie aktualizacji wykonuje sieć w wątku GUI | Zawieszony interfejs podczas błędu sieci lub wolnej odpowiedzi | Osobny wątek, jedna aktywna kontrola, obsługa zamknięcia okna, aktualizacja GUI w głównym wątku |
| Nazwy pobranych plików powstają z pierwszych 80 znaków URL | Długie adresy o wspólnym prefiksie mogą nadpisywać sobie wersję/changelog/manifest | Unikatowe pliki przez mkstemp i sprzątanie po odczycie |
| aio_secure_download nadpisuje globalne zmienne powłoki wywołującej | Możliwa zmiana URL/OUT/PY w nadrzędnym skrypcie | Izolacja funkcji pobierania w podpowłoce |
| Python pobierający plik może zostawić część danych; helper sprawdzał tylko niezerowy rozmiar | Częściowy plik mógł zostać uznany za pobrany | Wymagany prawidłowy kod zakończenia Pythona przed aktywacją pliku |
| Nieudana próba zdobycia blokady ustawia jej ścieżkę, a cleanup usuwał ją bez sprawdzenia właściciela | Druga próba mogła odblokować wciąż działającą pierwszą instalację | Usuwanie tylko blokady z własnym PID; osobna blokada aktualizacji AIO i operacji opkg |
| Dotychczasowa ścieżka ratunkowa kopiowała źródła po błędzie IPK | Pliki mogły mieć inną wersję niż baza opkg | Aktualizacja paczką; brak kopiowania źródeł po nieudanym opkg; kontrola bazy pakietów, version.txt i self-testu |
| Brak pełnego potwierdzenia spójności publikacji IPK | Nieaktualna/niedokończona publikacja może wprowadzać błąd | SHA-256, nazwa, wersja, architektura i kontrola struktury paczki AIO; mirror w repozytorium i zapasowy GitHub Release |
| Archiwa control/data korzystają z xz | Walidator oparty na tarfile może nie odczytać ich na Pythonie 2 lub bez lzma | IPK z control.tar.gz i data.tar.gz |
| Połączenie timera timeout.connect nie było przechowywane | Na części obrazów automatyczna konserwacja mogła nie działać | Zachowanie obiektu połączenia; konserwacja pomija katalogi blokad/logów i robocze operacje |
| Szybki start „Sprawdź aktualizacje” otwierał ekran informacji | Akcja nie odpowiadała podpisowi | Wywołuje sprawdzanie aktualizacji |

Nowy updater pobiera aktualne pliki pomocnicze zamiast używać starej kopii z tunera. Nie wymusza restartu GUI ani downgrade'u. Błąd opkg zatrzymuje instalację i jest raportowany; aktualizator nie gwarantuje transakcyjnego rollbacku bazy pakietów po przerwaniu pracy opkg lub utracie zasilania.

## Instalatory i menu

Dotychczasowe skrypty shell innych wtyczek porównano bajtowo z paczką 16.0.0. Pozostały niezmienione. Wszystkie istniejące dedykowane metody instalacji w runtime.py porównano przez AST; są identyczne. Dotychczasowe wpisy menu zachowano, z wyjątkiem celowo zmienionego Fury. Zachowano także filtrowanie właściwe dla obrazu i Pythona przed zbudowaniem zakładek.

W szczególności nie zmieniono poleceń E2iPlayer, IPTV Dream, S4aUpdater, PiconUpdater, MyUpdater ani CIEFP Oscam Editor. Wspólny helper pobierania/blokad został poprawiony, co wpływa na niezawodność tych operacji bez zmiany ich poleceń.

Dodano dokładne polecenia użytkownika w data/requested_installers.py:

- Fury FHD: adres `islam-2412/FuryBiss/refs/heads/main/fury/installer.sh`, zamiast wcześniejszego `islam-2412/IPKS/...`.
- Jihad FHD: `ahmeds200917/A.Shawky/refs/heads/main/install_jihad.sh`.
- Adult XXX: `Belfagor2005/xxxplugin/main/installer.sh`.

Stan sprawdzony przez odczyt HTTP w dniu audytu: Fury **404**, Jihad **200**, Adult XXX **200**. Skryptów nie wykonywano. Jihad używa wymuszeń opkg i bezwarunkowego exit 0, więc nie należy utożsamiać zakończenia jego polecenia z poprawną instalacją. Potok wget do sh może także zwrócić kod sh po nieudanym pobraniu; zachowano go zgodnie z dokładnym żądaniem użytkownika. Nowe komunikaty nie deklarują potwierdzonej instalacji zewnętrznego dodatku na podstawie samego kodu 0.

Źródła: [repozytorium AIO](https://github.com/OliOli2013/PanelAIO-Plugin), [Fury](https://raw.githubusercontent.com/islam-2412/FuryBiss/refs/heads/main/fury/installer.sh), [Jihad FHD](https://raw.githubusercontent.com/ahmeds200917/A.Shawky/refs/heads/main/install_jihad.sh), [Adult XXX](https://raw.githubusercontent.com/Belfagor2005/xxxplugin/main/installer.sh).

Zakładki PL/EN: AIO/Aktualizacje, Listy kanałów, IPTV/Odtwarzacze, EPG/Picony, Skórki, Softcam/OSCam, Wtyczki/Feedy, Kopie/Przywracanie, System/Konserwacja, Diagnostyka/Naprawa, Kontakt/Społeczność, Dla dorosłych 18+. Test porównuje liczbę i tożsamość wszystkich akcji przed i po grupowaniu w obu językach.

## Testy i ograniczenia

17 testów automatycznych: zgodność starego walidatora z nowym aktualizatorem, zachowanie instalatorów i menu, kompletność zakładek PL/EN, format i zawartość IPK, własność blokady, izolacja zmiennych pobierania, odrzucenie częściowego pobrania, równoległe pliki tymczasowe, obsługa GUI w tle/duplikatów/zamkniętego okna oraz 8 scenariuszy instalacji: sukces, zapasowy Release, brak paczki, błędny hash, błąd opkg, opkg bez rzeczywistej zmiany, zła wersja w bazie i zła wersja plików.

Dodatkowo: kompilacja kodu Python 3, składnia shell/JSON, istniejący test regresyjny, self-test wtyczki, wykonanie postinst na odizolowanej kopii plików. Sieć i opkg w testach aktualizacji są atrapami; zewnętrzni wydawcy i system gospodarza nie są modyfikowani. Dwa testy porównawcze wymagają rozpakowanej paczki bazowej w lokalizacji wskazanej w pliku testów; bez niej są pomijane.

Nie wykonano testów działania GUI na fizycznym Enigma2, rzeczywistego opkg na tunerze, dekodowania kanałów, sprzętowego OSCam ani faktycznej instalacji wszystkich zewnętrznych wtyczek. Nie był dostępny interpreter Python 2; zachowano zgodną składnię zmian, ale zgodność działania na wszystkich starych obrazach wymaga prób sprzętowych. Nie obiecuje się działania na 100% tunerów.

Błędy certyfikatów/data systemu, brak miejsca, ograniczenia sieci, uszkodzone opkg oraz niezgodności zewnętrznych dodatków nadal mogą uniemożliwić instalację. Aktualizator AIO zachowuje sprawdzanie certyfikatów HTTPS. Hash z tego samego repozytorium potwierdza spójność publikacji, nie jest niezależnym podpisem wydawcy.

Nie publikowano zmian na GitHubie. Instrukcja podmiany i instalacji znajduje się w INSTALACJA_16.0.1.txt. Aby 16.0.0 zobaczyła nową wersję online, trzeba opublikować całą poprawkę razem z IPK, sumą SHA-256 i version.txt.
