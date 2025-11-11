![Logo Panelu AIO](logo.png)

Panel AIO Plugin
Oficjalne repozytorium wtyczki Panel All-In-One (AIO) dla dekoderów z oprogramowaniem Enigma2.

Panel AIO (wersja 3.1) to zaawansowana, wielofunkcyjna wtyczka narzędziowa, która centralizuje zarządzanie dekoderem. Umożliwia błyskawiczną instalację list kanałów, popularnych wtyczek i softcamów, a także oferuje kompletny zestaw narzędzi systemowych i diagnostycznych – wszystko w jednym, intuicyjnym miejscu.

🚀 Aktualizacja 3.1 — Poprawki i Nowe Funkcje! (Listopad 2025)
Wersja 3.1 skupia się na stabilności, poprawkach błędów zgłoszonych przez użytkowników oraz dodaniu nowych, przydatnych funkcji.

Co nowego w v3.1?
Poprawka "Super Konfiguratora": Naprawiono krytyczny błąd, który powodował zawieszanie się kreatora po instalacji listy kanałów, uniemożliwiając automatyczną instalację piconów i Oscam.

Cicha instalacja zależności: Przy pierwszym uruchomieniu wtyczka nie pokazuje już okna konsoli. Wymagane pakiety (SSL, wget) instalują się teraz dyskretnie w tle, wyświetlając jedynie ekran ładowania.

Nowy Ekran "i - Info": Dodano nowy ekran informacyjny (dostępny pod przyciskiem 'i' na pilocie). Wyświetla on dane o wtyczce, autorze, notę prawną oraz listę ostatnich zmian (changelog) pobieraną na żywo z GitHub.

Poprawki stabilności: Naprawiono błędy (crash) występujące na niektórych obrazach (np. OpenATV 7.6) podczas przeładowywania list kanałów po zakończeniu instalacji.

Nowe instalatory: Dodano szybkie instalatory dla E2Kodi v2 oraz StreamlinkProxy.

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

XStreamity

ServiceApp

StreamlinkProxy

E2Kodi v2

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

Przycisk "Info" (i) wyświetlający szczegóły wtyczki, notę prawną i listę zmian.

⚖️ Nota Prawna
Autor wyraża zgodę na wykorzystywanie wtyczki tylko i wyłącznie na tunerach i systemach Enigma 2.

Jakiekolwiek inne wykorzystywanie, w tym tworzenie poradników na stronach internetowych, YouTube i innych social mediach, wymaga zgody autora wtyczki.

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

ℹ️ Info (i) – Wyświetla informacje o wtyczce, notę prawną i listę zmian

☕ Wsparcie
Jeżeli wtyczka jest dla Ciebie pomocna, możesz wesprzeć jej rozwój, stawiając autorowi kawę. Link znajdziesz w kodzie QR w interfejsie wtyczki.

Autor: Paweł Pawełek (msisystem@t.pl)

Repozytorium: https://github.com/OliOli2013/PanelAIO-Plugin
![Wesprzyj rozwój wtyczki](Kod_QR_buycoffee.png)
