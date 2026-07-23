#!/bin/sh
# AIO Panel 14.0.0 - transactional GitHub source installer.
set -u
REPO="OliOli2013/PanelAIO-Plugin"; BRANCH="main"
BASE="/usr/lib/enigma2/python/Plugins"; DST="$BASE/SystemPlugins/PanelAIO"; OLD="$BASE/Extensions/PanelAIO"
SELF_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
# During an online update this helper may not yet exist next to /tmp installer.
if [ -f "$SELF_DIR/aio_safe_common.sh" ]; then AIO_PLUGIN_DIR="$SELF_DIR"; . "$SELF_DIR/aio_safe_common.sh"
elif [ -f "$DST/aio_safe_common.sh" ]; then AIO_PLUGIN_DIR="$DST"; . "$DST/aio_safe_common.sh"
else echo '[PanelAIO] Missing aio_safe_common.sh; use the IPK package for recovery.'; exit 1; fi
URL1="https://github.com/${REPO}/archive/refs/heads/${BRANCH}.zip"; URL2="https://codeload.github.com/${REPO}/zip/refs/heads/${BRANCH}"
TMP="/tmp/PanelAIO/github_update_$$"; ZIP="$TMP/repo.zip"; EXTRACT="$TMP/extract"; NEW="$DST.aio-new-$$"; BAK="$DST.aio-old-$$"; LOG="/tmp/aio_github_update.log"
: > "$LOG" 2>/dev/null || true
log(){ printf '%s\n' "[PanelAIO] $*" | tee -a "$LOG"; }; cleanup(){ rm -rf "$TMP" "$NEW" 2>/dev/null || true; aio_release_lock; }
fail(){ log "ERROR: $1"; if [ -d "$BAK" ] && [ ! -d "$DST" ]; then mv "$BAK" "$DST" 2>/dev/null || true; fi; cleanup; trap - EXIT HUP INT TERM; exit 1; }
trap 'cleanup' EXIT HUP INT TERM
aio_acquire_lock plugin_update || fail "Another AIO update is already running."
rm -rf "$TMP" "$NEW" "$BAK" 2>/dev/null || true; mkdir -p "$EXTRACT" "$NEW" || fail "Cannot create staging directories."
aio_secure_download "$URL1" "$ZIP" 600 3 || aio_secure_download "$URL2" "$ZIP" 600 3 || fail "Cannot download repository ZIP over HTTPS."
aio_not_html "$ZIP" || fail "HTML response received instead of ZIP."
aio_validate_archive "$ZIP" zip 100000 1073741824 >> "$LOG" 2>&1 || fail "Unsafe or damaged repository ZIP."
command -v unzip >/dev/null 2>&1 || fail "unzip is missing. Install it before running the source updater."
unzip -oq "$ZIP" -d "$EXTRACT" >> "$LOG" 2>&1 || fail "Cannot extract repository ZIP."
SRC=""
for D in "$EXTRACT/PanelAIO-Plugin-main" "$EXTRACT/PanelAIO-Plugin-main/AIO-Panel" "$EXTRACT/PanelAIO-Plugin-$BRANCH" "$EXTRACT/PanelAIO-Plugin-$BRANCH/AIO-Panel"; do [ -f "$D/plugin.py" ] && [ -f "$D/version.txt" ] && { SRC="$D"; break; }; done
if [ -z "$SRC" ]; then F=$(find "$EXTRACT" -type f -name plugin.py -print -quit 2>/dev/null); [ -n "$F" ] && SRC=$(dirname "$F"); fi
[ -n "$SRC" ] || fail "Plugin source root not found."
cp -pR "$SRC"/. "$NEW/" || fail "Cannot copy staged plugin."
rm -rf "$NEW/.git" "$NEW/.github" "$NEW/release" "$NEW/releases" "$NEW/control" "$NEW/packaging" 2>/dev/null || true
find "$NEW" -type d -name __pycache__ -exec rm -rf {} \; 2>/dev/null || true; find "$NEW" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true
for REQUIRED in plugin.py legacy_plugin.py version.txt install_archive_script.sh picon_install_script.sh aio_safe_common.sh; do [ -s "$NEW/$REQUIRED" ] || fail "Missing required file: $REQUIRED"; done
PY=$(aio_python 2>/dev/null || true); [ -n "$PY" ] || fail "Python interpreter not found."
"$PY" -m py_compile "$NEW/plugin.py" "$NEW/legacy_plugin.py" >> "$LOG" 2>&1 || fail "Python syntax validation failed."
for S in "$NEW"/*.sh; do [ -f "$S" ] || continue; /bin/sh -n "$S" >> "$LOG" 2>&1 || fail "Shell syntax error: $(basename "$S")"; done
find "$NEW" -type f -name '*.sh' -exec chmod 755 {} \; 2>/dev/null || true; find "$NEW" -type f -name '*.py' -exec chmod 644 {} \; 2>/dev/null || true; find "$NEW" -type f -name '*.png' -exec chmod 644 {} \; 2>/dev/null || true
[ -d "$DST" ] && mv "$DST" "$BAK" || true
mv "$NEW" "$DST" || { [ -d "$BAK" ] && mv "$BAK" "$DST" 2>/dev/null || true; fail "Atomic activation failed."; }
[ -s "$DST/plugin.py" ] && [ -s "$DST/legacy_plugin.py" ] || { rm -rf "$DST" 2>/dev/null || true; [ -d "$BAK" ] && mv "$BAK" "$DST" 2>/dev/null || true; fail "Post-activation validation failed."; }
# Remove legacy Extensions copy only after successful activation, preserving one recovery copy temporarily.
if [ -d "$OLD" ]; then rm -rf "$OLD.aio-legacy" 2>/dev/null || true; mv "$OLD" "$OLD.aio-legacy" 2>/dev/null || true; fi
rm -rf "$BAK" "$OLD.aio-legacy" 2>/dev/null || true
sync 2>/dev/null || true
log "Installed version: $(cat "$DST/version.txt" 2>/dev/null || echo unknown). Manual GUI restart is recommended after verification."
cleanup; trap - EXIT HUP INT TERM; exit 0
