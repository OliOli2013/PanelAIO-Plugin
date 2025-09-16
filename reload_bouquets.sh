cat > /usr/lib/enigma2/python/Plugins/Extensions/PanelAIO/reload_bouquets.sh << EOF
#!/bin/sh
# Skrypt do przeładowania listy kanałów (bukietów) w Enigma2

# Używamy wget do wywołania API Webinterface, co jest standardową metodą
# Przeładowanie listy serwisów
wget -qO - "http://127.0.0.1/web/servicelistreload?mode=0" > /dev/null 2>&1
# Przeładowanie bukietów
wget -qO - "http://127.0.0.1/web/servicelistreload?mode=4" > /dev/null 2>&1

echo "DEBUG: Polecenia przeładowania bukietów zostały wysłane."

exit 0
EOF
