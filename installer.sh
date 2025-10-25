#!/bin/sh
# Skrypt instalacyjny dla wtyczki PanelAIO

# --- Konfiguracja ---
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/PanelAIO"
BASE_URL="https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main"

# --- Logika instalacji ---
echo ">>> Rozpoczynam instalację/aktualizację wtyczki PanelAIO..."

# Usuń starą wersję, jeśli istnieje
if [ -d "$PLUGIN_DIR" ]; then
    echo "--> Usuwam starą wersję..."
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
wget -q "$BASE_URL/reload_bouquets.sh" -O "$PLUGIN_DIR/reload_bouquets.sh"
wget -q "$BASE_URL/Kod_QR_buycoffee.png" -O "$PLUGIN_DIR/Kod_QR_buycoffee.png"

# --- Zmodyfikowana Sekcja: Ustawianie uprawnień ---
echo "--> Ustawiam uprawnienia do wykonania dla skryptów .sh..."
chmod +x "$PLUGIN_DIR"/*.sh
# Usunięto sprawdzanie i instalację dos2unix

echo ">>> Instalacja PanelAIO zakończona pomyślnie!"
echo ">>> Proszę ZAMKNĄĆ to okno i RĘCZNIE zrestartować Enigma2 (GUI), aby zmiany były widoczne."

exit 0
