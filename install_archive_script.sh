#!/bin/sh
set -e # Zakończ skrypt, jeśli którekolwiek polecenie zwróci błąd

echo "--- START install_archive_script.sh ---" # Dodany log
echo "Argumenty: \$1='$1' \$2='$2' \$3='$3'" # Dodany log

DOWNLOADED_FILE_PATH="$1"
ARCHIVE_TYPE="$2"
ERROR_MSG="$3"

TMP_EXTRACT_DIR="/tmp/list_extract_tmp"

echo "DEBUG: Tworzę/czyszczę katalog tymczasowy: $TMP_EXTRACT_DIR (25%)..."
rm -rf "$TMP_EXTRACT_DIR" && mkdir -p "$TMP_EXTRACT_DIR" || { echo "KRYTYCZNY BŁĄD: Nie udało się utworzyć $TMP_EXTRACT_DIR!"; exit 1; }
echo "DEBUG: Katalog tymczasowy gotowy."

if [ "$ARCHIVE_TYPE" = "zip" ]; then
    echo "DEBUG: Rozpakowuję archiwum ZIP: $DOWNLOADED_FILE_PATH do $TMP_EXTRACT_DIR..."
    if ! command -v unzip >/dev/null 2>&1; then
        echo "KRYTYCZNY BŁĄD: Narzędzie 'unzip' nie jest dostępne."
        exit 1
    fi
    unzip -o "$DOWNLOADED_FILE_PATH" -d "$TMP_EXTRACT_DIR" || { echo "KRYTYCZNY BŁĄD: Nie udało się rozpakować ZIP! $ERROR_MSG"; exit 1; }
elif [ "$ARCHIVE_TYPE" = "tar.gz" ]; then
    echo "DEBUG: Rozpakowuję archiwum TAR.GZ: $DOWNLOADED_FILE_PATH do $TMP_EXTRACT_DIR..."
    if ! command -v tar >/dev/null 2>&1; then
        echo "KRYTYCZNY BŁĄD: Narzędzie 'tar' nie jest dostępne."
        exit 1
    fi
    tar -xzf "$DOWNLOADED_FILE_PATH" -C "$TMP_EXTRACT_DIR" || { echo "KRYTYCZNY BŁĄD: Nie udało się rozpakować TAR.GZ! $ERROR_MSG"; exit 1; }
else
    echo "KRYTYCZNY BŁĄD: Nieobsługiwany format archiwum '$ARCHIVE_TYPE'."; exit 1;
fi
echo "DEBUG: Rozpakowywanie zakończone. Zawartość $TMP_EXTRACT_DIR:"
ls -R "$TMP_EXTRACT_DIR" # Dodany log - pokaż co zostało rozpakowane

echo "DEBUG: Wyszukuję pliki list kanałów (50%)..."

SOURCE_ENIGMA2_DIR=""
SOURCE_TUXBOX_DIR=""
MAIN_EXTRACTED_DIR="$TMP_EXTRACT_DIR"

if [ -f "$MAIN_EXTRACTED_DIR/etc/enigma2/lamedb" ]; then
    SOURCE_ENIGMA2_DIR="$MAIN_EXTRACTED_DIR/etc/enigma2"
    echo "DEBUG: Pliki Enigma2 (etc/enigma2/lamedb) znaleziono w: $SOURCE_ENIGMA2_DIR"
elif [ -f "$MAIN_EXTRACTED_DIR/lamedb" ]; then
    SOURCE_ENIGMA2_DIR="$MAIN_EXTRACTED_DIR"
    echo "DEBUG: Pliki Enigma2 (lamedb) znaleziono bezpośrednio w: $SOURCE_ENIGMA2_DIR"
else
    FOUND_LAMEDB_PATH=$(find "$MAIN_EXTRACTED_DIR" -name "lamedb" -type f -print -quit)
    if [ -n "$FOUND_LAMEDB_PATH" ]; then
        SOURCE_ENIGMA2_DIR=$(dirname "$FOUND_LAMEDB_PATH")
        echo "DEBUG: Pliki Enigma2 (lamedb) znaleziono przez find w: $SOURCE_ENIGMA2_DIR"
    else
        echo "KRYTYCZNY BŁĄD: Nie znaleziono 'lamedb' w $MAIN_EXTRACTED_DIR. Anuluję kopiowanie."
        exit 1
    fi
fi

if [ -f "$MAIN_EXTRACTED_DIR/etc/tuxbox/satellites.xml" ]; then
    SOURCE_TUXBOX_DIR="$MAIN_EXTRACTED_DIR/etc/tuxbox"
    echo "DEBUG: Plik satellites.xml (etc/tuxbox/satellites.xml) znaleziono w: $SOURCE_TUXBOX_DIR"
elif [ -f "$MAIN_EXTRACTED_DIR/satellites.xml" ]; then
    SOURCE_TUXBOX_DIR="$MAIN_EXTRACTED_DIR"
    echo "DEBUG: Plik satellites.xml znaleziono bezpośrednio w: $SOURCE_TUXBOX_DIR"
else
    FOUND_SATELLITES_PATH=$(find "$MAIN_EXTRACTED_DIR" -name "satellites.xml" -type f -print -quit)
    if [ -n "$FOUND_SATELLITES_PATH" ]; then
        SOURCE_TUXBOX_DIR=$(dirname "$FOUND_SATELLITES_PATH")
        echo "DEBUG: Plik satellites.xml znaleziono przez find w: $SOURCE_TUXBOX_DIR"
    else
        echo "OSTRZEŻENIE: satellites.xml nie znaleziono. Pomijam kopiowanie tego pliku."
        SOURCE_TUXBOX_DIR=""
    fi
fi

echo "DEBUG: Rozpoczynam kopiowanie plików..."
TARGET_ENIGMA2_DIR="/etc/enigma2"
TARGET_TUXBOX_DIR="/etc/tuxbox"

echo "DEBUG: Kopiowanie lamedb z '$SOURCE_ENIGMA2_DIR/lamedb' do '$TARGET_ENIGMA2_DIR/'..."
cp -f "$SOURCE_ENIGMA2_DIR/lamedb" "$TARGET_ENIGMA2_DIR/" || echo "BŁĄD podczas kopiowania lamedb!"
echo "DEBUG: Kopiowanie lamedb zakończone."

echo "DEBUG: Kopiowanie userbouquet* i bouquets* z '$SOURCE_ENIGMA2_DIR' do '$TARGET_ENIGMA2_DIR/'..."
find "$SOURCE_ENIGMA2_DIR" -maxdepth 1 -type f -name 'userbouquet.*' -print -exec cp -f {} "$TARGET_ENIGMA2_DIR/" \; || echo "OSTRZEŻENIE: Problemy podczas kopiowania userbouquet!"
find "$SOURCE_ENIGMA2_DIR" -maxdepth 1 -type f -name 'bouquets.*' -print -exec cp -f {} "$TARGET_ENIGMA2_DIR/" \; || echo "OSTRZEŻENIE: Problemy podczas kopiowania bouquets!"
echo "DEBUG: Kopiowanie userbouquet* i bouquets* zakończone."

echo "DEBUG: Kopiowanie opcjonalnych plików (blacklist, whitelist, itp.)..."
cp -f "$SOURCE_ENIGMA2_DIR/blacklist" "$TARGET_ENIGMA2_DIR/" >/dev/null 2>&1 || true
cp -f "$SOURCE_ENIGMA2_DIR/whitelist" "$TARGET_ENIGMA2_DIR/" >/dev/null 2>&1 || true
cp -f "$SOURCE_ENIGMA2_DIR/autobouquets.xml" "$TARGET_ENIGMA2_DIR/" >/dev/null 2>&1 || true
echo "DEBUG: Kopiowanie opcjonalnych plików zakończone."

if [ -n "$SOURCE_TUXBOX_DIR" ] && [ -d "$SOURCE_TUXBOX_DIR" ]; then
    echo "DEBUG: Kopiowanie plików Tuxbox (satellites.xml, itp.) z '$SOURCE_TUXBOX_DIR' do '$TARGET_TUXBOX_DIR/'..."
    cp -f "$SOURCE_TUXBOX_DIR/satellites.xml" "$TARGET_TUXBOX_DIR/" || echo "BŁĄD podczas kopiowania satellites.xml!"
    cp -f "$SOURCE_TUXBOX_DIR/terrestrial.xml" "$TARGET_TUXBOX_DIR/" >/dev/null 2>&1 || true
    cp -f "$SOURCE_TUXBOX_DIR/cables.xml" "$TARGET_TUXBOX_DIR/" >/dev/null 2>&1 || true
    cp -f "$SOURCE_TUXBOX_DIR/atsc.xml" "$TARGET_TUXBOX_DIR/" >/dev/null 2>&1 || true
    echo "DEBUG: Kopiowanie plików Tuxbox zakończone."
else
    echo "DEBUG: Katalog źródłowy Tuxbox ($SOURCE_TUXBOX_DIR) nie istnieje lub nie określony. Pomijam."
fi

echo "DEBUG: Kopiowanie plików zakończone. Przeładowuję bukiety (75%)..."
RELOAD_SCRIPT_PATH="$(dirname "$0")/reload_bouquets.sh"
echo "DEBUG: Wyznaczona ścieżka do reload_bouquets.sh: '$RELOAD_SCRIPT_PATH'"

if [ -f "$RELOAD_SCRIPT_PATH" ]; then
    echo "DEBUG: Plik reload_bouquets.sh istnieje w '$RELOAD_SCRIPT_PATH'."
    if [ -x "$RELOAD_SCRIPT_PATH" ]; then
        echo "DEBUG: Próba uruchomienia '$RELOAD_SCRIPT_PATH'..."
        if "$RELOAD_SCRIPT_PATH"; then
            echo "DEBUG: reload_bouquets.sh zakończony pomyślnie (kod wyjścia $?)."
        else
            echo "BŁĄD: Skrypt reload_bouquets.sh zwrócił błąd (kod wyjścia $?) podczas wykonywania!"
        fi
    else
        echo "KRYTYCZNY BŁĄD: Skrypt reload_bouquets.sh '$RELOAD_SCRIPT_PATH' nie ma uprawnień do wykonywania!"
        echo "Nadaj uprawnienia: chmod +x '$RELOAD_SCRIPT_PATH'"
    fi
else
    echo "KRYTYCZNY BŁĄD: Skrypt reload_bouquets.sh '$RELOAD_SCRIPT_PATH' nie został znaleziony!"
fi

echo "DEBUG: Usuwam pliki tymczasowe (90%)..."
rm -rf "$TMP_EXTRACT_DIR"
rm -f "$DOWNLOADED_FILE_PATH"
echo "DEBUG: Pliki tymczasowe usunięte."

echo "--- KONIEC install_archive_script.sh ---" # Dodany log
echo "Instalacja listy kanałów zakończona. Zalecany restart GUI, jeśli listy nie są widoczne!"
exit 0
