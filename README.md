![Logo Panelu AIO](logo.png)
Panel AIO-Plugin

Oficjalne repozytorium wtyczki Panel All-In-One (AIO) dla Enigma2

Panel AIO to zaawansowana, wielofunkcyjna wtyczka narzędziowa dla dekoderów z oprogramowaniem Enigma2.
Umożliwia zarządzanie listami kanałów, instalację popularnych wtyczek i softcamów, a także oferuje zestaw narzędzi systemowych i diagnostycznych – wszystko w jednym miejscu.

✨ Główne możliwości wtyczki
📡 Listy kanałów

Pobieranie i instalacja list kanałów z repozytorium PanelAIO oraz zewnętrznego S4aUpdater.

Automatyczne filtrowanie list (np. usuwanie niepożądanych źródeł).

Dynamiczne aktualizacje z pliku manifest.json.

🔑 Softcamy i wtyczki

Oscam – inteligentny instalator z automatycznym wyborem najlepszej wersji (master/emu/stable).

Restart Oscam i czyszczenie hasła Oscam.

Zarządzanie plikiem oscam.dvbapi: pobieranie z wielu repozytoriów, czyszczenie zawartości, możliwość wprowadzenia własnego URL.

Instalacja popularnych dodatków online:

AJPanel

E2iPlayer (Python3)

EPG Import

S4aUpdater

JediMakerXtream

YouTube plugin

NCam 15.5

🛠️ Narzędzia systemowe

Menadżer deinstalacji pakietów (opkg).

Instalacja Softcam Feed.

Aktualizacja pliku satellites.xml.

Pobieranie piconów z GitHub (z automatycznym nadpisywaniem i tworzeniem katalogu).

Zarządzanie hasłem root/FTP (ustawianie i kasowanie).

🧹 Diagnostyka i czyszczenie

Test prędkości internetu.

Wyświetlanie własnego adresu IP i średniego pingu.

Informacja o wolnym miejscu na dysku/flash.

Czyszczenie pamięci tymczasowej (/tmp) i cache RAM.

🔄 Aktualizacje i wsparcie

Wbudowany system sprawdzania aktualizacji z repozytorium GitHub (wersja, changelog).

Szybka aktualizacja do najnowszej wersji jednym kliknięciem.

Wbudowany kod QR z linkiem wsparcia autora.

Obsługa języków: polski / angielski (zmiana jednym przyciskiem pilota).

💻 Instalacja

Wgraj i uruchom wtyczkę bezpośrednio przez Telnet/SSH:

wget -q "--no-check-certificate" https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh -O - | /bin/sh

🖼️ Interfejs

Trzykolumnowy panel: Listy Kanałów, Softcam & Plugins, Tools & Extras.

Obsługa przycisków pilota:

🔴 Czerwony – Polski

🟢 Zielony – English

🟡 Żółty – Restart GUI

🔵 Niebieski – Wyjście

☕ Wsparcie

Jeżeli wtyczka jest dla Ciebie pomocna, możesz wesprzeć rozwój autora:
Kod QR w interfejsie → Buy me a coffee

Autor: Paweł Pawełek (msisystem@t.pl)


Repozytorium: https://github.com/OliOli2013/PanelAIO-Plugin

![Wesprzyj rozwój wtyczki](Kod_QR_buycoffee.png)


Instalacja Telnet: wget -q "--no-check-certificate" https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh -O - | /bin/sh
