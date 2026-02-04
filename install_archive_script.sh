#!/bin/sh
# Skrypt install_archive_script.sh (v7.0) - Zgodny z AIO Panel v7.0
# Logika: Rozpakuj -> Znajdź lamedb -> Kopiuj z naprawą uprawnień -> (Restart robi plugin.py)

# LOG_FILE dla debugowania
LOG_FILE="/tmp/aio_install.log"

# Start logging
echo "--- START install_archive_script.sh (v7.0) ---" > "$LOG_FILE"
echo "Argumenty: FILE='$1' TYPE='$2'" >> "$LOG_FILE"
date >> "$LOG_FILE"

DOWNLOADED_FILE_PATH="$1"
ARCHIVE_TYPE="$2"

TMP_EXTRACT_DIR="/tmp/list_extract_tmp"

# 1. Przygotowanie środowiska
echo "--> Przygotowuję katalog tymczasowy: $TMP_EXTRACT_DIR ..." | tee -a "$LOG_FILE"
rm -rf "$TMP_EXTRACT_DIR"
mkdir -p "$TMP_EXTRACT_DIR"

if [ ! -d "$TMP_EXTRACT_DIR" ]; then
    echo "!!! KRYTYCZNY BŁĄD: Nie udało się utworzyć $TMP_EXTRACT_DIR!" | tee -a "$LOG_FILE"
    exit 1
fi
echo "--> Katalog tymczasowy gotowy." >> "$LOG_FILE"

# 2. Rozpakowywanie
EXIT_CODE=1
echo "--> Rozpakowuję archiwum ($ARCHIVE_TYPE)..." | tee -a "$LOG_FILE"

if [ "$ARCHIVE_TYPE" = "zip" ]; then
    if ! command -v unzip >/dev/null 2>&1; then
        echo "!!! KRYTYCZNY BŁĄD: Brak narzędzia 'unzip' w systemie." | tee -a "$LOG_FILE"
        exit 1
    fi
    unzip -o "$DOWNLOADED_FILE_PATH" -d "$TMP_EXTRACT_DIR" >> "$LOG_FILE" 2>&1
    EXIT_CODE=$?
elif [ "$ARCHIVE_TYPE" = "tar.gz" ] || [ "$ARCHIVE_TYPE" = "tgz" ]; then
    if ! command -v tar >/dev/null 2>&1; then
        echo "!!! KRYTYCZNY BŁĄD: Brak narzędzia 'tar' w systemie." | tee -a "$LOG_FILE"
        exit 1
    fi
    tar -xzf "$DOWNLOADED_FILE_PATH" -C "$TMP_EXTRACT_DIR" >> "$LOG_FILE" 2>&1
    EXIT_CODE=$?
else
    echo "!!! KRYTYCZNY BŁĄD: Nieobsługiwany format archiwum '$ARCHIVE_TYPE'." | tee -a "$LOG_FILE"
    rm -f "$DOWNLOADED_FILE_PATH"
    exit 1
fi

if [ $EXIT_CODE -ne 0 ]; then
    echo "!!! BŁĄD PODCZAS ROZPAKOWYWANIA (kod: $EXIT_CODE)! Sprawdź $LOG_FILE." | tee -a "$LOG_FILE"
    rm -f "$DOWNLOADED_FILE_PATH"
    rm -rf "$TMP_EXTRACT_DIR"
    exit 1
fi

echo "--> Rozpakowywanie zakończone." >> "$LOG_FILE"

# 3. Wyszukiwanie katalogu z lamedb (Inteligentne wykrywanie struktury)
echo "--> Wyszukuję strukturę katalogów (szukam pliku 'lamedb')..." >> "$LOG_FILE"
SOURCE_DIR=""
# Znajdź pierwszy plik lamedb i pobierz jego katalog
FOUND_LAMEDB_PATH=$(find "$TMP_EXTRACT_DIR" -name "lamedb" -type f -print -quit)

if [ -n "$FOUND_LAMEDB_PATH" ]; then
    SOURCE_DIR=$(dirname "$FOUND_LAMEDB_PATH")
    echo "--> ZIDENTYFIKOWANO KATALOG ŹRÓDŁOWY: $SOURCE_DIR" | tee -a "$LOG_FILE"
else
    echo "!!! KRYTYCZNY BŁĄD: Nie znaleziono pliku 'lamedb' w archiwum. To nie jest poprawna lista kanałów E2." | tee -a "$LOG_FILE"
    rm -f "$DOWNLOADED_FILE_PATH"
    rm -rf "$TMP_EXTRACT_DIR"
    exit 1
fi

# 4. Kopiowanie Plików
echo "--> Rozpoczynam instalację plików..." | tee -a "$LOG_FILE"
TARGET_ENIGMA2_DIR="/etc/enigma2"
TARGET_TUXBOX_DIR="/etc/tuxbox"
COPY_ERRORS=0

# Sprawdzenie czy katalogi docelowe istnieją
if [ ! -d "$TARGET_ENIGMA2_DIR" ]; then
    mkdir -p "$TARGET_ENIGMA2_DIR"
fi

# Kopiowanie zawartości katalogu z lamedb do /etc/enigma2
echo "--> Kopiowanie z '$SOURCE_DIR' do '$TARGET_ENIGMA2_DIR/'..." >> "$LOG_FILE"
cp -rf "$SOURCE_DIR"/* "$TARGET_ENIGMA2_DIR/" 2>> "$LOG_FILE" || { 
    echo "!!! BŁĄD COPY: Problem z kopiowaniem do $TARGET_ENIGMA2_DIR"; 
    COPY_ERRORS=1; 
}

# Naprawa uprawnień (Fix Permissions) - WAŻNE w v7.0
echo "--> Naprawiam uprawnienia plików w $TARGET_ENIGMA2_DIR..." >> "$LOG_FILE"
# Ustawia 644 dla plików .tv, .radio, .dat i lamedb, aby system mógł je nadpisać
chmod 644 "$TARGET_ENIGMA2_DIR"/userbouquet.* 2>/dev/null
chmod 644 "$TARGET_ENIGMA2_DIR"/lamedb 2>/dev/null
chmod 644 "$TARGET_ENIGMA2_DIR"/blacklist 2>/dev/null
chmod 644 "$TARGET_ENIGMA2_DIR"/whitelist 2>/dev/null

# 5. Obsługa satellites.xml
if [ -f "$SOURCE_DIR/satellites.xml" ]; then
    echo "--> Znaleziono satellites.xml. Kopiowanie do '$TARGET_TUXBOX_DIR/'..." >> "$LOG_FILE"
    mkdir -p "$TARGET_TUXBOX_DIR"
    cp -f "$SOURCE_DIR/satellites.xml" "$TARGET_TUXBOX_DIR/" 2>> "$LOG_FILE"
    chmod 644 "$TARGET_TUXBOX_DIR/satellites.xml"
else
    echo "--> Brak pliku satellites.xml w katalogu z listą (to normalne dla niektórych paczek)." >> "$LOG_FILE"
fi

# 6. Czyszczenie
echo "--> Sprzątanie po instalacji..." | tee -a "$LOG_FILE"
rm -rf "$TMP_EXTRACT_DIR"
rm -f "$DOWNLOADED_FILE_PATH"

# 7. Raport końcowy
echo "--- KONIEC install_archive_script.sh (v7.0) ---" >> "$LOG_FILE"

if [ $COPY_ERRORS -ne 0 ]; then
    echo ">>> Instalacja ZAKOŃCZONA Z BŁĘDAMI KOPIOWANIA." | tee -a "$LOG_FILE"
    echo ">>> Sprawdź log: $LOG_FILE" | tee -a "$LOG_FILE"
    exit 1
else
    echo ">>> Instalacja listy kanałów ZAKOŃCZONA POMYŚLNIE." | tee -a "$LOG_FILE"
    echo ">>> Oczekiwanie na przeładowanie listy przez wtyczkę..." | tee -a "$LOG_FILE"
    exit 0
fi
