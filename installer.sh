#!/bin/sh
# AIO Panel 16.0.2 package updater. Compatible with the 16.0.0 validator.
set -u
REPO='OliOli2013/PanelAIO-Plugin'
BRANCH="${1:-main}"
case "$BRANCH" in main|test) ;; *) echo 'Unsupported branch' >&2; exit 2 ;; esac
BASE="https://raw.githubusercontent.com/$REPO/$BRANCH"
DST='/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO'
PKG='enigma2-plugin-extensions-panelaio'
WORK=$(mktemp -d /tmp/aio-self-update.XXXXXX) || exit 1
LOG='/tmp/aio_github_update.log'
AIO_LOCK_DIR=''
cleanup() { rm -rf "$WORK"; if command -v aio_release_lock >/dev/null 2>&1; then aio_release_lock; fi; }
trap cleanup EXIT
trap 'exit 130' HUP INT TERM
fail() { printf '[AIO] ERROR: %s\n' "$1" | tee -a "$LOG" >&2; exit 1; }

# Always obtain current helpers, including when called by an older installed copy.
bootstrap_download() (
    B_URL="$1"; B_OUT="$2"
    if command -v wget >/dev/null 2>&1; then
        wget -q -T 30 -O "$B_OUT.part" "$B_URL" && [ -s "$B_OUT.part" ] && mv "$B_OUT.part" "$B_OUT" && exit 0
    fi
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL --connect-timeout 15 --max-time 60 -o "$B_OUT.part" "$B_URL" && [ -s "$B_OUT.part" ] && mv "$B_OUT.part" "$B_OUT" && exit 0
    fi
    exit 1
)
bootstrap_download "$BASE/aio_safe_common.sh" "$WORK/aio_safe_common.sh" || fail 'Cannot download update helper over HTTPS. Check date, CA certificates and network.'
/bin/sh -n "$WORK/aio_safe_common.sh" || fail 'Invalid helper'
AIO_PLUGIN_DIR="$WORK"
. "$WORK/aio_safe_common.sh" || fail 'Cannot load helper'
aio_acquire_lock plugin_update || fail 'Another AIO update is running'
: > "$LOG"
command -v opkg >/dev/null 2>&1 || fail 'This IPK update requires opkg. DreamOS/DEB needs its own package.'
mkdir -p "$WORK/core" || fail 'Cannot create staging directory'
for HELPER in core/ipk_validator.py; do
    aio_secure_download "$BASE/$HELPER" "$WORK/$HELPER" 30 2 >> "$LOG" 2>&1 || fail 'Cannot download package validator'
done
PY=$(aio_python) || fail 'Python is missing'
aio_secure_download "$BASE/version.txt" "$WORK/version.txt" 30 2 >> "$LOG" 2>&1 || fail 'Cannot download version'
VERSION=$(tr -d '\r\n ' < "$WORK/version.txt")
printf '%s' "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || fail 'Invalid version response'
NAME="${PKG}_${VERSION}_all.ipk"
# Keep the repository mirror in the replacement ZIP so releases are optional.
RELEASE="https://github.com/$REPO/releases/download/$VERSION/$NAME"
MIRROR="$BASE/release/$NAME"
if ! aio_secure_download "$MIRROR" "$WORK/update.ipk" 180 2 >> "$LOG" 2>&1; then
    aio_secure_download "$RELEASE" "$WORK/update.ipk" 180 2 >> "$LOG" 2>&1 || fail 'IPK missing in both repository mirror and GitHub Release'
fi
aio_secure_download "$BASE/SHA256SUMS.txt" "$WORK/SHA256SUMS.txt" 30 2 >> "$LOG" 2>&1 || fail 'Cannot download checksums'
EXPECTED=$(awk -v p="release/$NAME" '$2==p {print $1}' "$WORK/SHA256SUMS.txt")
[ "${#EXPECTED}" -eq 64 ] || fail 'Package checksum missing or ambiguous'
ACTUAL=$(aio_sha256 "$WORK/update.ipk") || fail 'Cannot hash package'
[ "$EXPECTED" = "$ACTUAL" ] || fail 'Checksum mismatch; repository publication may be incomplete. Retry later.'
META=$("$PY" "$WORK/core/ipk_validator.py" "$WORK/update.ipk" '^enigma2-plugin-extensions-panelaio$' 2>> "$LOG") || fail 'Invalid IPK'
[ "$META" = "OK|$PKG|$VERSION|all" ] || fail 'Package metadata does not match advertised version'
CURRENT=$(opkg list-installed "$PKG" 2>/dev/null | awk -v p="$PKG" '$1==p {print $3; exit}')
if [ -n "$CURRENT" ] && opkg compare-versions "$CURRENT" '>>' "$VERSION"; then
    fail 'Installed package is newer. Downgrade was not performed.'
fi
# Use the same operation lock as other AIO package installations.
UPDATE_LOCK="$AIO_LOCK_DIR"
AIO_LOCK_DIR=''
if ! aio_acquire_lock opkg; then
    AIO_LOCK_DIR="$UPDATE_LOCK"
    fail 'Another package operation is running'
fi
PACKAGE_LOCK="$AIO_LOCK_DIR"
cleanup() {
    rm -rf "$WORK"
    AIO_LOCK_DIR="$PACKAGE_LOCK"; aio_release_lock
    AIO_LOCK_DIR="$UPDATE_LOCK"; aio_release_lock
}
printf '[AIO] Installing %s\n' "$VERSION" | tee -a "$LOG"
# Do not fall through to a source copy after a package-manager failure.
# Such a copy would leave the package database inconsistent with installed files.
opkg install --force-reinstall "$WORK/update.ipk" >> "$LOG" 2>&1 || fail 'opkg failed; see /tmp/aio_github_update.log'
INSTALLED=$(opkg list-installed "$PKG" 2>/dev/null | awk -v p="$PKG" '$1==p {print $3; exit}')
[ "$INSTALLED" = "$VERSION" ] || fail 'Package database version did not change'
[ "$(cat "$DST/version.txt" 2>/dev/null)" = "$VERSION" ] || fail 'Installed files have wrong version'
"$PY" "$DST/core/selftest.py" "$DST" >> "$LOG" 2>&1 || fail 'Installed payload self-test failed'
printf '[AIO] Verified version %s. Restart Enigma2 GUI manually.\n' "$VERSION" | tee -a "$LOG"
exit 0
