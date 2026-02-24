![Logo Panelu AIO](logo.png)

Panel AIO (All-In-One) dla Enigma2

## Panel AIO v9.1.1 - Python Compatibility Update

### 🇬🇧 English:
* **Fixed:** Random missing descriptions/options in menu on Python 2 (OpenATV 6.4 / VTi).
* **Compatibility:** Plugin now works on all Python systems (Py2/Py3).
* **GUI Improvement:** Forced correct text type conversion in GUI lists (Py2: str/UTF-8 bytes, Py3: str) – eliminates display issues like `<not-a-string>` and disappearing function names.
* **Updated/Added:** - ChocholousekPicons
  - CIEFP Oscam Editor
  - FilmXY
  - FootOnsat
  - e-stralker

---

### 🇵🇱 Polski:
* **Naprawiono:** Losowy brak opisów/opcji w menu na Python 2 (OpenATV 6.4 / VTi).
* **Kompatybilność:** Wtyczka działa na wszystkich systemach Python (Py2/Py3).
* **Usprawnienie GUI:** Wymuszona poprawna konwersja typów tekstu w listach GUI (Py2: str/UTF-8 bytes, Py3: str) – eliminuje problem wyświetlania pozycji jako `<not-a-string>` oraz znikających nazw funkcji.
* **Zaktualizowano/Dodano:**
  - ChocholousekPicons
  - CIEFP Oscam Editor
  - FilmXY
  - FootOnsat
  - e-stralker
✨ Główne Funkcje
Panel AIO został zaprojektowany wokół **czterech** głównych sekcji (dostępnych po naciśnięciu strzałek lewo/prawo):

1. Wizard (Super Konfigurator)
Idealny do "czystej" instalacji. Jedno kliknięcie i kreator automatycznie:
* Pobierze i zainstaluje najnowszą listę kanałów (z repozytorium AIO).
* Pobierze i zainstaluje komplet piconów (opcjonalnie).
* Zainstaluje Softcam Feed oraz najnowszą wersję Oscam.
* Zrestartuje GUI, aby zmiany weszły w życie.

2. Listy Kanałów i Picony
* Dostęp do aktualnych list kanałów z dedykowanego repozytorium AIO oraz dynamicznie pobieranych list z S4aUpdater.
* Osobny instalator picon (jeśli nie chcesz korzystać z kreatora).

3. Softcam i Instalatory Wtyczek (1-Click)
Zapomnij o szukaniu poleceń w internecie. Zainstaluj najpopularniejsze dodatki jednym kliknięciem:
* **Zarządzanie Oscam**: Restart, kasowanie hasła WebIf, instalacja Oscam Feed.
* E2iPlayer (dla Python 3)
* AJPanel
* XStreamity, IPTV Dream, ServiceApp, YouTube, E2Kodi v2 i wiele innych!

4. Narzędzia i Diagnostyka
Kompletny "toolbox" dla Twojego dekodera:
* **Backup/Restore**: Szybkie tworzenie i przywracanie kopii zapasowych Listy Kanałów oraz Konfiguracji Oscam.
* Diagnostyka Sieci: Pełny test prędkości (speedtest), sprawdzanie pingu i publicznego IP.
* Narzędzia Systemowe: Menadżer deinstalacji pakietów, aktualizacja `satellites.xml`, czyszczenie pamięci RAM i cache.
* Zarządzanie Hasłem: Szybkie ustawianie lub kasowanie hasła dostępu root/FTP.

💻 Instalacja jest prosta. Połącz się z dekoderem przez terminal SSH (np. PuTTY lub Telnet) i wklej poniższą komendę:


wget -q -O - https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh | /bin/sh

Po instalacji zalecany jest restart Enigma2.

🎮 Sterowanie

🔴 Czerwony: Zmiana języka na Polski

🟢 Zielony: Zmiana języka na Angielski

🟡 Żółty: Restart GUI (Interfejsu)

🔵 Niebieski: Sprawdź aktualizacje wtyczki

STRZAŁKI L/P: Przełączanie między głównymi sekcjami (Listy, Wtyczki, Narzędzia, Diagnostyka)

ℹ️ Info (przycisk 'i'): Wyświetla informacje o wtyczce, notę prawną i listę zmian

☕ Wsparcie i Autor Twórca: Paweł Pawełek (msisystem@t.pl) Grupa Wsparcia: Facebook - Enigma 2 Oprogramowanie, dodatki

Podoba Ci się wtyczka i chcesz wesprzeć jej dalszy rozwój?
Możesz postawić autorowi kawę, skanując kod QR dostępny w interfejsie wtyczki.
