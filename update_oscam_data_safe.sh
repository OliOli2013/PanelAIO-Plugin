#!/bin/sh
# AIO Panel 14.0.0 - transactional online update of OSCam auxiliary data.
set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"; . "$PLUGIN_DIR/aio_safe_common.sh" || exit 1
TYPE="${1:-}"; STATUS="${2:-/tmp/PanelAIO/oscam_data.status}"; shift 2 2>/dev/null || true
LOG="/tmp/aio_oscam_data_${TYPE}.log"; WORK="/tmp/PanelAIO/oscam_data_${TYPE}_$$"; FILE="$WORK/new"; BACKUP="$WORK/backup"
mkdir -p "$(dirname "$STATUS")" "$WORK" "$BACKUP" 2>/dev/null || exit 1; rm -f "$STATUS" "$STATUS.tmp" 2>/dev/null || true; : > "$LOG" 2>/dev/null || true
log(){ printf '%s\n' "[AIO OSCam Data] $*" | tee -a "$LOG"; }; status(){ printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }
cleanup(){ rm -rf "$WORK" 2>/dev/null || true; aio_release_lock; }
fail(){ MSG="$1"; STAGE="${2:-unknown}"; log "BŁĄD [$STAGE]: $MSG"; status "ERROR|$MSG|$STAGE|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }
trap 'cleanup' EXIT HUP INT TERM
case "$TYPE" in srvid|srvid2|softcamkey) ;; *) fail "Nieobsługiwany typ danych." arguments ;; esac
aio_acquire_lock "oscam_data_$TYPE" || fail "Ta aktualizacja jest już uruchomiona." lock
FOUND=0
for URL in "$@"; do
  rm -f "$FILE" 2>/dev/null || true
  if aio_secure_download "$URL" "$FILE" 180 2 && aio_not_html "$FILE"; then FOUND=1; log "Pobrano: $URL"; break; fi
done
[ "$FOUND" -eq 1 ] || fail "Żadne źródło HTTPS nie zwróciło poprawnego pliku." download
case "$TYPE" in
  srvid) grep -qE '^[[:space:]]*[0-9A-Fa-f,]+:[0-9A-Fa-f]+' "$FILE" || fail "Nieprawidłowy format oscam.srvid." validation; NAME=oscam.srvid ;;
  srvid2) grep -qE '^[[:space:]]*[0-9A-Fa-f,]+:[0-9A-Fa-f]+' "$FILE" || fail "Nieprawidłowy format oscam.srvid2." validation; NAME=oscam.srvid2 ;;
  softcamkey) grep -qE '^[[:space:]]*[A-Za-z0-9]+[[:space:]]+[0-9A-Fa-f]+' "$FILE" || fail "Nieprawidłowy format SoftCam.Key." validation; NAME=SoftCam.Key ;;
esac
DIRS=""
for PID in $(pidof oscam oscam-emu oscam_emu ncam 2>/dev/null); do
  [ -r "/proc/$PID/cmdline" ] || continue
  CMD=$(tr '\000' ' ' < "/proc/$PID/cmdline" 2>/dev/null || true)
  C=$(printf '%s\n' "$CMD" | sed -n 's/.*[[:space:]]-c[[:space:]]\([^[:space:]]*\).*/\1/p')
  [ -n "$C" ] && [ -d "$C" ] && DIRS="$DIRS
$C"
done
for D in /etc/tuxbox/config/oscam /etc/tuxbox/config /etc/oscam /usr/keys; do [ -d "$D" ] && DIRS="$DIRS
$D"; done
DIRS=$(printf '%s\n' "$DIRS" | sed '/^[[:space:]]*$/d' | awk '!seen[$0]++')
[ -n "$DIRS" ] || fail "Nie znaleziono katalogu konfiguracji OSCam/NCam." detect
STAMP=$(date +%Y%m%d_%H%M%S 2>/dev/null || echo now); COUNT=0
printf '%s\n' "$DIRS" | while IFS= read -r D; do
  [ -d "$D" ] || continue
  [ -f "$D/$NAME" ] && cp -a "$D/$NAME" "$D/$NAME.aio-bak-$STAMP" 2>> "$LOG" || true
  TMP="$D/.${NAME}.aio-new-$$"
  cp "$FILE" "$TMP" 2>> "$LOG" || exit 20
  chmod 644 "$TMP" 2>/dev/null || true
  mv -f "$TMP" "$D/$NAME" 2>> "$LOG" || exit 21
  echo "$D/$NAME" >> "$WORK/installed"
done || fail "Nie udało się zapisać pliku we wszystkich katalogach." install
[ -s "$WORK/installed" ] || fail "Nie zapisano żadnego pliku." verify
COUNT=$(wc -l < "$WORK/installed" | tr -d ' ')
/bin/sh "$PLUGIN_DIR/oscam_control_script.sh" restart /tmp/PanelAIO/oscam_control.status >> "$LOG" 2>&1 || log "Ostrzeżenie: restart CAM wymaga ręcznej kontroli."
sync 2>/dev/null || true
status "OK|$NAME|$COUNT|log=$LOG"; log "OK: $NAME w $COUNT katalogach"; cleanup; trap - EXIT HUP INT TERM; exit 0
