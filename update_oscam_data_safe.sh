#!/bin/sh
# AIO Panel 16.0.2 - validated OSCam data updates with explicit results.
set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"; . "$PLUGIN_DIR/aio_safe_common.sh" || exit 1
TYPE="${1:-}"; STATUS="${2:-/tmp/PanelAIO/oscam_data.status}"
case "$TYPE" in services|srvid|srvid2|softcamkey) ;; *) echo 'Invalid data type' >&2; exit 2 ;; esac
[ "$#" -ge 3 ] || { echo 'Missing data sources' >&2; exit 2; }
shift 2
LOG="/tmp/aio_oscam_data_${TYPE}.log"
WORK=$(mktemp -d /tmp/aio-oscam-data.XXXXXX) || exit 1
mkdir -p "$(dirname "$STATUS")" "$WORK/prepared" || exit 1
log(){ printf '%s\n' "[AIO OSCam Data] $*" | tee -a "$LOG"; }
status(){ printf '%s\n' "$*" > "$STATUS.tmp" && mv -f "$STATUS.tmp" "$STATUS"; }
cleanup(){ rm -rf "$WORK"; aio_release_lock; }
fail(){ log "ERROR: $1"; status "ERROR|$1|log=$LOG"; exit 1; }
trap cleanup EXIT
trap 'exit 130' HUP INT TERM
aio_acquire_lock oscam_data || fail 'Another OSCam data update is running'
: > "$LOG"
rm -f "$STATUS" "$STATUS.tmp" "$STATUS.json"
PY=$(aio_python) || fail 'Python is missing'
FOUND=0
for SOURCE in "$@"; do
    log "Downloading: $SOURCE"
    if aio_secure_download "$SOURCE" "$WORK/download" 30 2 >> "$LOG" 2>&1; then
        if "$PY" "$PLUGIN_DIR/core/oscam_data.py" prepare "$TYPE" "$WORK/download" "$WORK/prepared" >> "$LOG" 2>&1; then
            FOUND=1; break
        fi
        log 'Invalid data; trying next source'
    else
        log 'Download failed; trying next source'
    fi
done
[ "$FOUND" -eq 1 ] || fail 'No source returned valid data; existing files were not changed'
"$PY" "$PLUGIN_DIR/core/oscam_data.py" install "$TYPE" "$WORK/prepared" "$STATUS.json" >> "$LOG" 2>&1 || fail 'Cannot install or verify OSCam data; check log'
# Do not guess a binary or restart a different CAM. Report that a reload is needed.
status "OK|$TYPE|report=$STATUS.json|log=$LOG"
log 'Files verified. Reload/restart the active CAM from its manager to apply changes.'
exit 0
