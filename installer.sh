#!/bin/sh
# Skrypt instalacyjny dla wtyczki PanelAIO (v7.0)
# Zgodny z migracją do SystemPlugins

# --- Konfiguracja ---
# NOWA ŚCIEŻKA (SystemPlugins) - zgodnie z Changelog v7.0
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO"
# STARA ŚCIEŻKA (do usunięcia przy migracji)
OLD_PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/PanelAIO"

TMP_UPDATE_DIR="/tmp/PanelAIO_Update"
BASE_URL="https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main"
LOG_FILE="/tmp/PanelAIO_Update.log"

# --- Funkcja wykonująca aktualizację w tle ---
do_background_update() {
    echo ">>> Rozpoczynam aktualizację PanelAIO v7.0 w tle (log: $LOG_FILE)..." > "$LOG_FILE"
    date >> "$LOG_FILE"

    # 1. Przygotowanie katalogu tymczasowego
    echo "--> Przygotowuję katalog tymczasowy..." >> "$LOG_FILE"
    rm -rf "$TMP_UPDATE_DIR"
    mkdir -p "$TMP_UPDATE_DIR"

    # 2. Pobieranie plików
    echo "--> Pobieram pliki wtyczki do /tmp..." >> "$LOG_FILE"
    
    # Lista plików do pobrania
    wget -q "$BASE_URL/plugin.py" -O "$TMP_UPDATE_DIR/plugin.py" >> "$LOG_FILE" 2>&1
    wget -q "$BASE_URL/__init__.py" -O "$TMP_UPDATE_DIR/__init__.py" >> "$LOG_FILE" 2>&1
    wget -q "$BASE_URL/logo.png" -O "$TMP_UPDATE_DIR/logo.png" >> "$LOG_FILE" 2>&1
    wget -q "$BASE_URL/selection.png" -O "$TMP_UPDATE_DIR/selection.png" >> "$LOG_FILE" 2>&1
    wget -q "$BASE_URL/install_archive_script.sh" -O "$TMP_UPDATE_DIR/install_archive_script.sh" >> "$LOG_FILE" 2>&1
    wget -q "$BASE_URL/update_satellites_xml.sh" -O "$TMP_UPDATE_DIR/update_satellites_xml.sh" >> "$LOG_FILE" 2>&1
    wget -q "$BASE_URL/Kod_QR_buycoffee.png" -O "$TMP_UPDATE_DIR/Kod_QR_buycoffee.png" >> "$LOG_FILE" 2>&1

    # Weryfikacja pobrania kluczowego pliku
    if [ ! -f "$TMP_UPDATE_DIR/plugin.py" ]; then
        echo "!!! BŁĄD: Nie udało się pobrać pliku plugin.py. Sprawdź łącze internetowe lub URL. Przerywam." >> "$LOG_FILE"
        rm -rf "$TMP_UPDATE_DIR"
        exit 1
    fi

    # Zabezpieczenie dla SystemPlugins: Jeśli __init__.py nie istnieje na serwerze, stwórz pusty.
    # Jest to wymagane, aby Enigma2 widziała wtyczkę w SystemPlugins.
    if [ ! -f "$TMP_UPDATE_DIR/__init__.py" ]; then
        echo "--> Tworzę brakujący __init__.py (wymagany dla SystemPlugins)..." >> "$LOG_FILE"
        touch "$TMP_UPDATE_DIR/__init__.py"
    fi

    # 3. Czyszczenie starej wersji (MIGRACJA)
    echo "--> Sprzątanie starych wersji..." >> "$LOG_FILE"
    
    # Usuń starą wersję z Extensions (jeśli użytkownik miał v5.0 lub starszą)
    if [ -d "$OLD_PLUGIN_DIR" ]; then
        echo "--> Wykryto starą wersję w Extensions. Usuwanie..." >> "$LOG_FILE"
        rm -rf "$OLD_PLUGIN_DIR" >> "$LOG_FILE" 2>&1
    fi

    # Usuń obecną wersję z SystemPlugins (przy reinstalacji)
    if [ -d "$PLUGIN_DIR" ]; then
        rm -rf "$PLUGIN_DIR" >> "$LOG_FILE" 2>&1
    fi

    # 4. Instalacja nowej wersji
    echo "--> Instaluję nową wersję do SystemPlugins..." >> "$LOG_FILE"
    # Upewnij się, że katalog nadrzędny istnieje
    mkdir -p "$(dirname "$PLUGIN_DIR")"
    
    # Przenieś pliki
    mv "$TMP_UPDATE_DIR" "$PLUGIN_DIR" >> "$LOG_FILE" 2>&1

    # 5. Uprawnienia
    echo "--> Ustawiam uprawnienia..." >> "$LOG_FILE"
    # Skrypty shell muszą być wykonywalne
    chmod +x "$PLUGIN_DIR"/*.sh >> "$LOG_FILE" 2>&1
    # Pliki python i grafiki standardowo 644
    chmod 644 "$PLUGIN_DIR"/*.py "$PLUGIN_DIR"/*.png >> "$LOG_FILE" 2>&1

    # Krótka pauza na synchronizację systemu plików
    sleep 2

    # 6. Czyszczenie końcowe
    rm -rf "$TMP_UPDATE_DIR" >> "$LOG_FILE" 2>&1

    echo ">>> Aktualizacja PanelAIO v7.0 ZAKOŃCZONA." >> "$LOG_FILE"
    date >> "$LOG_FILE"
    echo ">>> WYMAGANY RESTART GUI (Enigma2) ABY ZOBACZYĆ ZMIANY." >> "$LOG_FILE"
    exit 0
}

# --- Główna logika skryptu ---
echo ">>> Uruchamiam instalator PanelAIO v7.0..."
# Uruchomienie w tle
( do_background_update ) &

# Komunikaty dla użytkownika w terminalu
echo "-----------------------------------------------------"
echo ">>> Rozpoczęto instalację/aktualizację w tle."
echo ">>> Wersja docelowa: 7.0 (SystemPlugins)"
echo ">>> Log operacji: $LOG_FILE"
echo ""
echo ">>> Po odczekaniu ok. 30 sekund wykonaj restart GUI,"
echo ">>> aby wtyczka pojawiła się w menu."
echo "-----------------------------------------------------"

exit 0
