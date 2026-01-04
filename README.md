![Logo Panelu AIO](logo.png)

Panel AIO (All-In-One) dla Enigma2

Panel AIO (wersja **4.3**) to kompletne centrum zarządzania Twoim dekoderem Enigma2. Zamiast instalować i pamiętać o wielu różnych dodatkach, AIO łączy je wszystkie w jedno, intuicyjne menu.

Wtyczka została stworzona, aby maksymalnie uprościć konfigurację dekodera – zarówno dla początkujących, jak i zaawansowanych użytkowników.

🚀 Nowości w wersji 4.3 (Listopad 2025)

Ta aktualizacja skupia się na ulepszeniu narzędzi systemowych, instalatorów oraz poprawie stabilności operacji:

* **Dodano Instalator Softcam:** W sekcji Softcam i Wtyczki dodano nową, bezpośrednią opcję instalacji Softcam Feed.
* **Dodan Instalator IPTV Dream:** Instalacja wtyczki IPTV Dream została uproszczona i teraz startuje bezpośrednio w tle, bez konieczności sprawdzania wersji, co przyspiesza proces.
* **Poprawa Czyszczenia Cache:** Narzędzie do Czyszczenia Pamięci Tymczasowej (`/tmp`) zostało ulepszone – bezpiecznie usuwa popularne pliki instalacyjne (.ipk, .zip, .tar.gz) oraz logi, z pominięciem kluczowych dla systemu plików.
* **Nowa Nazwa Oscam:** Pozycja "Oscam Feed - Instalator (Auto)" wyświetla teraz wykrytą wersję (np. `Oscam Feed - 11700`) dla lepszej informacji o pakiecie.
* **Kluczowa Poprawka "Super Konfiguratora" (w 3.1):** Naprawiono błąd, który powodował zawieszanie się kreatora po instalacji listy kanałów. Cały proces (lista, picony, oscam) przechodzi płynnie do końca.
* **Nowy Ekran Informacyjny (w 3.1):** Dodano czytelne okno z informacjami o autorze, nocie prawnej oraz liście ostatnich zmian pobieranej na żywo z GitHub.
* **Cicha Instalacja Zależności (w 3.1):** Wtyczka nie pokazuje już okna konsoli przy pierwszym starcie. Niezbędne pakiety instalują się dyskretnie w tle.

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

```bash
wget -q "--no-check-certificate" https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh -O - | /bin/sh
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
