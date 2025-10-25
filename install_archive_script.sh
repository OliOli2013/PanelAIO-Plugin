#!/bin/sh
set -e # Zakończ skrypt, jeśli którekolwiek polecenie zwróci błąd

echo "--- START install_archive_script.sh ---"
echo "Argumenty: \$1='$1' \$2='$2' \$3='$3'"

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
ls -R "$TMP_EXTRACT_DIR"

echo "DEBUG: Wyszukuję pliki list kanałów (50%)..."

# --- NOWA, POPRAWIONA LOGIKA WYSZUKIWANIA PLIKÓW ---
SOURCE_DIR=""
FOUND_LAMEDB_PATH=$(find "$TMP_EXTRACT_DIR" -name "lamedb" -type f -print -quit)

if [ -n "$FOUND_LAMEDB_PATH" ]; then
    SOURCE_DIR=$(dirname "$FOUND_LAMEDB_PATH")
    echo "DEBUG: Znaleziono główny katalog z listą kanałów: $SOURCE_DIR"
else
    echo "KRYTYCZNY BŁĄD: Nie znaleziono pliku 'lamedb' w rozpakowanym archiwum. Anuluję."
    exit 1
fi
# --- KONIEC NOWEJ LOGIKI ---

echo "DEBUG: Rozpoczynam kopiowanie plików..."
TARGET_ENIGMA2_DIR="/etc/enigma2"
TARGET_TUXBOX_DIR="/etc/tuxbox"

# Kopiowanie wszystkich plików z znalezionego katalogu źródłowego
echo "DEBUG: Kopiowanie plików z '$SOURCE_DIR' do '$TARGET_ENIGMA2_DIR/' oraz '$TARGET_TUXBOX_DIR/'..."
cp -rf "$SOURCE_DIR"/* "$TARGET_ENIGMA2_DIR/" || echo "OSTRZEŻENIE: Wystąpiły problemy podczas kopiowania plików do $TARGET_ENIGMA2_DIR"

# Plik satellites.xml ma swoje specjalne miejsce
if [ -f "$SOURCE_DIR/satellites.xml" ]; then
    cp -f "$SOURCE_DIR/satellites.xml" "$TARGET_TUXBOX_DIR/" || echo "OSTRZEŻENIE: Nie udało się skopiować satellites.xml"
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

echo "--- KONIEC install_archive_script.sh ---"
echo "Instalacja listy kanałów zakończona. Zalecany restart GUI, jeśli listy nie są widoczne!"
exit 0
