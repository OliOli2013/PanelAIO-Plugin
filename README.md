![Logo Panelu AIO](logo.png)
Panel AIO Plugin
Oficjalne repozytorium wtyczki Panel All-In-One (AIO) dla dekoderów z oprogramowaniem Enigma2.

Panel AIO to zaawansowana, wielofunkcyjna wtyczka narzędziowa, która centralizuje zarządzanie dekoderem. Umożliwia błyskawiczną instalację list kanałów, popularnych wtyczek i softcamów, a także oferuje kompletny zestaw narzędzi systemowych i diagnostycznych – wszystko w jednym, intuicyjnym miejscu.

🚀 Wielka Aktualizacja do Wersji 2.0! (Październik 2025)
Ta aktualizacja jest obowiązkowa dla użytkowników najnowszych obrazów, takich jak OpenATV 7.6+, OpenPLi 9.1+ i innych opartych na Pythonie 3.11+.

Wersja 2.0 rozwiązuje kluczowe problemy, które powodowały błędy krytyczne (BSOD/GSOD) na nowszych systemach. Wtyczka została w pełni dostosowana i jest teraz w 100% kompatybilna z najnowszym oprogramowaniem.

Co naprawiono?

Krytyczny błąd (BSOD/GSOD) – Usunięto problem powodujący awarię wtyczki przy starcie na systemach z Python 3.11+.

Zawieszanie się tunera – Naprawiono błąd, który powodował zawieszanie się interfejsu po zakończeniu pracy "Super Konfiguratora".

Błąd "Modal open" – Rozwiązano problem z awarią podczas pierwszego uruchomienia wtyczki na niektórych systemach.

Instalator Oscam – Ulepszono inteligentny instalator, który teraz posiada alternatywną metodę instalacji, gdy softcam nie jest dostępny w oficjalnym feedzie.

✨ Główne Możliwości Wtyczki
📡 Listy kanałów
Pobieranie i instalacja gotowych list kanałów z dedykowanego repozytorium oraz zewnętrznego S4aUpdater.

Automatyczne filtrowanie i dynamiczne aktualizacje.

🔑 Softcamy i wtyczki
Oscam – Inteligentny instalator z automatycznym wyborem najlepszej wersji (master/emu/stable) oraz awaryjną metodą instalacji.

Pełne zarządzanie Oscam: restart, kasowanie hasła, edycja pliku oscam.dvbapi z wielu źródeł.

Błyskawiczna instalacja popularnych dodatków online:

AJPanel

E2iPlayer (dla Python 3)

EPG Import

S4aUpdater

JediMakerXtream

YouTube

NCam

🛠️ Narzędzia systemowe i diagnostyka
Menadżer deinstalacji pakietów (opkg).

Aktualizacja pliku satellites.xml i instalacja Softcam Feed.

Pobieranie piconów z GitHub z automatycznym tworzeniem katalogu.

Zarządzanie hasłem dostępu root/FTP (ustawianie i kasowanie).

Test prędkości internetu oraz wyświetlanie IP i pingu.

Informacja o wolnym miejscu i czyszczenie pamięci tymczasowej oraz cache RAM.

🔄 Aktualizacje i Interfejs
Wbudowany system sprawdzania aktualizacji z repozytorium GitHub (wersja i changelog).

Obsługa języków polskiego i angielskiego, zmieniana jednym przyciskiem.

Wbudowany kod QR ze linkiem wsparcia autora.

💻 Instalacja
Połącz się z dekoderem przez terminal (np. PuTTY lub Telnet) i wykonaj poniższą komendę:

Bash

wget -q "--no-check-certificate" https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh -O - | /bin/sh
Po instalacji zalecany jest restart Enigma2.

🖼️ Interfejs i Sterowanie
Wtyczka posiada intuicyjny, trzykolumnowy interfejs. Do nawigacji służą kolorowe przyciski pilota:

🔴 Czerwony – Zmiana języka na Polski

🟢 Zielony – Zmiana języka na Angielski

🟡 Żółty – Restart GUI

🔵 Niebieski – Sprawdź aktualizacje wtyczki

☕ Wsparcie
Jeżeli wtyczka jest dla Ciebie pomocna, możesz wesprzeć jej rozwój, stawiając autorowi kawę. Link znajdziesz w kodzie QR w interfejsie wtyczki.

Autor: Paweł Pawełek (msisystem@t.pl)

Repozytorium: https://github.com/OliOli2013/PanelAIO-Plugin
Kod QR w interfejsie → Buy me a coffee

Autor: Paweł Pawełek (msisystem@t.pl)


Repozytorium: https://github.com/OliOli2013/PanelAIO-Plugin

![Wesprzyj rozwój wtyczki](Kod_QR_buycoffee.png)
