#!/bin/sh
# AIO Panel 14.0.0 - multi-path OSCam configuration backup.
set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"; . "$PLUGIN_DIR/aio_safe_common.sh" || exit 1
DEST="${1:-}"; STATUS="${2:-/tmp/PanelAIO/oscam_backup.status}"; LOG="/tmp/aio_oscam_backup.log"; WORK=""
ROOT_PREFIX="${AIO_ROOT_PREFIX:-}"
CONFIG_OVERRIDE="${AIO_OSCAM_CONFIG_DIRS:-}"
mkdir -p "$(dirname "$STATUS")" 2>/dev/null || true; rm -f "$STATUS" "$STATUS.tmp" 2>/dev/null || true; : > "$LOG" 2>/dev/null || true
log(){ printf '%s\n' "[AIO OSCam Backup] $*" | tee -a "$LOG"; }; status(){ printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }
cleanup(){ [ -n "$WORK" ] && rm -rf "$WORK" 2>/dev/null || true; aio_release_lock; }; fail(){ MSG="$1"; STAGE="${2:-unknown}"; log "BŁĄD [$STAGE]: $MSG"; status "ERROR|$MSG|$STAGE|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }
copy_regular_tree(){ SRC="$1"; DST="$2"; mkdir -p "$DST" || return 1; find "$SRC" -type f 2>/dev/null | while IFS= read -r F; do REL=${F#"$SRC"/}; case "$REL" in *'..'*) exit 2;; esac; mkdir -p "$DST/$(dirname "$REL")" || exit 3; cp -p "$F" "$DST/$REL" || exit 4; done; }
trap 'cleanup' EXIT HUP INT TERM
aio_acquire_lock oscam_config || fail "Inna operacja konfiguracji OSCam jest już wykonywana." lock
[ -n "$DEST" ] || fail "Nie podano katalogu backupu." arguments; mkdir -p "$DEST" || fail "Nie można utworzyć katalogu backupu." destination; [ -w "$DEST" ] || fail "Katalog backupu nie jest zapisywalny." destination
FREE=$(aio_free_kb "$DEST"); case "$FREE" in ''|*[!0-9]*) FREE=0 ;; esac; [ "$FREE" -ge 20480 ] || fail "Za mało miejsca na backup (minimum 20 MB)." space
STAMP=$(date +%Y%m%d_%H%M%S); WORK="$DEST/.aio_oscam_backup_${STAMP}_$$"; STAGE="$WORK/stage"; OUT="$DEST/aio_oscam_config_backup_${STAMP}.tar.gz"; mkdir -p "$STAGE/rootfs" || fail "Nie można utworzyć stagingu." workdir
DIRS="$CONFIG_OVERRIDE"
# Running process -c path first in production.
if [ -z "$ROOT_PREFIX" ] && [ -z "$CONFIG_OVERRIDE" ]; then
    for PID in $(pidof oscam 2>/dev/null) $(pidof oscam-emu 2>/dev/null) $(pidof oscam_emu 2>/dev/null); do
        [ -r "/proc/$PID/cmdline" ] || continue; CMD=$(tr '\000' ' ' < "/proc/$PID/cmdline" 2>/dev/null); PREV=""; for A in $CMD; do if [ "$PREV" = c ]; then DIRS="$DIRS $A"; PREV=""; continue; fi; case "$A" in -c) PREV=c;; -c*) DIRS="$DIRS ${A#-c}";; esac; done
    done
fi
if [ -z "$CONFIG_OVERRIDE" ]; then
    for L in /etc/tuxbox/config /etc/tuxbox/config/oscam /etc/tuxbox/config/oscam-emu /etc/oscam /usr/keys /var/keys; do D="$ROOT_PREFIX$L"; [ -f "$D/oscam.conf" ] && DIRS="$DIRS $D" || true; done
fi
UNIQUE="$WORK/dirs"; : > "$UNIQUE"; for D in $DIRS; do [ -d "$D" ] || continue; grep -qxF "$D" "$UNIQUE" 2>/dev/null || echo "$D" >> "$UNIQUE"; done
[ -s "$UNIQUE" ] || fail "Nie wykryto katalogu z oscam.conf." detection
COUNT=0
while IFS= read -r D; do
    if [ -n "$ROOT_PREFIX" ]; then REL=${D#"$ROOT_PREFIX"/}; LOGICAL=/$REL; else REL=${D#/}; LOGICAL=$D; fi
    case "$REL" in etc/tuxbox/config*|etc/oscam*|usr/keys*|var/keys*) ;; *) fail "Niedozwolony katalog konfiguracji: $D" validation ;; esac
    copy_regular_tree "$D" "$STAGE/rootfs/$REL" || fail "Nie można skopiować $D." copy
    echo "$LOGICAL" >> "$STAGE/config_dirs.txt"; COUNT=$((COUNT+1))
done < "$UNIQUE"
{
 echo 'format=AIO_OSCAM_BACKUP_V2'; echo "created=$(date '+%Y-%m-%d %H:%M:%S')"; echo "directories=$COUNT";
} > "$STAGE/manifest.txt"
tar -czpf "$WORK/backup.tar.gz" -C "$STAGE" . || fail "Nie można utworzyć archiwum." archive
aio_validate_archive "$WORK/backup.tar.gz" tar.gz 100000 536870912 >> "$LOG" 2>&1 || fail "Weryfikacja backupu nie powiodła się." verify
mv -f "$WORK/backup.tar.gz" "$OUT" || fail "Nie można zapisać backupu." destination
printf '%s\n' "$(basename "$OUT")" > "$DEST/aio_oscam_config_backup.latest.tmp" && mv -f "$DEST/aio_oscam_config_backup.latest.tmp" "$DEST/aio_oscam_config_backup.latest" || true
ls -1t "$DEST"/aio_oscam_config_backup_*.tar.gz 2>/dev/null | awk 'NR>5' | while IFS= read -r OLD; do [ "$OLD" = "$OUT" ] || rm -f "$OLD" 2>/dev/null || true; done
status "OK|$OUT|directories=$COUNT|log=$LOG"; log "OK: $OUT"; cleanup; trap - EXIT HUP INT TERM; exit 0
