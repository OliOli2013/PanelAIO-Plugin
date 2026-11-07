# 📺 AIO Panel 18.0.0 — centrum zarządzania Enigma2

**Wydanie:** 7 listopada 2026 r.  
**Autor:** Paweł Pawełek | AIO Team  
**Repozytorium:** [OliOli2013/PanelAIO-Plugin](https://github.com/OliOli2013/PanelAIO-Plugin)  
**Języki interfejsu:** polski i angielski

AIO Panel to rozbudowane centrum narzędzi dla odbiorników **Enigma2**. Pozwala zarządzać listami kanałów, piconami, wtyczkami, skórkami, emulatorami OSCam, kopiami zapasowymi i narzędziami systemowymi — z poziomu pilota.

Wersja **18.0.0** rozwija trzy obszary: bezpieczniejszą aktualizację list satelitarnych, wydzieloną zakładkę **„Moje projekty”** oraz aktualniejsze informacje o wersjach OSCam.

## 🆕 Co nowego w 18.0.0?

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

- **[AIO Panel 18.0.0 — IPK](release/enigma2-plugin-extensions-panelaio_18.0.0_all.ipk)** — systemy z **OPKG**, np. wiele obrazów OpenATV i OpenPLi;
- **[AIO Panel 18.0.0 — DEB](release/enigma2-plugin-extensions-panelaio_18.0.0_all.deb)** — systemy z **DPKG**, np. wybrane obrazy DreamOS.

Wybierz pakiet odpowiedni dla menedżera pakietów zainstalowanego na tunerze.

Przykładowa instalacja po przesłaniu pliku do katalogu `/tmp`:

**OPKG (IPK):**

```sh
opkg install /tmp/enigma2-plugin-extensions-panelaio_18.0.0_all.ipk
```

**DPKG (DEB):**

```sh
dpkg -i /tmp/enigma2-plugin-extensions-panelaio_18.0.0_all.deb
```

Po instalacji uruchom ponownie interfejs Enigma2, jeżeli jest to wymagane.

### Aktualizacja z poziomu panelu

W AIO Panel można skorzystać z funkcji sprawdzania aktualizacji (niebieski przycisk lub dział „AIO / Aktualizacje”, zależnie od skórki). Działanie automatycznej aktualizacji zależy od poprawnego opublikowania pakietów i metadanych wydania.

## ✅ Testy i ważne ograniczenia

W procesie przygotowania 18.0.0 sprawdzono:

- składnię **46 plików Python** bez tworzenia bytecode na odbiorniku;
- wewnętrzny test AIO Panel;
- pozycję nowej zakładki, tłumaczenia PL/EN, **10 unikatowych projektów** i brak powielania ich instalatorów;
- budowanie pakietów **IPK/DEB**, metadane wersji i skrypty instalacyjne.

Dodatkowo tester potwierdził na Ustym 4K Pro zachowanie konfiguracji FAVOURITES podczas aktualizacji opartej na r3.

**Nie wykonano jeszcze pełnych testów wydania 18.0.0 na wszystkich fizycznych odbiornikach ani wykonawczego testu środowiska Python 2.** Przed wdrożeniem na wiele urządzeń sprawdź aktualizację na jednym tunerze i zachowaj kopię konfiguracji.

Szczegółowe informacje: [RELEASE_NOTES_18.0.0.md](RELEASE_NOTES_18.0.0.md) oraz [changelog.txt](changelog.txt).

## 📬 Projekt i zgłoszenia

- [Repozytorium AIO Panel](https://github.com/OliOli2013/PanelAIO-Plugin)
- [Zgłoszenia błędów i propozycje](https://github.com/OliOli2013/PanelAIO-Plugin/issues)
- [Pozostałe projekty autora](https://github.com/OliOli2013?tab=repositories)

---

**AIO Panel — wszystko w jednym miejscu dla Enigma2.**  
**© Paweł Pawełek | AIO Team**
