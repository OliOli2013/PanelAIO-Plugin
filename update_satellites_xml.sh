#!/bin/sh
# Skrypt do pobierania satellites.xml

echo 'Rozpoczynam pobieranie satellites.xml (0%)...'
wget -O /etc/tuxbox/satellites.xml http://raw.githubusercontent.com/OpenPLi/tuxbox-xml/master/xml/satellites.xml || { echo 'Błąd: Nie udało się pobrać satellites.xml!'; exit 1; }

echo 'Pobrano i zapisano satellites.xml pomyślnie (100%).'
