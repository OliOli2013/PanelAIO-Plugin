#!/bin/sh
# AIO Panel 14.0.1 - transactional installer for a fixed plugin directory from an HTTPS archive.
set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"; . "$PLUGIN_DIR/aio_safe_common.sh" || exit 1
URL="${1:-}"; SOURCE_REL="${2:-}"; TARGET="${3:-}"; MARKER="${4:-plugin.py}"; STATUS="${5:-/tmp/PanelAIO/plugin_archive.status}"
LOG="/tmp/aio_plugin_archive_install.log"; WORK="/tmp/PanelAIO/plugin_archive_$$"; ARCHIVE="$WORK/archive"
mkdir -p "$(dirname "$STATUS")" /tmp/PanelAIO 2>/dev/null || true; rm -rf "$WORK" "$STATUS" "$STATUS.tmp" 2>/dev/null || true; mkdir -p "$WORK/extract" || exit 1; : > "$LOG" 2>/dev/null || true
log(){ printf '%s\n' "[AIO Plugin Archive] $*" | tee -a "$LOG"; }
status(){ printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }
cleanup(){ rm -rf "$WORK" 2>/dev/null || true; aio_release_lock; }
fail(){ MSG="$1"; STAGE="${2:-unknown}"; log "BŁĄD [$STAGE]: $MSG"; status "ERROR|$MSG|$STAGE|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }
trap 'cleanup' EXIT HUP INT TERM
aio_acquire_lock plugin_archive || fail "Inny instalator wtyczki jest już uruchomiony." lock
case "$SOURCE_REL" in /*|*..*) fail "Niedozwolona ścieżka źródłowa." arguments ;; esac
case "$TARGET" in /usr/lib/enigma2/python/Plugins/Extensions/*|/usr/lib/enigma2/python/Plugins/SystemPlugins/*) ;; *) fail "Niedozwolony katalog docelowy." arguments ;; esac
case "$MARKER" in *[!A-Za-z0-9._/-]*|/*|*..*) fail "Niedozwolony marker." arguments ;; esac
aio_secure_download "$URL" "$ARCHIVE" 600 3 || fail "Nie udało się pobrać archiwum przez HTTPS." download
aio_not_html "$ARCHIVE" || fail "Pobrano HTML zamiast archiwum." validation
PY=$(aio_python 2>/dev/null || true); [ -n "$PY" ] || fail "Brak Pythona do walidacji." dependency
"$PY" "$PLUGIN_DIR/core/archive_validator.py" "$ARCHIVE" >> "$LOG" 2>&1 || fail "Archiwum jest niebezpieczne lub uszkodzone." validation
if dd if="$ARCHIVE" bs=2 count=1 2>/dev/null | grep -q '^PK'; then
  command -v unzip >/dev/null 2>&1 || fail "Brak unzip." dependency
  unzip -q "$ARCHIVE" -d "$WORK/extract" >> "$LOG" 2>&1 || fail "Nie można rozpakować ZIP." extract
else
  tar -xzf "$ARCHIVE" -C "$WORK/extract" >> "$LOG" 2>&1 || fail "Nie można rozpakować TAR.GZ." extract
fi
SOURCE="$WORK/extract/$SOURCE_REL"
[ -d "$SOURCE" ] || fail "Brak oczekiwanego katalogu w archiwum." validation
[ -f "$SOURCE/$MARKER" ] || fail "Brak pliku kontrolnego wtyczki." validation
find "$SOURCE" -type l -exec sh -c 'for x do t=$(readlink "$x") || exit 1; case "$t" in /*|*..*) exit 2;; esac; done' sh {} + >> "$LOG" 2>&1 || fail "Niedozwolone dowiązanie w archiwum." validation
PARENT=$(dirname "$TARGET"); BASE=$(basename "$TARGET"); STAGED="$PARENT/.${BASE}.aio-new-$$"; BACKUP="$PARENT/.${BASE}.aio-old-$$"
mkdir -p "$PARENT" || fail "Nie można utworzyć katalogu docelowego." install
rm -rf "$STAGED" "$BACKUP" 2>/dev/null || true
cp -a "$SOURCE" "$STAGED" >> "$LOG" 2>&1 || fail "Nie można przygotować nowej wersji." install
[ -f "$STAGED/$MARKER" ] || fail "Walidacja stagingu nie powiodła się." verify
if [ -d "$TARGET" ]; then mv "$TARGET" "$BACKUP" || fail "Nie można zabezpieczyć starej wersji." backup; fi
if ! mv "$STAGED" "$TARGET"; then [ -d "$BACKUP" ] && mv "$BACKUP" "$TARGET" 2>/dev/null || true; fail "Nie można aktywować nowej wersji." activate; fi
chmod -R u+rwX,go+rX "$TARGET" 2>/dev/null || true
if [ -n "$PY" ]; then "$PY" -m compileall -q "$TARGET" >> "$LOG" 2>&1 || { rm -rf "$TARGET"; [ -d "$BACKUP" ] && mv "$BACKUP" "$TARGET"; fail "Kod Python nie przechodzi kompilacji." verify; }; fi
rm -rf "$BACKUP" 2>/dev/null || true
sync 2>/dev/null || true
status "OK|$TARGET|log=$LOG"; log "OK: $TARGET"; cleanup; trap - EXIT HUP INT TERM; exit 0
