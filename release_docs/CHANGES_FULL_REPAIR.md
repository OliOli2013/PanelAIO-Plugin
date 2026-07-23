# AIO Panel 14.0.0 — pełna naprawa bezpieczeństwa i niezawodności

Data wydania: 23 lipca 2026 r.

Numer wersji pozostaje **14.0.0**, zgodnie z założeniem. Pakiet jest przeznaczony do wymuszonej reinstalacji istniejącej wersji.

## Najważniejsze zmiany

### Instalacja list kanałów i restore

- instalacja odbywa się w osobnym katalogu staging;
- archiwa ZIP/TAR są sprawdzane przed rozpakowaniem;
- blokowane są ścieżki absolutne, `..`, symlinki, hardlinki i urządzenia specjalne;
- przed zmianą tworzona jest kompletna, zweryfikowana kopia aktualnych list;
- sprawdzane są wolne miejsce i inody;
- operacja ma blokadę uniemożliwiającą równoległą instalację lub restore;
- po instalacji sprawdzane są `lamedb/lamedb5`, indeksy bukietów i rzeczywista zawartość;
- każdy błąd uruchamia automatyczny rollback;
- restore działa w odłączonym procesie, dlatego zatrzymanie GUI nie zabija procedury;
- Enigma2 jest ponownie uruchamiana także po błędzie przywracania;
- backup obejmuje ten sam zestaw plików, który instalator może zmienić.

### Picony

- osobna akcja i osobny instalator piconów;
- pobieranie wyłącznie przez HTTPS;
- walidacja ZIP oraz odrzucanie HTML zamiast archiwum;
- kontrola miejsca i liczby inodów w katalogu roboczym i docelowym;
- rekurencyjne wyszukiwanie PNG;
- wykrywanie dwóch różnych plików o tej samej nazwie przed rozpoczęciem kopiowania;
- atomowe kopiowanie, weryfikacja liczby plików i status końcowy;
- blokada równoległych instalacji;
- Super Konfigurator FULL pozwala wybrać pamięć wewnętrzną, USB, HDD, MMC albo własną ścieżkę.

### Super Konfigurator START/FULL

- instaluje dokładnie listę **Polska 13E AIO Panel**;
- instaluje bezpiecznie obsługę Softcam;
- preferuje pakiety OSCam-Emu przed zwykłym OSCam;
- ustawia OSCam przez konfigurację Enigma2 zamiast modyfikowania pliku ustawień w czasie pracy GUI;
- uruchamia tylko jeden wykryty manager Softcam;
- sprawdza, czy proces rzeczywiście wystartował;
- zatrzymuje kolejkę po błędzie krytycznym;
- oferuje ponowienie lub anulowanie;
- nie zgłasza sukcesu po błędnym kodzie wyjścia;
- nie obiecuje automatycznego restartu i nie wykonuje go samoczynnie.

### Bezpieczeństwo sieciowe i aktualizacje

- usunięto `--no-check-certificate`, `curl -k` i niezabezpieczony kontekst SSL;
- zdalne skrypty nie są uruchamiane przez `wget/curl | sh`;
- skrypt jest najpierw pobierany, sprawdzany i dopiero potem uruchamiany;
- menu nie zawiera już surowych komend pobierania do powłoki;
- zdalny manifest nie może dostarczyć dowolnego `install_cmd`;
- IPK jest sprawdzany po nagłówku, nazwie pakietu, architekturze i opcjonalnej sumie SHA-256;
- aktualizacja AIO używa stagingu, walidacji składni i rollbacku;
- historyczne odwołania Softcam do `http://updates.mynonpublic.com/oea` są przed wykonaniem przepisywane wyłącznie na odpowiadający adres HTTPS; każdy inny adres HTTP blokuje instalację;
- źródło bootstrapu jest przypinane sumą SHA-256, a nieoczekiwana zmiana wymaga świadomej akceptacji użytkownika;
- `satellites.xml` i dane OSCam są pobierane do pliku tymczasowego, walidowane i podmieniane atomowo.

### Backup/restore OSCam

- wykrywanie wielu typowych lokalizacji konfiguracji;
- preferowanie ścieżki `-c` aktywnego procesu;
- bezpieczne archiwum z manifestem;
- allowlista katalogów przy restore;
- kopia bieżącej konfiguracji i rollback;
- jednolite sterowanie `oscam`, `oscam-emu` i `oscam_emu`;
- łagodny stop przed wymuszonym zakończeniem;
- sprawdzenie startu po zmianie konfiguracji.

### M3U i bukiety

- unikalny katalog roboczy dla każdej operacji;
- walidowane identyfikatory bukietów;
- poprawne kodowanie URL w service reference;
- oczyszczanie nazw kanałów;
- atomowy zapis i kopia indeksu bukietów;
- jawny komunikat błędu zamiast cichego `except: pass` w krytycznej ścieżce;
- nowy format danych akcji oparty na kodowanym JSON, niewrażliwy na porty i dwukropki w URL;
- zachowana zgodność odczytu starych wpisów menu.

### GUI i stabilność

- timery ekranów są zatrzymywane w `onClose`;
- callbacki sprawdzają, czy ekran nadal istnieje;
- ekrany monitorowania, logów, usług, aktualizacji i diagnostyki mają wariant SD;
- język PL/EN jest zapisywany;
- Auto RAM nie wykonuje `drop_caches`; używa garbage collectora i usuwa wyłącznie własne stare pliki tymczasowe;
- automatyczna konserwacja jest rejestrowana przy starcie sesji;
- ukryta instalacja zależności przy samym otwarciu panelu została zastąpiona pytaniem i kontrolą wyniku;
- Service Manager steruje jedną rzeczywiście wykrytą usługą;
- hasło root jest maskowane i przekazywane przez plik tymczasowy z prawami 600.

### Czyszczenie i operacje systemowe

- czyszczenie `/tmp` ograniczono do plików AIO;
- Smart Cleanup nie usuwa cudzych logów ani list OPKG;
- narzędzie wykrywania uszkodzonych wtyczek tylko raportuje — nie kasuje katalogów;
- operacje OPKG, list, piconów i OSCam mają niezależne blokady;
- nazwy pakietów i ścieżki są walidowane przed użyciem w poleceniu.

### Instalacja i deinstalacja IPK

- `preinst` nie usuwa działającej wersji;
- sprawdzane jest minimalne wolne miejsce;
- `postinst` sprawdza kompletność plików, składnię Python i shell;
- stara ścieżka `Extensions/PanelAIO` jest usuwana dopiero po pozytywnej walidacji nowej instalacji;
- `postrm` zachowuje ustawienia, listy i backupy użytkownika;
- zachowano historyczną nazwę pakietu `extensions` dla zgodności aktualizacji, a dodano alias `Provides` dla `systemplugins`.

## Architektura

Ryzykowne operacje systemowe zostały wydzielone do osobnych, testowalnych modułów i skryptów. Warstwa interfejsu `legacy_plugin.py` pozostaje częściowo monolityczna z powodu zgodności z istniejącym GUI i obrazami Python 2. Nie wpływa to na transakcyjność nowych operacji, ale dalsze dzielenie samego GUI powinno być wykonywane etapami, aby nie tworzyć regresji.
