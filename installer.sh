#!/bin/sh
# Skrypt instalacyjny dla wtyczki PanelAIO (v3 - pobieranie do /tmp)

# --- Konfiguracja ---
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/PanelAIO"
TMP_UPDATE_DIR="/tmp/PanelAIO_Update"
BASE_URL="https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main"

# --- Logika instalacji ---
echo ">>> Rozpoczynam instalację/aktualizację wtyczki PanelAIO..."

# Utwórz czysty katalog tymczasowy
echo "--> Przygotowuję katalog tymczasowy..."
rm -rf "$TMP_UPDATE_DIR"
mkdir -p "$TMP_UPDATE_DIR"

# Pobierz wszystkie niezbędne pliki do katalogu tymczasowego
echo "--> Pobieram pliki wtyczki do /tmp..."
wget -q "$BASE_URL/plugin.py" -O "$TMP_UPDATE_DIR/plugin.py"
wget -q "$BASE_URL/logo.png" -O "$TMP_UPDATE_DIR/logo.png"
wget -q "$BASE_URL/selection.png" -O "$TMP_UPDATE_DIR/selection.png"
wget -q "$BASE_URL/install_archive_script.sh" -O "$TMP_UPDATE_DIR/install_archive_script.sh"
wget -q "$BASE_URL/update_satellites_xml.sh" -O "$TMP_UPDATE_DIR/update_satellites_xml.sh"
wget -q "$BASE_URL/reload_bouquets.sh" -O "$TMP_UPDATE_DIR/reload_bouquets.sh"
wget -q "$BASE_URL/Kod_QR_buycoffee.png" -O "$TMP_UPDATE_DIR/Kod_QR_buycoffee.png"

# Sprawdź, czy pobrano kluczowy plik plugin.py
if [ ! -f "$TMP_UPDATE_DIR/plugin.py" ]; then
    echo "!!! BŁĄD: Nie udało się pobrać pliku plugin.py. Prerywam instalację."
    rm -rf "$TMP_UPDATE_DIR"
    exit 1
fi

# Usuń starą wersję wtyczki (jeśli istnieje) tuż przed przeniesieniem nowej
echo "--> Usuwam starą wersję wtyczki (jeśli istnieje)..."
if [ -d "$PLUGIN_DIR" ]; then
    rm -rf "$PLUGIN_DIR"
fi

# Utwórz docelowy katalog i przenieś do niego pobrane pliki
echo "--> Instaluję nową wersję..."
mkdir -p "$(dirname "$PLUGIN_DIR")" # Upewnij się, że Extensions istnieje
mv "$TMP_UPDATE_DIR" "$PLUGIN_DIR"

# Ustaw uprawnienia (już na plikach w docelowej lokalizacji)
echo "--> Ustawiam uprawnienia do wykonania dla skryptów .sh..."
chmod +x "$PLUGIN_DIR"/*.sh

# Usuń katalog tymczasowy (już niepotrzebny)
rm -rf "$TMP_UPDATE_DIR"

echo ">>> Instalacja PanelAIO zakończona pomyślnie!"
echo ">>> Proszę ZAMKNĄĆ to okno i RĘCZNIE zrestartować Enigma2 (GUI), aby zmiany były widoczne."

exit 0
