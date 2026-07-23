#!/bin/sh
# AIO Panel 14.0.1 - validated OSCam restore with rollback.
set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"; . "$PLUGIN_DIR/aio_safe_common.sh" || exit 1
ARCHIVE="${1:-}"; STATUS="${2:-/tmp/PanelAIO/oscam_restore.status}"; LOG="/tmp/aio_oscam_restore.log"; WORK=""; APPLY=0
ROOT_PREFIX="${AIO_ROOT_PREFIX:-}"
TEST_NO_OSCAM="${AIO_TEST_NO_OSCAM:-0}"
mkdir -p "$(dirname "$STATUS")" 2>/dev/null || true; rm -f "$STATUS" "$STATUS.tmp" 2>/dev/null || true; : > "$LOG" 2>/dev/null || true
log(){ printf '%s\n' "[AIO OSCam Restore] $*" | tee -a "$LOG"; }; status(){ printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }
cleanup(){ [ -n "$WORK" ] && rm -rf "$WORK" 2>/dev/null || true; aio_release_lock; }
restore_rollback(){ [ -d "$WORK/rollback/rootfs" ] || return 1; mkdir -p "$ROOT_PREFIX" 2>/dev/null || true; cp -pR "$WORK/rollback/rootfs"/. "$ROOT_PREFIX/" || return 1; sync 2>/dev/null || true; }
fail(){ MSG="$1"; STAGE="${2:-unknown}"; RB=not-needed; log "BŁĄD [$STAGE]: $MSG"; if [ "$APPLY" -eq 1 ]; then restore_rollback && RB=ok || RB=failed; [ "$TEST_NO_OSCAM" = "1" ] || /bin/sh "$PLUGIN_DIR/oscam_control_script.sh" restart /tmp/PanelAIO/oscam_restore_restart.status >> "$LOG" 2>&1 || true; fi; status "ERROR|$MSG|$STAGE|rollback=$RB|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }
copy_current(){ DST="$1"; mkdir -p "$DST/rootfs"; for L in /etc/tuxbox/config /etc/tuxbox/config/oscam /etc/tuxbox/config/oscam-emu /etc/oscam /usr/keys /var/keys; do D="$ROOT_PREFIX$L"; [ -d "$D" ] || continue; REL=${L#/}; mkdir -p "$DST/rootfs/$REL"; find "$D" -type f 2>/dev/null | while IFS= read -r F; do R=${F#"$D"/}; mkdir -p "$DST/rootfs/$REL/$(dirname "$R")" || exit 2; cp -p "$F" "$DST/rootfs/$REL/$R" || exit 3; done || return 1; done; }
trap 'cleanup' EXIT HUP INT TERM
aio_acquire_lock oscam_config || fail "Inna operacja konfiguracji OSCam jest już wykonywana." lock
[ -s "$ARCHIVE" ] || fail "Brak archiwum backupu." arguments
aio_validate_archive "$ARCHIVE" tar.gz 100000 536870912 >> "$LOG" 2>&1 || fail "Backup jest uszkodzony lub niebezpieczny." validation
WORK="/tmp/aio_oscam_restore_$(date +%Y%m%d_%H%M%S)_$$"; mkdir -p "$WORK/stage" "$WORK/rollback" || fail "Nie można utworzyć stagingu." workdir
tar -xzpf "$ARCHIVE" -C "$WORK/stage" || fail "Nie można rozpakować backupu." extract
[ -f "$WORK/stage/manifest.txt" ] && grep -q '^format=AIO_OSCAM_BACKUP_V2$' "$WORK/stage/manifest.txt" || fail "Nieobsługiwany format backupu OSCam." content
[ -d "$WORK/stage/rootfs" ] || fail "Brak rootfs w backupie." content
# Restrict top-level restore paths.
find "$WORK/stage/rootfs" -type f 2>/dev/null | while IFS= read -r F; do REL=${F#"$WORK/stage/rootfs"/}; case "$REL" in etc/tuxbox/config/*|etc/oscam/*|usr/keys/*|var/keys/*) ;; *) echo "Blocked path: $REL" >&2; exit 2;; esac; done || fail "Backup próbuje zapisać poza dozwolonymi katalogami OSCam." validation
find "$WORK/stage/rootfs" -type f -name oscam.conf | grep -q . || fail "Backup nie zawiera oscam.conf." content
copy_current "$WORK/rollback" || fail "Nie można przygotować rollbacku bieżącej konfiguracji." backup
[ "$TEST_NO_OSCAM" = "1" ] || /bin/sh "$PLUGIN_DIR/oscam_control_script.sh" stop /tmp/PanelAIO/oscam_restore_stop.status >> "$LOG" 2>&1 || true
APPLY=1
mkdir -p "$ROOT_PREFIX" 2>/dev/null || true
cp -pR "$WORK/stage/rootfs"/. "$ROOT_PREFIX/" || fail "Błąd kopiowania konfiguracji." apply
find "$ROOT_PREFIX/etc/tuxbox/config" "$ROOT_PREFIX/etc/oscam" "$ROOT_PREFIX/usr/keys" "$ROOT_PREFIX/var/keys" -type f 2>/dev/null -exec chmod 600 {} \; || true
sync 2>/dev/null || true
if [ "$TEST_NO_OSCAM" != "1" ]; then /bin/sh "$PLUGIN_DIR/oscam_control_script.sh" restart /tmp/PanelAIO/oscam_restore_restart.status >> "$LOG" 2>&1 || fail "Konfiguracja została zapisana, ale OSCam nie wystartował." restart; fi
APPLY=0
status "OK|$ARCHIVE|log=$LOG"; log "Restore OSCam zakończony poprawnie."; cleanup; trap - EXIT HUP INT TERM; exit 0
