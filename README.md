![Logo Panelu AIO](logo.png)

# Panel AIO (All-In-One) dla Enigma2

Panel AIO (aktualna wersja **5.0**) to kompletne centrum zarządzania Twoim dekoderem Enigma2. Zamiast instalować i pamiętać o wielu różnych dodatkach, AIO łączy je wszystkie w jedno, intuicyjne menu z podziałem na zakładki.

Wtyczka została stworzona, aby maksymalnie uprościć konfigurację dekodera – zarówno dla początkujących, jak i zaawansowanych użytkowników.

## 🚀 Nowości w wersji 5.0 (Grudzień 2025)

Ta aktualizacja to **całkowita przebudowa** interfejsu oraz logiki wtyczki, skupiająca się na stabilności i nowych narzędziach diagnostycznych.

* **🆕 Nowy Interfejs (Zakładki):** Menu nie jest już jedną długą listą. Wprowadzono nawigację **Lewo/Prawo**, która przełącza między 4 kategoriami: *Listy, Softcam, Narzędzia, Info*.
* **🆕 Aktualizacje Online:** Dodano możliwość pobierania najnowszych plików konfiguracyjnych:
    * `oscam.srvid` oraz `oscam.srvid2` (z oficjalnych repozytoriów + fallback).
    * `SoftCam.Key` (pobieranie z repozytorium online).
* **➕ Monitor Systemowy:** Podgląd użycia CPU, RAM, temperatury oraz zajętości dysków w czasie rzeczywistym.
* **➕ Menedżerowie Systemowi:** Dodano wbudowane narzędzia:
    * **Przeglądarka Logów:** (syslog, messages, crashlog).
    * **Menedżer Cron:** Edycja harmonogramu zadań.
    * **Menedżer Usług:** Zarządzanie usługami (FTP, Samba, SSH itp.).
    * **Menedżer Deinstalacji:** Graficzne usuwanie pakietów systemowych.
* **🐛 Kluczowe Poprawki Stabilności:** Usunięto moduły powodujące restarty GUI ("Green Screen") na nowszych systemach (Narzędzia Sieciowe, Auto Backup).
* **⚡ Ulepszony "Super Konfigurator":** Kreator pierwszej instalacji działa teraz stabilniej na osobnym ekranie postępu.

---

## ✨ Główne Funkcje (Podział na Zakładki)

Nawigacja między sekcjami odbywa się za pomocą **STRZAŁEK LEWO / PRAWO** na pilocie.

### 1. 📺 Listy Kanałów
* Dostęp do aktualnych list kanałów z dedykowanego repozytorium AIO.
* Dynamicznie pobierane listy z S4aUpdater.
* Obsługa archiwów `.zip`, `.tar.gz` oraz instalacja bukietów `.tv`.

### 2. 🔑 Softcam i Wtyczki (1-Click)
Zainstaluj najpopularniejsze dodatki jednym kliknięciem:
* **Zarządzanie Oscam:** Restart, kasowanie hasła, instalacja Oscam Feed (wykrywanie wersji), NCam.
* **Klucze:** Szybka aktualizacja `SoftCam.Key` oraz plików `srvid`.
* **Wtyczki:** E2iPlayer, AJPanel, XStreamity, IPTV Dream, ServiceApp, YouTube, E2Kodi v2, J00zeks Feed.

### 3. ⚙️ Narzędzia Systemowe
Narzędzia do zarządzania systemem:
* **✨ Super Konfigurator (Wizard):** Automatyczna instalacja "na czysto" (Zależności -> Lista -> Picony -> Oscam).
* **Backup/Restore:** Tworzenie i przywracanie kopii Listy Kanałów oraz Konfiguracji Oscam.
* **Picony:** Instalator picon (wersja transparentna).
* **Inne:** Aktualizacja `satellites.xml`, Menedżer deinstalacji.

### 4. ℹ️ Info i Diagnostyka
Kompletny "toolbox" diagnostyczny:
* **Monitor Systemowy:** Wykresy wydajności (CPU/RAM/Temp).
* **Log Viewer:** Szybki podgląd logów systemowych.
* **Czyszczenie:** Auto RAM Cleaner (cykliczne czyszczenie), czyszczenie cache, zwalnianie pamięci.
* **Usługi:** Zarządzanie hasłami (FTP/Root) oraz usługami systemowymi.

---

## 💻 Instalacja

Połącz się z dekoderem przez terminal SSH (np. PuTTY, Terminal lub Telnet) i wklej poniższą komendę:

```bash
wget -q "--no-check-certificate" https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh -O - | /bin/sh

Po instalacji zalecany jest restart Enigma2 (GUI).
