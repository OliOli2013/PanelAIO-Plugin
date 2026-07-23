#!/bin/sh
# AIO Panel 14.0.1 - complete channel-list backup without duplicate latest copy.
set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"
. "$PLUGIN_DIR/aio_safe_common.sh" || exit 1
DEST="${1:-}"; STATUS="${2:-/tmp/PanelAIO/channel_backup.status}"; LOG="/tmp/aio_channels_backup.log"
SOURCE_E2="${AIO_SOURCE_ENIGMA2_DIR:-/etc/enigma2}"
SOURCE_TUXBOX="${AIO_SOURCE_TUXBOX_DIR:-/etc/tuxbox}"
WORK=""; OUT=""
mkdir -p "$(dirname "$STATUS")" 2>/dev/null || true
rm -f "$STATUS" "$STATUS.tmp" 2>/dev/null || true
: > "$LOG" 2>/dev/null || LOG="/tmp/aio_channels_backup_$$.log"
log(){ printf '%s\n' "[AIO Channel Backup] $*" | tee -a "$LOG"; }
status(){ printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }
cleanup(){ [ -n "$WORK" ] && rm -rf "$WORK" 2>/dev/null || true; aio_release_lock; }
fail(){ MSG="$1"; STAGE="${2:-unknown}"; log "BŁĄD [$STAGE]: $MSG"; status "ERROR|$MSG|$STAGE|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }
trap 'cleanup' EXIT HUP INT TERM
aio_acquire_lock channel_lists || fail "Inna operacja list kanałów jest już wykonywana." lock
[ -n "$DEST" ] || fail "Nie podano katalogu backupu." arguments
case "$DEST" in /*) ;; *) fail "Katalog backupu musi być ścieżką bezwzględną." arguments ;; esac
mkdir -p "$DEST" || fail "Nie można utworzyć katalogu backupu." destination
[ -w "$DEST" ] || fail "Katalog backupu nie jest zapisywalny." destination
FREE=$(aio_free_kb "$DEST"); case "$FREE" in ''|*[!0-9]*) FREE=0 ;; esac
[ "$FREE" -ge 20480 ] || fail "Za mało miejsca na backup (minimum 20 MB)." space
STAMP=$(date +%Y%m%d_%H%M%S)
WORK="$DEST/.aio_channel_backup_${STAMP}_$$"; STAGE="$WORK/stage"; OUT_TMP="$WORK/aio_channels_backup_${STAMP}.tar.gz"
OUT="$DEST/aio_channels_backup_${STAMP}.tar.gz"
mkdir -p "$STAGE/enigma2" "$STAGE/tuxbox" || fail "Nie można utworzyć stagingu." workdir

COUNT=0
for N in lamedb lamedb5 bouquets.tv bouquets.radio blacklist whitelist; do
    if [ -f "$SOURCE_E2/$N" ]; then cp -p "$SOURCE_E2/$N" "$STAGE/enigma2/$N" || fail "Błąd kopiowania $N." copy; COUNT=$((COUNT+1)); fi
done
for F in "$SOURCE_E2"/*.tv "$SOURCE_E2"/*.radio "$SOURCE_E2"/*.del; do
    [ -f "$F" ] || continue
    case "$(basename "$F")" in bouquets.tv|bouquets.radio) continue ;; esac
    cp -p "$F" "$STAGE/enigma2/" || fail "Błąd kopiowania $(basename "$F")." copy
    COUNT=$((COUNT+1))
done
for N in satellites.xml cables.xml terrestrial.xml; do
    if [ -f "$SOURCE_TUXBOX/$N" ]; then cp -p "$SOURCE_TUXBOX/$N" "$STAGE/tuxbox/$N" || fail "Błąd kopiowania $N." copy; COUNT=$((COUNT+1)); fi
done
[ "$COUNT" -gt 0 ] || fail "Nie znaleziono plików list kanałów." content
{
    echo 'format=AIO_CHANNEL_BACKUP_V2'
    echo "created=$(date '+%Y-%m-%d %H:%M:%S')"
    echo "files=$COUNT"
    echo "source=$SOURCE_E2,$SOURCE_TUXBOX"
} > "$STAGE/manifest.txt"

tar -czpf "$OUT_TMP" -C "$STAGE" . || fail "Nie można utworzyć archiwum." archive
aio_validate_archive "$OUT_TMP" tar.gz 100000 1073741824 >> "$LOG" 2>&1 || fail "Weryfikacja utworzonego backupu nie powiodła się." verify
mv -f "$OUT_TMP" "$OUT" || fail "Nie można zapisać finalnego backupu." destination
printf '%s\n' "$(basename "$OUT")" > "$DEST/aio_channels_backup.latest.tmp" && mv -f "$DEST/aio_channels_backup.latest.tmp" "$DEST/aio_channels_backup.latest" || true
# Retain the five newest dated backups; never delete the file just created.
ls -1t "$DEST"/aio_channels_backup_*.tar.gz 2>/dev/null | awk 'NR>5' | while IFS= read -r OLD; do [ "$OLD" = "$OUT" ] || rm -f "$OLD" 2>/dev/null || true; done
sync 2>/dev/null || true
status "OK|$OUT|files=$COUNT|log=$LOG"
log "OK: zapisano $OUT ($COUNT plików)."
cleanup; trap - EXIT HUP INT TERM; exit 0
