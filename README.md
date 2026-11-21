# 📺 AIO Panel 18.2.0 — centrum zarządzania Enigma2


## Nowości 18.2.0

Nowe kolorowe ikony kategorii i instalatorów, podglądy funkcji (oznaczone ilustracje),
dokładniejsze znajdowanie rzeczywistych zrzutów skórek oraz czytelna grafika zastępcza,
gdy autor nie udostępnia zdjęcia. Wybór piconów ma osobne okno z przełączanym jasnym i ciemnym tłem
dla **ilustracji przezroczystości**; nie jest to zdjęcie z archiwum piconów.
**Wydanie 18.2.0** · wersja standardowa AIO Team

**Autor:** Paweł Pawełek | AIO Team  
**Repozytorium:** [OliOli2013/PanelAIO-Plugin](https://github.com/OliOli2013/PanelAIO-Plugin)  
**Języki interfejsu:** polski i angielski

AIO Panel to rozbudowane centrum narzędzi dla odbiorników **Enigma2**. Pozwala zarządzać listami kanałów, piconami, wtyczkami, skórkami, emulatorami OSCam, kopiami zapasowymi i narzędziami systemowymi — z poziomu pilota.

## Motywy w 18.1.2

W otwartym panelu naciśnij **MENU**, zaznacz **Motyw** i użyj strzałek **◀ / ▶**. Okno od razu pokazuje wybrane kolory. **Zielony** zapisuje wygląd panelu, **EXIT** anuluje podgląd. Ustawienie znajdziesz również w **System / Konserwacja → Wygląd panelu**.

Do wyboru jest dziewięć motywów. **Ocean**, **Bursztyn** i **Wysoki kontrast** zachowują dotychczasowe identyfikatory. Nowe warianty to **Szmaragd**, **Ametyst**, **Rubin**, **Turkus**, **Grafit** i **Perła (jasny)**. Perła ma jasne tło i ciemne opisy klawiszy pilota. Ikony menu oraz zdjęcia skórek można włączać niezależnie od wybranego motywu.

Paczki 18.1.2 zawierają poprawiony edytor z 18.1.1 i dają się zainstalować bezpośrednio na 18.0.0.

## Poprawka w 18.1.1

Na odbiorniku SF8008 z OpenATV 8.1.0 beta naciśnięcie **MENU** w panelu powodowało restart Enigma2. Poprawiono otwieranie ekranu **Wygląd panelu** i dodano test uruchamiania jego elementów. Po aktualizacji uruchom ponownie interfejs Enigma2, otwórz **MENU**, wybierz motyw i zapisz zielonym przyciskiem.

## Funkcje dodane w 18.1.0

- Naciśnij **MENU** w otwartym panelu albo wybierz **System / Konserwacja → Wygląd panelu**. Możesz osobno przełączać ikony menu i podglądy skórek. Strzałki zmieniają wartość, zielony przycisk zapisuje ustawienia, a EXIT anuluje edycję.
- Zaznacz skórkę, aby zobaczyć jej zdjęcie. **INFO** powiększa podgląd, **OK** otwiera instalację. AIOHD NEXT ma podgląd również w **Moje projekty**. Pakiet zawiera 12 zdjęć. Dodatkowe skórki z feedu mogą pokazać plik z tunera lub pobrać zdjęcie w tle. Źródła zdjęć zebrano w [wykazie autorów](assets/previews/credits.txt).
- Superkonfigurator w wariantach **START** i **pełnym z piconami** zapisuje kopię dotychczasowej listy i automatycznie zastępuje ją listą **Polska 13E AIO Panel**. Poprzednie bukiety, własne IPTV i lokalne usługi można odzyskać przez **Kopie / Przywracanie → Restore Listy Kanałów**. Wariant samych zależności pomija listy. W zakładce **Listy kanałów** nadal można ręcznie wybrać aktualizację SAT z zachowaniem danych lub pełną wymianę.
- Panel zapamiętuje ręczny wybór języka. Aglare, Luka i Maxy korzystają z pakietu odpowiedniego dla wykrytego OpenATV lub OpenPLi. W Pythonie 2 panel filtruje również wpisy prowadzące do wydań wymagających Pythona 3.
- Jihad FHD może korzystać z pakietu udostępnionego przez feed obrazu. Podczas weryfikacji 18.1.0 zewnętrzny IPK autora miał niestandardowy nagłówek i wadliwie zakończony plik control. Gdy feed nie oferuje tej skórki, walidator odrzuca tę wersję pobraną od wydawcy. Podgląd jest dostępny.

## Funkcje wprowadzone w 18.0.0

### 🛰️ Aktualizacja tylko części satelitarnej

W trybie **aktualizacji istniejącej listy z zachowaniem danych użytkownika** AIO Panel aktualizuje kanały i transpondery SAT, chroniąc lokalną konfigurację odbiornika:

- **DVB-T/T2** — zachowanie lokalnie wyszukanych usług, ich nazw oraz parametrów multipleksów;
- **DVB-C** — zachowanie usług telewizji kablowej;
- **FAVOURITES** — zachowanie własnych bukietów, ich zawartości, kolejności, separatorów i numeracji;
- **IPTV** — zachowanie własnych bukietów i referencji strumieni;
- **bezpieczeństwo operacji** — kontrola zgodności usług lokalnych oraz wycofanie zmian w razie wykrycia niespójności.

Mechanizm opiera się na poprawkach z testowej wersji **17.0.4-r3**. W zgłoszonym teście na **Ustym 4K Pro** użytkownik potwierdził zachowanie całej listy FAVOURITES, nazw i numeracji **11130–11197** bez ponownego importowania danych. To wynik konkretnego testu, a nie gwarancja zgodności ze wszystkimi systemami i tunerami.

> **Uwaga:** tryb pełnej wymiany listy działa inaczej — może zastąpić dotychczasowe dane. Przed instalacją lub dużą aktualizacją wykonaj kopię zapasową konfiguracji `/etc/enigma2/`.

### 🧩 Nowa zakładka „Moje projekty”

Nowa zakładka jest umieszczona **bezpośrednio pod „Listy kanałów”**. Zgromadzono w niej projekty Enigma2 autora — bez powielania ich pozycji instalacyjnych w kategoriach IPTV, EPG, skórki lub narzędzia.

| Projekt | Zastosowanie |
| --- | --- |
| [AIO Panel](https://github.com/OliOli2013/PanelAIO-Plugin) | Centrum zarządzania i aktualizacje panelu |
| [IPTV Dream](https://github.com/OliOli2013/IPTV-Dream-Plugin) | Odtwarzanie IPTV |
| [MyUpdater](https://github.com/OliOli2013/MyUpdater-Plugin) | Aktualizowanie wtyczek Enigma2 |
| [PiconUpdater](https://github.com/OliOli2013/PiconUpdater) | Zarządzanie piconami |
| [Simple IPTV EPG](https://github.com/OliOli2013/SimpleIPTV_EPG) | Dopasowanie EPG i piconów do IPTV |
| [NeoRadio](https://github.com/OliOli2013/NeoRadio) | Radio internetowe |
| [PP Channel Sync](https://github.com/OliOli2013/PPChannelSync-Plugin) | Synchronizacja kanałów |
| [E2 Doctor](https://github.com/OliOli2013/E2-Doctor-Plugin) | Diagnostyka tunera (Python 3) |
| [AIOHD NEXT](https://github.com/OliOli2013/AIOHD-NEXT-Skin) | Skórka Enigma2 |
| [OpenCamView](https://github.com/OliOli2013/OpenCamView-Plugin) | Podgląd kamer IP/RTSP/ONVIF (Python 3) |

Repozytorium list kanałów **PanelAIO-Lists** pozostaje obsługiwane w kategorii „Listy kanałów”. Repozytorium strony internetowej nie jest instalowaną wtyczką i dlatego nie występuje w tej zakładce.

### 🔐 OSCam i aktualność wersji

- **OSCam Levi45:** wersja udostępniona w repozytorium autora w dniu wydania to **11968 / Emu r803**. Panel korzysta z informacji pochodzących z aktualnego instalatora źródłowego zamiast stale wyświetlać starszy numer `11966`.
- **OSCam-Emu z feedu odbiornika:** wersja dostępna do instalacji jest odróżniona od wersji już zainstalowanej. Może się różnić pomiędzy systemami i feedami.

Źródło Levi45: [levi-45/Levi45Emulator](https://github.com/levi-45/Levi45Emulator).

## 📋 Układ menu

1. **Listy kanałów**
2. **Moje projekty**
3. IPTV / Odtwarzacze
4. EPG / Picony
5. Skórki
6. Softcam / OSCam
7. Wtyczki / Feedy
8. Kopie / Przywracanie
9. System / Konserwacja
10. Diagnostyka / Naprawa
11. Kontakt / Społeczność
12. Dla dorosłych 18+
13. AIO / Aktualizacje

Nazwy pozycji są tłumaczone zgodnie z wybranym językiem panelu.

## 🛠️ Pozostałe funkcje

AIO Panel zachowuje rozwiązania rozwijane we wcześniejszych wersjach, w tym:

- listy kanałów AIO Team i narzędzia aktualizacji/przywracania;
- picony dla **Hot Bird 13°E**, **Astra 19,2°E** oraz zestawu łączonego 13°E + 19,2°E;
- obsługę instalacji wtyczek i skórek, m.in. E2iPlayer, JediMakerXtream, ChocholousekPicons i Obsidian FHD;
- operacje na OSCam, aktualizację danych oraz kopie zapasowe;
- diagnostykę, narzędzia konserwacji i informacje o postępie;
- funkcje szybkiego dostępu, wyszukiwania, historii i ulubionych akcji panelu.

Dostępność poszczególnych pakietów zewnętrznych zależy od ich źródeł, zgodności z obrazem Enigma2 oraz architektury odbiornika.

## 📦 Instalacja i aktualizacja

### Pobieranie pakietów

- **[AIO Panel 18.2.0 — IPK](release/enigma2-plugin-extensions-panelaio_18.2.0_all.ipk)** — systemy z **OPKG**, np. wiele obrazów OpenATV i OpenPLi;
- **[AIO Panel 18.2.0 — DEB](release/enigma2-plugin-extensions-panelaio_18.2.0_all.deb)** — systemy z **DPKG**, np. wybrane obrazy DreamOS.

Wybierz pakiet odpowiedni dla menedżera pakietów zainstalowanego na tunerze.

Przykładowa instalacja po przesłaniu pliku do katalogu `/tmp`:

**OPKG (IPK):**

```sh
opkg install /tmp/enigma2-plugin-extensions-panelaio_18.2.0_all.ipk
```

**DPKG (DEB):**

```sh
dpkg -i /tmp/enigma2-plugin-extensions-panelaio_18.2.0_all.deb
```

Po instalacji uruchom ponownie interfejs Enigma2, jeżeli jest to wymagane.

### Aktualizacja z poziomu panelu

W AIO Panel można skorzystać z funkcji sprawdzania aktualizacji (niebieski przycisk lub dział „AIO / Aktualizacje”, zależnie od skórki). Działanie automatycznej aktualizacji zależy od poprawnego opublikowania pakietów i metadanych wydania.

## ✅ Testy i ważne ograniczenia

Test interfejsu przechodzi przez wszystkie pozycje 13 kategorii w polskiej i angielskiej wersji na testowym zestawie danych. Sprawdza nawigację pilotem, uruchomienie właściwej funkcji, dobór wariantu skórki, zapis ustawień, powiększenie obrazu i oba sposoby instalacji listy. Sprawdzone środowiska to Python 3.12 i Python 2.7 (PyPy). Wywołania instalujące pakiety są w tym teście przechwytywane. W osobnej próbie instalator i przywracanie pracowały na rzeczywistym archiwum Polska 13E oraz katalogach testowych.

Działanie edytora 18.1.1 potwierdzono na SF8008 z OpenATV. Nowe palety 18.1.2 sprawdzono programowo, a ich odbiór na telewizorze zależy również od ustawień obrazu. Dostępność wtyczek zewnętrznych zależy od pakietów dla danego obrazu i wersji Pythona.

~~~sh
python3 tests/test_dashboard.py
./build_ipk.sh
sha256sum -c SHA256SUMS.txt
~~~

Historia wersji znajduje się w [changelog.txt](changelog.txt).

## 📬 Projekt i zgłoszenia

- [Repozytorium AIO Panel](https://github.com/OliOli2013/PanelAIO-Plugin)
- [Zgłoszenia błędów i propozycje](https://github.com/OliOli2013/PanelAIO-Plugin/issues)
- [Pozostałe projekty autora](https://github.com/OliOli2013?tab=repositories)

---

**AIO Panel — wszystko w jednym miejscu dla Enigma2.**  
**© Paweł Pawełek | AIO Team**
