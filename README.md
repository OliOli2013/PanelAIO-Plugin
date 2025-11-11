![Logo Panelu AIO](logo.png)

Panel AIO (All-In-One) dla Enigma2

Panel AIO (wersja 3.1) to kompletne centrum zarządzania Twoim dekoderem Enigma2. Zamiast instalować i pamiętać o wielu różnych dodatkach, AIO łączy je wszystkie w jedno, intuicyjne menu.

Wtyczka została stworzona, aby maksymalnie uprościć konfigurację dekodera – zarówno dla początkujących, jak i zaawansowanych użytkowników.

🚀 Nowości w wersji 3.1 (Listopad 2025)

Ta aktualizacja skupia się na stabilności, poprawkach błędów zgłoszonych przez użytkowników oraz dodaniu nowych, przydatnych funkcji:

Kluczowa poprawka "Super Konfiguratora": Naprawiono błąd, który powodował zawieszanie się kreatora po instalacji listy kanałów. Teraz cały proces (lista, picony, oscam) przechodzi płynnie do końca.

Nowy Ekran Informacyjny (przycisk 'i'): Dodano czytelne okno z informacjami o autorze, grupie na Facebooku, nocie prawnej oraz liście ostatnich zmian pobieranej na żywo z GitHub.

Cicha Instalacja Zależności: Wtyczka nie pokazuje już okna konsoli przy pierwszym starcie. Niezbędne pakiety (SSL, wget) instalują się dyskretnie w tle.

Dodatkowe Instalatory: Dodano szybkie instalatory dla E2Kodi v2 oraz StreamlinkProxy.

Poprawki Stabilności: Rozwiązano problemy (crashe) zgłaszane przez użytkowników OpenATV 7.6.

✨ Główne Funkcje
Panel AIO został zaprojektowany wokół trzech głównych sekcji:

1. Wizard (Super Konfigurator)
Idealny do "czystej" instalacji. Jedno kliknięcie i kreator automatycznie:

Pobierze i zainstaluje najnowszą listę kanałów.

Pobierze i zainstaluje komplet piconów.

Zainstaluje Softcam Feed oraz najnowszą wersję Oscam.

Zrestartuje GUI, aby zmiany weszły w życie.

2. Listy Kanałów i Picony

Dostęp do aktualnych list kanałów z dedykowanego repozytorium AIO (m.in. Bzyk, JakiTaki) oraz dynamicznie pobieranych list z S4aUpdater.

Osobny instalator picon (jeśli nie chcesz korzystać z kreatora).

3. Instalatory Wtyczek (1-Click)

Zapomnij o szukaniu poleceń w internecie. Zainstaluj najpopularniejsze dodatki jednym kliknięciem:

E2iPlayer (dla Python 3)

AJPanel

XStreamity

ServiceApp

YouTube

E2Kodi v2

...i wiele innych!

4. Narzędzia i Diagnostyka

Kompletny "toolbox" dla Twojego dekodera:

Zarządzanie Oscam: Restart, kasowanie hasła WebIf, pobieranie oscam.dvbapi.

Diagnostyka Sieci: Pełny test prędkości (speedtest), sprawdzanie pingu i publicznego IP.

Narzędzia Systemowe: Menadżer deinstalacji pakietów, aktualizacja satellites.xml, czyszczenie pamięci RAM i cache.

Zarządzanie Hasłem: Szybkie ustawianie lub kasowanie hasła dostępu root/FTP.

💻 Instalacja
Instalacja jest prosta. Połącz się z dekoderem przez terminal SSH (np. PuTTY lub Telnet) i wklej poniższą komendę:


wget -q "--no-check-certificate" https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh -O - | /bin/sh

Po instalacji zalecany jest restart Enigma2.

🎮 Sterowanie
🔴 Czerwony: Zmiana języka na Polski

🟢 Zielony: Zmiana języka na Angielski

🟡 Żółty: Restart GUI (Interfejsu)

🔵 Niebieski: Sprawdź aktualizacje wtyczki

ℹ️ Info (przycisk 'i'): Wyświetla informacje o wtyczce, notę prawną i listę zmian

⚖️ Nota Prawna
Autor wyraża zgodę na wykorzystywanie wtyczki tylko i wyłącznie na tunerach i systemach Enigma 2.

Jakiekolwiek inne wykorzystywanie, w tym tworzenie poradników na stronach internetowych, YouTube i innych social mediach, wymaga zgody autora wtyczki.

☕ Wsparcie i Autor
Twórca: Paweł Pawełek (msisystem@t.pl) Grupa Wsparcia: Facebook - Enigma 2 Oprogramowanie, dodatki

Podoba Ci się wtyczka i chcesz wesprzeć jej dalszy rozwój? Możesz postawić autorowi kawę, skanując kod QR dostępny w interfejsie wtyczki.
![Wesprzyj rozwój wtyczki](Kod_QR_buycoffee.png)
