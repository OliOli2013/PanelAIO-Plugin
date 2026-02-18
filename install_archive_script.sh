#!/bin/sh
# Skrypt install_archive_script.sh (v9.0) - Zgodny z AIO Panel v5.0
# Logika: Rozpakuj -> Znajdź lamedb -> Kopiuj -> (Restart robi plugin.py)

# LOG_FILE dla debugowania
LOG_FILE="/tmp/aio_install.log"

# Start logging
echo "--- START install_archive_script.sh (v9.0) ---" > "$LOG_FILE"
echo "Argumenty: \$1='$1' \$2='$2'" >> "$LOG_FILE"
date >> "$LOG_FILE"

DOWNLOADED_FILE_PATH="$1"
ARCHIVE_TYPE="$2"

TMP_EXTRACT_DIR="/tmp/list_extract_tmp"

echo "--> Przygotowuję katalog tymczasowy: $TMP_EXTRACT_DIR ..." | tee -a "$LOG_FILE"
rm -rf "$TMP_EXTRACT_DIR" && mkdir -p "$TMP_EXTRACT_DIR"
if [ $? -ne 0 ]; then
    echo "!!! KRYTYCZNY BŁĄD: Nie udało się utworzyć $TMP_EXTRACT_DIR!" | tee -a "$LOG_FILE"
    exit 1
fi
echo "--> Katalog tymczasowy gotowy." >> "$LOG_FILE"

# Rozpakowywanie
EXIT_CODE=1
echo "--> Rozpakowuję archiwum ($ARCHIVE_TYPE)..." | tee -a "$LOG_FILE"
if [ "$ARCHIVE_TYPE" = "zip" ]; then
    if ! command -v unzip >/dev/null 2>&1; then
        echo "!!! KRYTYCZNY BŁĄD: Narzędzie 'unzip' nie jest dostępne." | tee -a "$LOG_FILE"
        exit 1
    fi
    unzip -o "$DOWNLOADED_FILE_PATH" -d "$TMP_EXTRACT_DIR" >> "$LOG_FILE" 2>&1
    EXIT_CODE=$?
elif [ "$ARCHIVE_TYPE" = "tar.gz" ]; then
    if ! command -v tar >/dev/null 2>&1; then
        echo "!!! KRYTYCZNY BŁĄD: Narzędzie 'tar' nie jest dostępne." | tee -a "$LOG_FILE"
        exit 1
    fi
    tar -xzf "$DOWNLOADED_FILE_PATH" -C "$TMP_EXTRACT_DIR" >> "$LOG_FILE" 2>&1
    EXIT_CODE=$?
else
    echo "!!! KRYTYCZNY BŁĄD: Nieobsługiwany format archiwum '$ARCHIVE_TYPE'." | tee -a "$LOG_FILE"
    rm -f "$DOWNLOADED_FILE_PATH" # Cleanup downloaded file on error
    exit 1
fi

if [ $EXIT_CODE -ne 0 ]; then
    echo "!!! BŁĄD PODCZAS ROZPAKOWYWANIA (kod: $EXIT_CODE)! Sprawdź $LOG_FILE. Przerywam." | tee -a "$LOG_FILE"
    rm -f "$DOWNLOADED_FILE_PATH" # Cleanup
    rm -rf "$TMP_EXTRACT_DIR"
    exit 1
fi
echo "--> Rozpakowywanie zakończone. Zawartość $TMP_EXTRACT_DIR:" >> "$LOG_FILE"
ls -R "$TMP_EXTRACT_DIR" >> "$LOG_FILE" 2>&1

# --- Wyszukiwanie katalogu z lamedb ---
echo "--> Wyszukuję katalog z plikiem 'lamedb'..." >> "$LOG_FILE"
SOURCE_DIR=""
FOUND_LAMEDB_PATH=$(find "$TMP_EXTRACT_DIR" -name "lamedb" -type f -print -quit)

if [ -n "$FOUND_LAMEDB_PATH" ]; then
    SOURCE_DIR=$(dirname "$FOUND_LAMEDB_PATH")
    echo "--> Znaleziono główny katalog z listą kanałów: $SOURCE_DIR" | tee -a "$LOG_FILE"
else
    echo "!!! KRYTYCZNY BŁĄD: Nie znaleziono pliku 'lamedb' w rozpakowanym archiwum. Anuluję." | tee -a "$LOG_FILE"
    rm -f "$DOWNLOADED_FILE_PATH" # Cleanup
    rm -rf "$TMP_EXTRACT_DIR"
    exit 1
fi
# --- Koniec wyszukiwania ---

# --- Kopiowanie Plików (nadpisywanie) ---
echo "--> Rozpoczynam kopiowanie plików (nadpisywanie)..." | tee -a "$LOG_FILE"
TARGET_ENIGMA2_DIR="/etc/enigma2"
TARGET_TUXBOX_DIR="/etc/tuxbox"
COPY_ERRORS=0

# Kopiowanie wszystkich plików z znalezionego katalogu źródłowego do /etc/enigma2
echo "--> Kopiowanie z '$SOURCE_DIR' do '$TARGET_ENIGMA2_DIR/'..." >> "$LOG_FILE"
cp -rf "$SOURCE_DIR"/* "$TARGET_ENIGMA2_DIR/" 2>> "$LOG_FILE" || { echo "!!! OSTRZEŻENIE: Wystąpiły problemy podczas kopiowania plików do $TARGET_ENIGMA2_DIR (szczegóły w $LOG_FILE)"; COPY_ERRORS=1; }

# Kopiowanie satellites.xml, jeśli istnieje
if [ -f "$SOURCE_DIR/satellites.xml" ]; then
    echo "--> Kopiowanie satellites.xml do '$TARGET_TUXBOX_DIR/'..." >> "$LOG_FILE"
    # Upewnij się, że katalog /etc/tuxbox istnieje
    mkdir -p "$TARGET_TUXBOX_DIR" >> "$LOG_FILE" 2>&1
    cp -f "$SOURCE_DIR/satellites.xml" "$TARGET_TUXBOX_DIR/" 2>> "$LOG_FILE" || { echo "!!! OSTRZEŻENIE: Nie udało się skopiować satellites.xml (szczegóły w $LOG_FILE)"; COPY_ERRORS=1; }
fi
echo "--> Kopiowanie plików zakończone." >> "$LOG_FILE"
# --- Koniec Kopiowania ---

# --- Czyszczenie ---
echo "--> Usuwam pliki tymczasowe..." | tee -a "$LOG_FILE"
rm -rf "$TMP_EXTRACT_DIR" >> "$LOG_FILE" 2>&1
rm -f "$DOWNLOADED_FILE_PATH" >> "$LOG_FILE" 2>&1
echo "--> Pliki tymczasowe usunięte." >> "$LOG_FILE"
# --- Koniec Czyszczenia ---

# --- Komunikat końcowy ---
echo "--- KONIEC install_archive_script.sh (v9.0) ---" >> "$LOG_FILE"
if [ $COPY_ERRORS -ne 0 ]; then
    echo ">>> Instalacja ZAKOŃCZONA Z OSTRZEŻENIAMI." | tee -a "$LOG_FILE"
    echo ">>> Sprawdź listę kanałów. W razie problemów może być konieczny restart GUI." | tee -a "$LOG_FILE"
    echo ">>> Szczegółowe logi znajdziesz w pliku: $LOG_FILE" | tee -a "$LOG_FILE"
else
    echo ">>> Instalacja listy kanałów ZAKOŃCZONA pomyślnie." | tee -a "$LOG_FILE"
    echo ">>> Restart/Przeładowanie list zostanie wykonane przez plugin.py" | tee -a "$LOG_FILE"
fi
sleep 1 # Krótka pauza

exit 0
