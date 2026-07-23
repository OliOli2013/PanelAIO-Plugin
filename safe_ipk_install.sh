#!/bin/sh
# AIO Panel 14.0.0 - HTTPS IPK downloader/validator/installer.
set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"; . "$PLUGIN_DIR/aio_safe_common.sh" || exit 1
URL="${1:-}"; EXPECTED="${2:-^[A-Za-z0-9.+_-]+$}"; STATUS="${3:-/tmp/PanelAIO/ipk_install.status}"; SHA="${4:-}"; LOG="/tmp/aio_ipk_install.log"; FILE="/tmp/PanelAIO/aio_package_$$.ipk"
mkdir -p "$(dirname "$STATUS")" /tmp/PanelAIO 2>/dev/null || true; rm -f "$STATUS" "$STATUS.tmp" "$FILE" 2>/dev/null || true; : > "$LOG" 2>/dev/null || true
log(){ printf '%s\n' "[AIO IPK] $*" | tee -a "$LOG"; }; status(){ printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }; cleanup(){ rm -f "$FILE" 2>/dev/null || true; aio_release_lock; }
fail(){ MSG="$1"; STAGE="${2:-unknown}"; log "BŁĄD [$STAGE]: $MSG"; status "ERROR|$MSG|$STAGE|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }
trap 'cleanup' EXIT HUP INT TERM
aio_acquire_lock opkg || fail "Inna operacja OPKG jest już wykonywana." lock
aio_secure_download "$URL" "$FILE" 600 3 || fail "Nie udało się pobrać IPK przez HTTPS." download
aio_not_html "$FILE" || fail "Pobrano HTML zamiast IPK." validation
PY=$(aio_python 2>/dev/null || true); [ -n "$PY" ] || fail "Brak Pythona do walidacji IPK." dependency
META=$("$PY" "$PLUGIN_DIR/core/ipk_validator.py" "$FILE" "$EXPECTED" 2>> "$LOG") || fail "IPK jest uszkodzony albo ma nieoczekiwaną nazwę pakietu." validation
if [ -n "$SHA" ]; then GOT=$(aio_sha256 "$FILE" 2>/dev/null || true); [ "$GOT" = "$SHA" ] || fail "Suma SHA-256 IPK nie pasuje." checksum; fi
PACKAGE=$(printf '%s' "$META" | awk -F'|' '{print $2}')
log "Instalacja pakietu: $PACKAGE"
opkg install --force-reinstall "$FILE" >> "$LOG" 2>&1 || opkg install "$FILE" >> "$LOG" 2>&1 || fail "opkg nie zainstalował pakietu." install
opkg list-installed 2>/dev/null | awk '{print $1}' | grep -qx "$PACKAGE" || fail "Pakiet nie jest widoczny jako zainstalowany." verify
status "OK|$PACKAGE|log=$LOG"; log "OK: $PACKAGE"; cleanup; trap - EXIT HUP INT TERM; exit 0
