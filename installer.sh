#!/bin/sh
# AIO Panel 14.0.1 - online installer/update script (E2iPlayer hotfix)
VERSION="14.0.1"
PACKAGE="enigma2-plugin-extensions-panelaio_${VERSION}_all.ipk"
EXPECTED_SHA256="a2d5ef14ce54de1234763eefd31cf846bb8ae228d97259e80c98182d435c5aa0"
URL_PRIMARY="https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/release/${PACKAGE}"
URL_FALLBACK="https://github.com/OliOli2013/PanelAIO-Plugin/raw/refs/heads/main/release/${PACKAGE}"
TMP="/tmp/${PACKAGE}"
LOG="/tmp/panelaio_installer.log"
log(){ echo "[AIO Panel] $*" | tee -a "$LOG"; }
fail(){ log "BŁĄD: $*"; rm -f "$TMP" 2>/dev/null; exit 1; }
download_file(){
    url="$1"; out="$2"
    if command -v wget >/dev/null 2>&1; then wget -q -O "$out" "$url" && return 0; fi
    if command -v curl >/dev/null 2>&1; then curl -fL --connect-timeout 30 --max-time 600 -o "$out" "$url" && return 0; fi
    return 1
}
: > "$LOG" 2>/dev/null || true
rm -f "$TMP" 2>/dev/null
command -v opkg >/dev/null 2>&1 || fail "Nie znaleziono polecenia opkg."
log "Pobieranie AIO Panel ${VERSION} (E2iPlayer hotfix)..."
download_file "$URL_PRIMARY" "$TMP" || download_file "$URL_FALLBACK" "$TMP" || fail "Nie można pobrać pakietu IPK z GitHuba."
[ -s "$TMP" ] || fail "Pobrany plik jest pusty."
SIZE=$(wc -c < "$TMP" 2>/dev/null || echo 0)
[ "$SIZE" -gt 10000 ] 2>/dev/null || fail "Pobrany plik jest zbyt mały."
if head -c 512 "$TMP" 2>/dev/null | grep -Eqi '<!DOCTYPE|<html|404: Not Found'; then fail "GitHub zwrócił HTML zamiast IPK."; fi
if command -v sha256sum >/dev/null 2>&1; then
    ACTUAL=$(sha256sum "$TMP" | awk '{print $1}')
    [ "$ACTUAL" = "$EXPECTED_SHA256" ] || fail "Nieprawidłowa suma SHA-256."
elif command -v openssl >/dev/null 2>&1; then
    ACTUAL=$(openssl dgst -sha256 "$TMP" | awk '{print $NF}')
    [ "$ACTUAL" = "$EXPECTED_SHA256" ] || fail "Nieprawidłowa suma SHA-256."
fi
log "Wymuszona ponowna instalacja tej samej wersji 14.0.1..."
opkg install --force-reinstall "$TMP" >> "$LOG" 2>&1 || opkg install --force-overwrite --force-reinstall "$TMP" >> "$LOG" 2>&1 || fail "Instalacja OPKG nie powiodła się. Log: $LOG"
rm -f "$TMP" 2>/dev/null
sync 2>/dev/null || true
log "AIO Panel 14.0.1 z poprawką E2iPlayer został zainstalowany."
log "Poprawka warstwy shell działa od razu; pełne przeładowanie kodu nastąpi po restarcie GUI."
exit 0
