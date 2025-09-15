#!/bin/sh
# Skrypt do instalacji archiwum (zip lub tar.gz)

ARCHIVE_PATH="$1"
ARCHIVE_TYPE="$2"
EXTRACT_DIR="/tmp/list_extract_tmp"

echo "--- START install_archive_script.sh ---"
echo "Argumenty: \$1='$1' \$2='$2' \$3='$3'"

if [ ! -f "$ARCHIVE_PATH" ]; then
    echo "KRYTYCZNY BŁĄD: Plik archiwum nie istnieje: $ARCHIVE_PATH"
    exit 1
fi

echo "DEBUG: Tworzę/czyszczę katalog tymczasowy ($EXTRACT_DIR)..."
rm -rf "$EXTRACT_DIR"
mkdir -p "$EXTRACT_DIR"
echo "DEBUG: Katalog tymczasowy gotowy."

if [ "$ARCHIVE_TYPE" = "zip" ]; then
    echo "DEBUG: Rozpakowuję archiwum ZIP: $ARCHIVE_PATH do $EXTRACT_DIR..."
    unzip -o "$ARCHIVE_PATH" -d "$EXTRACT_DIR"
    if [ $? -ne 0 ]; then
        echo "KRYTYCZNY BŁĄD: Nie udało się rozpakować ZIP!"
        exit 1
    fi
else
    echo "DEBUG: Rozpakowuję archiwum TAR.GZ: $ARCHIVE_PATH do $EXTRACT_DIR..."
    tar -xzf "$ARCHIVE_PATH" -C "$EXTRACT_DIR"
    if [ $? -ne 0 ]; then
        echo "KRYTYCZNY BŁĄD: Nie udało się rozpakować TAR.GZ!"
        exit 1
    fi
fi

echo "DEBUG: Kopiuję pliki na swoje miejsca..."
cp -rf "$EXTRACT_DIR"/* /

echo "DEBUG: Czyszczę po sobie..."
rm -rf "$EXTRACT_DIR"
rm -f "$ARCHIVE_PATH"

echo "--- KONIEC install_archive_script.sh ---"
exit 0
