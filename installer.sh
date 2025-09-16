#!/bin/sh
# Skrypt instalacyjny dla wtyczki PanelAIO

# --- Konfiguracja ---
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/PanelAIO"
BASE_URL="https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main"

# --- Logika instalacji ---
echo ">>> Rozpoczynam instalację/aktualizację wtyczki PanelAIO..."

# Usuń starą wersję, jeśli istnieje, aby zapewnić czystą instalację
if [ -d "$PLUGIN_DIR" ]; then
    echo "--> Znaleziono starą wersję. Usuwam katalog: $PLUGIN_DIR"
    rm -rf "$PLUGIN_DIR"
fi

# Utwórz katalog wtyczki
echo "--> Tworzę katalog wtyczki..."
mkdir -p "$PLUGIN_DIR"

# Pobierz wszystkie niezbędne pliki
echo "--> Pobieram pliki wtyczki..."
wget -q "$BASE_URL/plugin.py" -O "$PLUGIN_DIR/plugin.py"
wget -q "$BASE_URL/logo.png" -O "$PLUGIN_DIR/logo.png"
wget -q "$BASE_URL/selection.png" -O "$PLUGIN_DIR/selection.png"
wget -q "$BASE_URL/install_archive_script.sh" -O "$PLUGIN_DIR/install_archive_script.sh"
wget -q "$BASE_URL/update_satellites_xml.sh" -O "$PLUGIN_DIR/update_satellites_xml.sh"
wget -q "$BASE_URL/reload_bouquets.sh" -O "$PLUGIN_DIR/reload_bouquets.sh" # <-- DODANA LINIA

# Ustaw uprawnienia do wykonywania dla skryptów .sh
echo "--> Ustawiam uprawnienia dla skryptów..."
chmod +x "$PLUGIN_DIR/install_archive_script.sh"
chmod +x "$PLUGIN_DIR/update_satellites_xml.sh"
chmod +x "$PLUGIN_DIR/reload_bouquets.sh" # <-- DODANA LINIA

echo ">>> Instalacja PanelAIO zakończona pomyślnie!"
echo ">>> Proszę zrestartować Enigma2, aby zmiany były widoczne."

exit 0
