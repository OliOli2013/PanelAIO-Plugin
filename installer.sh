#!/bin/sh
# AIO Panel 14.0.1 - standalone online installer/update script
# Works for both a fresh installation and an existing installation.

VERSION="14.0.1"
PACKAGE="enigma2-plugin-extensions-panelaio_${VERSION}_all.ipk"
EXPECTED_SHA256="b87f3e8f687fcd2288f96ff1b7740be797f1b3d134c873abe610659117fa578f"
URL_PRIMARY="https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/release/${PACKAGE}"
URL_FALLBACK="https://github.com/OliOli2013/PanelAIO-Plugin/raw/refs/heads/main/release/${PACKAGE}"
TMP="/tmp/${PACKAGE}"
LOG="/tmp/panelaio_installer.log"

log() {
    echo "[AIO Panel] $*" | tee -a "$LOG"
}

fail() {
    log "BŁĄD: $*"
    rm -f "$TMP" 2>/dev/null
    exit 1
}

download_file() {
    url="$1"
    out="$2"

    if command -v wget >/dev/null 2>&1; then
        wget -q -O "$out" "$url" && return 0
    fi

    if command -v curl >/dev/null 2>&1; then
        curl -fL --connect-timeout 30 --max-time 600 -o "$out" "$url" && return 0
    fi

    return 1
}

: > "$LOG" 2>/dev/null || true
rm -f "$TMP" 2>/dev/null

command -v opkg >/dev/null 2>&1 || fail "Nie znaleziono polecenia opkg."

log "Pobieranie AIO Panel ${VERSION}..."
download_file "$URL_PRIMARY" "$TMP" || download_file "$URL_FALLBACK" "$TMP" || fail "Nie można pobrać pakietu IPK z GitHuba."

[ -s "$TMP" ] || fail "Pobrany plik jest pusty."

SIZE=$(wc -c < "$TMP" 2>/dev/null || echo 0)
[ "$SIZE" -gt 10000 ] 2>/dev/null || fail "Pobrany plik jest zbyt mały i prawdopodobnie nie jest pakietem IPK."

if head -c 512 "$TMP" 2>/dev/null | grep -Eqi '<!DOCTYPE|<html|404: Not Found'; then
    fail "GitHub zwrócił stronę HTML zamiast pakietu IPK."
fi

if command -v sha256sum >/dev/null 2>&1; then
    ACTUAL_SHA256=$(sha256sum "$TMP" 2>/dev/null | awk '{print $1}')
    [ "$ACTUAL_SHA256" = "$EXPECTED_SHA256" ] || fail "Suma SHA-256 pobranego IPK jest nieprawidłowa."
elif command -v openssl >/dev/null 2>&1; then
    ACTUAL_SHA256=$(openssl dgst -sha256 "$TMP" 2>/dev/null | awk '{print $NF}')
    [ "$ACTUAL_SHA256" = "$EXPECTED_SHA256" ] || fail "Suma SHA-256 pobranego IPK jest nieprawidłowa."
else
    log "OSTRZEŻENIE: brak sha256sum/openssl — pominięto kontrolę SHA-256."
fi

log "Instalacja pakietu ${PACKAGE}..."
if opkg install --force-reinstall "$TMP" >> "$LOG" 2>&1; then
    :
elif opkg install --force-overwrite --force-reinstall "$TMP" >> "$LOG" 2>&1; then
    :
else
    fail "Instalacja OPKG nie powiodła się. Log: $LOG"
fi

rm -f "$TMP" 2>/dev/null
sync 2>/dev/null || true

log "AIO Panel ${VERSION} został zainstalowany."
log "Wykonaj restart GUI: killall -9 enigma2"
exit 0
