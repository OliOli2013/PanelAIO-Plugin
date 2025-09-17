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

# --- NOWA SEKCJA: Naprawa plików ---
echo "--> Weryfikuję i naprawiam uprawnienia oraz format plików..."

# Spróbuj zainstalować dos2unix, jeśli go nie ma
if ! command -v dos2unix > /dev/null 2>&1; then
    echo "--> Próbuję doinstalować 'dos2unix'..."
    opkg update
    opkg install dos2unix
fi

# Użyj dos2unix na wszystkich skryptach, jeśli jest dostępny
if command -v dos2unix > /dev/null 2>&1; then
    echo "--> Konwertuję format plików na Unix..."
    dos2unix "$PLUGIN_DIR"/*.sh
fi

# Zawsze nadawaj uprawnienia do wykonania
echo "--> Ustawiam uprawnienia do wykonania dla skryptów .sh..."
chmod +x "$PLUGIN_DIR"/*.sh

# --- KONIEC NOWEJ SEKCJI ---

echo ">>> Instalacja PanelAIO zakończona pomyślnie!"
echo ">>> Proszę zrestartować Enigma2, aby zmiany były widoczne."

exit 0
