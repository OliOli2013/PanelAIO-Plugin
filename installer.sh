#!/bin/sh
# AIO Panel 16.0.0 - IPK-first transactional installer/updater with source-recovery fallback.
set -u
REPO="OliOli2013/PanelAIO-Plugin"
BRANCH="${1:-main}"
case "$BRANCH" in main|test) ;; *) echo "[PanelAIO] Unsupported update branch: $BRANCH" >&2; exit 2 ;; esac
BASE="/usr/lib/enigma2/python/Plugins"; DST="$BASE/SystemPlugins/PanelAIO"; OLD="$BASE/Extensions/PanelAIO"
SELF_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
BOOT="/tmp/PanelAIO/bootstrap_$$"
mkdir -p "$BOOT/core" 2>/dev/null || { echo '[PanelAIO] Cannot create bootstrap directory.' >&2; exit 1; }

# Fresh-install bootstrap: wget .../installer.sh | /bin/sh has no companion files yet.
# Download only the exact AIO helper from this repository/branch, sanity-check it, then source it.
if [ -f "$SELF_DIR/aio_safe_common.sh" ]; then
    AIO_PLUGIN_DIR="$SELF_DIR"; . "$SELF_DIR/aio_safe_common.sh"
elif [ -f "$DST/aio_safe_common.sh" ]; then
    AIO_PLUGIN_DIR="$DST"; . "$DST/aio_safe_common.sh"
else
    COMMON_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}/aio_safe_common.sh"
    command -v wget >/dev/null 2>&1 || { echo '[PanelAIO] wget is required.' >&2; exit 1; }
    wget -q -O "$BOOT/aio_safe_common.sh" "$COMMON_URL" || { echo '[PanelAIO] Cannot bootstrap aio_safe_common.sh.' >&2; exit 1; }
    [ -s "$BOOT/aio_safe_common.sh" ] || { echo '[PanelAIO] Empty bootstrap helper.' >&2; exit 1; }
    grep -q 'aio_secure_download' "$BOOT/aio_safe_common.sh" || { echo '[PanelAIO] Invalid bootstrap helper.' >&2; exit 1; }
    AIO_PLUGIN_DIR="$BOOT"; . "$BOOT/aio_safe_common.sh" || exit 1
fi
TMP="/tmp/PanelAIO/github_update_$$"; EXTRACT="$TMP/extract"; ZIP="$TMP/repo.zip"; NEW="$DST.aio-new-$$"; BAK="$DST.aio-old-$$"; LOG="/tmp/aio_github_update.log"
: > "$LOG" 2>/dev/null || true
log(){ printf '%s\n' "[PanelAIO] $*" | tee -a "$LOG"; }
cleanup(){ rm -rf "$TMP" "$NEW" "$BOOT" 2>/dev/null || true; aio_release_lock; }
fail(){ log "ERROR: $1"; if [ -d "$BAK" ] && [ ! -d "$DST" ]; then mv "$BAK" "$DST" 2>/dev/null || true; fi; cleanup; trap - EXIT HUP INT TERM; exit 1; }
trap 'cleanup' EXIT HUP INT TERM
aio_acquire_lock plugin_update || fail "Another AIO update is already running."
rm -rf "$TMP" "$NEW" "$BAK" 2>/dev/null || true; mkdir -p "$EXTRACT" "$NEW" || fail "Cannot create staging directories."

# Preferred route: exactly the same IPK artifact that is distributed to users.
VERSION_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}/version.txt"
VERSION_FILE="$TMP/version.txt"
if aio_secure_download "$VERSION_URL" "$VERSION_FILE" 30 2 >/dev/null 2>&1; then
    VERSION=$(tr -d '\r\n ' < "$VERSION_FILE" 2>/dev/null || true)
else
    VERSION=""
fi
case "$VERSION" in
    ''|*[!0-9.]* ) VERSION="" ;;
esac
IPK_RUNNER=""
if [ -x "$DST/safe_ipk_install.sh" ] && [ -s "$DST/core/ipk_validator.py" ]; then
    IPK_RUNNER="$DST/safe_ipk_install.sh"
elif [ -n "$VERSION" ]; then
    # Bootstrap the same safe IPK validator for a completely fresh install.
    aio_secure_download "https://raw.githubusercontent.com/${REPO}/${BRANCH}/safe_ipk_install.sh" "$BOOT/safe_ipk_install.sh" 30 2 >/dev/null 2>&1 || true
    aio_secure_download "https://raw.githubusercontent.com/${REPO}/${BRANCH}/core/ipk_validator.py" "$BOOT/core/ipk_validator.py" 30 2 >/dev/null 2>&1 || true
    if [ -s "$BOOT/safe_ipk_install.sh" ] && [ -s "$BOOT/core/ipk_validator.py" ]; then
        chmod 700 "$BOOT/safe_ipk_install.sh" 2>/dev/null || true
        IPK_RUNNER="$BOOT/safe_ipk_install.sh"
    fi
fi
if [ -n "$VERSION" ] && [ -n "$IPK_RUNNER" ]; then
    IPK_NAME="enigma2-plugin-extensions-panelaio_${VERSION}_all.ipk"
    IPK_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}/release/${IPK_NAME}"
    STATUS="$TMP/ipk.status"
    log "Trying release IPK first: $IPK_NAME"
    if /bin/sh "$IPK_RUNNER" "$IPK_URL" '^enigma2-plugin-extensions-panelaio$' "$STATUS" >> "$LOG" 2>&1; then
        log "IPK update completed successfully: $VERSION"
        cleanup; trap - EXIT HUP INT TERM; exit 0
    fi
    log "Release IPK not available or failed validation; switching to source-recovery mode."
fi

# Recovery route: staged source installation. This remains only as a fallback.
URL1="https://github.com/${REPO}/archive/refs/heads/${BRANCH}.zip"; URL2="https://codeload.github.com/${REPO}/zip/refs/heads/${BRANCH}"
aio_secure_download "$URL1" "$ZIP" 600 3 || aio_secure_download "$URL2" "$ZIP" 600 3 || fail "Cannot download repository ZIP over HTTPS."
aio_not_html "$ZIP" || fail "HTML response received instead of ZIP."
aio_validate_archive "$ZIP" zip 100000 1073741824 >> "$LOG" 2>&1 || fail "Unsafe or damaged repository ZIP."
command -v unzip >/dev/null 2>&1 || fail "unzip is missing. Install it before running the source updater."
unzip -oq "$ZIP" -d "$EXTRACT" >> "$LOG" 2>&1 || fail "Cannot extract repository ZIP."
SRC=""
for D in "$EXTRACT/PanelAIO-Plugin-$BRANCH" "$EXTRACT/PanelAIO-Plugin-$BRANCH/AIO-Panel"; do [ -f "$D/plugin.py" ] && [ -f "$D/version.txt" ] && { SRC="$D"; break; }; done
if [ -z "$SRC" ]; then F=$(find "$EXTRACT" -type f -name plugin.py -print -quit 2>/dev/null); [ -n "$F" ] && SRC=$(dirname "$F"); fi
[ -n "$SRC" ] || fail "Plugin source root not found."
cp -pR "$SRC"/. "$NEW/" || fail "Cannot copy staged plugin."
rm -rf "$NEW/.git" "$NEW/.github" "$NEW/release" "$NEW/releases" "$NEW/control" "$NEW/packaging" "$NEW/tests" "$NEW/tools" 2>/dev/null || true
rm -f "$NEW/.gitattributes" "$NEW/.gitignore" "$NEW/build_ipk.sh" "$NEW/Picony.zip" "$NEW/SHA256SUMS.txt" "$NEW/PLIKI_DO_PODMIANY.txt" "$NEW/update.json" "$NEW/README.md" "$NEW/RELEASES.md" 2>/dev/null || true
rm -f "$NEW"/AIO_PANEL_*_ZMIANY.txt "$NEW"/AIO_PANEL_*_POPRAWKI.txt "$NEW"/AIO_PANEL_AWARYJNE_USUNIECIE.txt 2>/dev/null || true
rm -f "$NEW"/AIO_Panel_*_TEST_REPORT.txt "$NEW"/*_FIX_TEST_REPORT.txt "$NEW"/ARCHITECTURE_*.md "$NEW"/CHANNELS_FIX_TEST_REPORT.txt 2>/dev/null || true
rm -f "$NEW"/CHANNEL_INSTALL_FIX_*.txt "$NEW"/FIXES_*.txt "$NEW"/GITHUB_REPLACEMENT_INSTRUCTIONS.txt "$NEW"/LIST_ORDER_FIX_*.txt 2>/dev/null || true
rm -f "$NEW"/SUPERCONFIG_*.txt "$NEW"/SUPER_CONFIG_*.txt "$NEW"/UPDATE_ONLINE_FIX_*.txt 2>/dev/null || true
find "$NEW" -depth -type d -name __pycache__ -print 2>/dev/null | while IFS= read -r D; do rm -rf "$D" 2>/dev/null || true; done
find "$NEW" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true
for REQUIRED in plugin.py runtime.py legacy_plugin.py version.txt BUILD_ID.txt install_archive_script.sh picon_install_script.sh install_iptv_dream_safe.sh install_s4aupdater_safe.sh install_picon_updater_safe.sh install_myupdater_safe.sh aio_safe_common.sh core/logger.py core/result.py core/action_registry.py core/source_registry.py core/selftest.py ui/modern.py ui/screens/connect.py assets/modern/qr_site.png; do [ -s "$NEW/$REQUIRED" ] || fail "Missing required file: $REQUIRED"; done
PY=$(aio_python 2>/dev/null || true); [ -n "$PY" ] || fail "Python interpreter not found."
if "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info[0] >= 3 else 1)' >/dev/null 2>&1; then
    "$PY" -m compileall -q "$NEW" >> "$LOG" 2>&1 || fail "Python syntax validation failed."
else
    "$PY" -m py_compile "$NEW/plugin.py" "$NEW/runtime.py" "$NEW/legacy_plugin.py" "$NEW/ui/modern.py" "$NEW/ui/screens/connect.py" "$NEW/core/logger.py" "$NEW/core/result.py" "$NEW/core/action_registry.py" "$NEW/core/activity.py" "$NEW/core/source_registry.py" >> "$LOG" 2>&1 || fail "Python 2 compatibility syntax validation failed."
fi
find "$NEW" -type f -name '*.sh' -print 2>/dev/null | while IFS= read -r S; do /bin/sh -n "$S" >> "$LOG" 2>&1 || exit 1; done || fail "Shell syntax validation failed."
"$PY" "$NEW/core/selftest.py" "$NEW" >> "$LOG" 2>&1 || fail "AIO 16.0.0 self-test failed."
find "$NEW" -type f -name '*.sh' -exec chmod 755 {} \; 2>/dev/null || true
find "$NEW" -type f -name '*.py' -exec chmod 644 {} \; 2>/dev/null || true
find "$NEW" -type f -name '*.png' -exec chmod 644 {} \; 2>/dev/null || true
[ -d "$DST" ] && mv "$DST" "$BAK" || true
mv "$NEW" "$DST" || { [ -d "$BAK" ] && mv "$BAK" "$DST" 2>/dev/null || true; fail "Atomic activation failed."; }
[ -s "$DST/plugin.py" ] && [ -s "$DST/runtime.py" ] && [ -s "$DST/legacy_plugin.py" ] || { rm -rf "$DST" 2>/dev/null || true; [ -d "$BAK" ] && mv "$BAK" "$DST" 2>/dev/null || true; fail "Post-activation validation failed."; }
if [ -d "$OLD" ]; then rm -rf "$OLD.aio-legacy" 2>/dev/null || true; mv "$OLD" "$OLD.aio-legacy" 2>/dev/null || true; fi
rm -rf "$BAK" "$OLD.aio-legacy" 2>/dev/null || true
sync 2>/dev/null || true
log "Installed version: $(cat "$DST/version.txt" 2>/dev/null || echo unknown). Manual GUI restart is recommended after verification."
cleanup; trap - EXIT HUP INT TERM; exit 0
