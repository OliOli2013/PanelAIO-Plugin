#!/bin/sh
# Skrypt instalacyjny dla wtyczki PanelAIO (v6 - precyzyjniejsze instrukcje)

# --- Konfiguracja ---
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/PanelAIO"
TMP_UPDATE_DIR="/tmp/PanelAIO_Update"
BASE_URL="https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main"
LOG_FILE="/tmp/PanelAIO_Update.log"

# --- Funkcja wykonująca aktualizację w tle ---
do_background_update() {
    echo ">>> Rozpoczynam aktualizację PanelAIO w tle (log: $LOG_FILE)..." > "$LOG_FILE"
    date >> "$LOG_FILE"

    # Utwórz czysty katalog tymczasowy
    echo "--> Przygotowuję katalog tymczasowy..." >> "$LOG_FILE"
    rm -rf "$TMP_UPDATE_DIR" >> "$LOG_FILE" 2>&1
    mkdir -p "$TMP_UPDATE_DIR" >> "$LOG_FILE" 2>&1

    # Pobierz wszystkie niezbędne pliki do katalogu tymczasowego
    echo "--> Pobieram pliki wtyczki do /tmp..." >> "$LOG_FILE"
    wget -q "$BASE_URL/plugin.py" -O "$TMP_UPDATE_DIR/plugin.py" >> "$LOG_FILE" 2>&1
    wget -q "$BASE_URL/logo.png" -O "$TMP_UPDATE_DIR/logo.png" >> "$LOG_FILE" 2>&1
    wget -q "$BASE_URL/selection.png" -O "$TMP_UPDATE_DIR/selection.png" >> "$LOG_FILE" 2>&1
    wget -q "$BASE_URL/install_archive_script.sh" -O "$TMP_UPDATE_DIR/install_archive_script.sh" >> "$LOG_FILE" 2>&1
    wget -q "$BASE_URL/update_satellites_xml.sh" -O "$TMP_UPDATE_DIR/update_satellites_xml.sh" >> "$LOG_FILE" 2>&1
    wget -q "$BASE_URL/reload_bouquets.sh" -O "$TMP_UPDATE_DIR/reload_bouquets.sh" >> "$LOG_FILE" 2>&1
    wget -q "$BASE_URL/Kod_QR_buycoffee.png" -O "$TMP_UPDATE_DIR/Kod_QR_buycoffee.png" >> "$LOG_FILE" 2>&1

    # Sprawdź, czy pobrano kluczowy plik plugin.py
    if [ ! -f "$TMP_UPDATE_DIR/plugin.py" ]; then
        echo "!!! BŁĄD: Nie udało się pobrać pliku plugin.py. Prerywam instalację." >> "$LOG_FILE"
        rm -rf "$TMP_UPDATE_DIR" >> "$LOG_FILE" 2>&1
        exit 1
    fi

    # Usuń starą wersję wtyczki (jeśli istnieje) tuż przed przeniesieniem nowej
    echo "--> Usuwam starą wersję wtyczki (jeśli istnieje)..." >> "$LOG_FILE"
    if [ -d "$PLUGIN_DIR" ]; then
        rm -rf "$PLUGIN_DIR" >> "$LOG_FILE" 2>&1
    fi

    # Utwórz docelowy katalog i przenieś do niego pobrane pliki
    echo "--> Instaluję nową wersję..." >> "$LOG_FILE"
    mkdir -p "$(dirname "$PLUGIN_DIR")" >> "$LOG_FILE" 2>&1 # Upewnij się, że Extensions istnieje
    mv "$TMP_UPDATE_DIR" "$PLUGIN_DIR" >> "$LOG_FILE" 2>&1

    # Ustaw uprawnienia (już na plikach w docelowej lokalizacji)
    echo "--> Ustawiam uprawnienia do wykonania dla skryptów .sh..." >> "$LOG_FILE"
    chmod +x "$PLUGIN_DIR"/*.sh >> "$LOG_FILE" 2>&1

    # Dodaj krótką pauzę, aby upewnić się, że operacje na plikach się zakończyły
    sleep 3

    # Usuń katalog tymczasowy (już niepotrzebny)
    rm -rf "$TMP_UPDATE_DIR" >> "$LOG_FILE" 2>&1

    echo ">>> Aktualizacja PanelAIO w tle ZAKOŃCZONA." >> "$LOG_FILE"
    date >> "$LOG_FILE"
    echo ">>> Można teraz RĘCZNIE zrestartować Enigma2 (GUI)." >> "$LOG_FILE"
    exit 0
}

# --- Główna logika skryptu ---
# Uruchom funkcję aktualizacji w tle
echo ">>> Uruchamiam aktualizację PanelAIO w tle..."
( do_background_update ) & # Kluczowe: uruchomienie w subshellu (&) w tle

# Wyświetl instrukcje dla użytkownika i zakończ
echo "-----------------------------------------------------"
echo ">>> Aktualizacja została uruchomiona w tle."
echo ">>> Proces trwa od kilkunastu sekund do minuty."
echo ">>> Po tym czasie można bezpiecznie zrestartować GUI."
echo ""
echo ">>> Możesz sprawdzić plik logu, aby upewnić się,"
echo ">>> że aktualizacja się zakończyła:"
echo ">>> $LOG_FILE"
echo ""
echo ">>> Zrestartuj Enigma2 (GUI),"
echo ">>> aby zmiany zaczęły obowiązywać."
echo "-----------------------------------------------------"

# Zakończ skrypt wywołany przez Console natychmiast
exit 0
