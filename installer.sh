#!/bin/sh
# Skrypt instalacyjny dla Panelu AIO

# Konfiguracja
PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/PanelAIO"
GIT_USER="OliOli2013"
GIT_REPO="PanelAIO-Plugin"
# Add all necessary scripts to this list
FILES="plugin.py logo.png selection.png install_archive_script.sh update_satellites_xml.sh" 

# Komunikaty
echo ">>>"
echo ">>> Instalacja wtyczki Panel AIO..."
echo ">>>"

# Usuwanie starej wersji
if [ -d "$PLUGIN_PATH" ]; then
    echo "> Usuwanie poprzedniej wersji..."
    rm -rf "$PLUGIN_PATH"
fi

# Tworzenie katalogu
mkdir -p "$PLUGIN_PATH"

# Pobieranie plików
echo "> Pobieranie plików wtyczki..."
for FILE in $FILES; do
    wget -q "--no-check-certificate" "https://raw.githubusercontent.com/$GIT_USER/$GIT_REPO/main/$FILE" -O "$PLUGIN_PATH/$FILE"
done

# === WAŻNA POPRAWKA - NADAWANIE UPRAWNIEŃ ===
echo "> Ustawianie uprawnień do uruchamiania..."
chmod +x "$PLUGIN_PATH"/*.sh

# Zakończenie
echo ">>>"
echo ">>> Instalacja zakończona pomyślnie!"
echo ">>> Proszę zrestartować Enigma2."
echo ">>>"

exit 0
