#!/bin/sh
# AIO Panel - self-contained GitHub installer
# Keeps the public one-liner compatible with fresh install and update.

set -u

REPO="OliOli2013/PanelAIO-Plugin"
BRANCH="main"
PKG_DEFAULT="enigma2-plugin-extensions-panelaio"
META_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}/update.json"
TMP_DIR="/tmp/PanelAIO-installer-$$"
META_FILE="$TMP_DIR/update.json"
IPK_FILE="$TMP_DIR/panelaio.ipk"
LOG_FILE="/tmp/panelaio_installer.log"

log() {
    printf '%s\n' "[PanelAIO] $*" | tee -a "$LOG_FILE"
}

cleanup() {
    rm -rf "$TMP_DIR" 2>/dev/null || true
}

fail() {
    log "ERROR: $*"
    cleanup
    exit 1
}

trap 'cleanup' EXIT HUP INT TERM
: > "$LOG_FILE" 2>/dev/null || true
mkdir -p "$TMP_DIR" || fail "Nie można utworzyć katalogu tymczasowego."

command -v wget >/dev/null 2>&1 || fail "Brak polecenia wget."
command -v opkg >/dev/null 2>&1 || fail "Brak menedżera pakietów opkg."

CACHE_BUSTER=$(date +%s 2>/dev/null || echo $$)
log "Pobieranie informacji o aktualnej wersji..."
if ! wget -q -O "$META_FILE" "${META_URL}?${CACHE_BUSTER}"; then
    wget -q --no-check-certificate -O "$META_FILE" "${META_URL}?${CACHE_BUSTER}" \
        || fail "Nie można pobrać update.json z GitHuba."
fi

[ -s "$META_FILE" ] || fail "Pobrany update.json jest pusty."

IPK_URL=$(sed -n 's/^[[:space:]]*"url"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$META_FILE" | head -n 1)
EXPECTED_SHA=$(sed -n 's/^[[:space:]]*"sha256"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$META_FILE" | head -n 1)
VERSION=$(sed -n 's/^[[:space:]]*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$META_FILE" | head -n 1)
PACKAGE=$(sed -n 's/^[[:space:]]*"package"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$META_FILE" | head -n 1)

[ -n "$IPK_URL" ] || fail "Brak adresu IPK w update.json."
[ -n "$PACKAGE" ] || PACKAGE="$PKG_DEFAULT"
[ -n "$VERSION" ] || VERSION="nieznana"

log "Pobieranie AIO Panel ${VERSION}..."
if ! wget -q -O "$IPK_FILE" "${IPK_URL}?${CACHE_BUSTER}"; then
    wget -q --no-check-certificate -O "$IPK_FILE" "${IPK_URL}?${CACHE_BUSTER}" \
        || fail "Nie można pobrać pakietu IPK."
fi

[ -s "$IPK_FILE" ] || fail "Pobrany pakiet IPK jest pusty."

FILE_SIZE=$(wc -c < "$IPK_FILE" 2>/dev/null || echo 0)
[ "$FILE_SIZE" -gt 1024 ] || fail "Pobrany plik jest zbyt mały i prawdopodobnie nie jest pakietem IPK."

# Odrzuć typową odpowiedź HTML zamiast pakietu.
if head -c 256 "$IPK_FILE" 2>/dev/null | grep -qiE '<!doctype html|<html'; then
    fail "GitHub zwrócił stronę HTML zamiast pakietu IPK."
fi

if [ -n "$EXPECTED_SHA" ]; then
    ACTUAL_SHA=""
    if command -v sha256sum >/dev/null 2>&1; then
        ACTUAL_SHA=$(sha256sum "$IPK_FILE" | awk '{print $1}')
    elif command -v openssl >/dev/null 2>&1; then
        ACTUAL_SHA=$(openssl dgst -sha256 "$IPK_FILE" 2>/dev/null | awk '{print $NF}')
    fi

    if [ -n "$ACTUAL_SHA" ]; then
        [ "$ACTUAL_SHA" = "$EXPECTED_SHA" ] \
            || fail "Suma SHA-256 pakietu jest nieprawidłowa."
        log "Weryfikacja SHA-256: OK."
    else
        log "Brak sha256sum/openssl — pominięto lokalną kontrolę SHA-256."
    fi
fi

if opkg status "$PACKAGE" 2>/dev/null | grep -q '^Status:.*installed'; then
    log "Wykryto istniejącą instalację — wykonywana jest aktualizacja/reinstalacja."
    if ! opkg --force-reinstall install "$IPK_FILE" >> "$LOG_FILE" 2>&1; then
        cat "$LOG_FILE"
        fail "opkg nie zainstalował pakietu."
    fi
else
    log "Wykonywana jest świeża instalacja."
    if ! opkg install "$IPK_FILE" >> "$LOG_FILE" 2>&1; then
        cat "$LOG_FILE"
        fail "opkg nie zainstalował pakietu."
    fi
fi

cat "$LOG_FILE"
opkg status "$PACKAGE" 2>/dev/null | grep -q '^Status:.*installed' \
    || fail "Instalacja nie została potwierdzona przez opkg. Sprawdź $LOG_FILE."

log "AIO Panel został zainstalowany. Wykonaj Restart GUI."
cleanup
trap - EXIT HUP INT TERM
exit 0
