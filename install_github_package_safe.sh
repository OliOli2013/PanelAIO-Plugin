#!/bin/sh
# AIO Panel: verified publisher packages mirrored in PanelAIO-Plugin/third_party.
# Installed on demand, never bundled inside AIO Panel IPK/DEB.
set -u
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
AIO_PLUGIN_DIR="$ROOT"
. "$ROOT/aio_safe_common.sh" || exit 1
KEY="${1:-}"
if command -v opkg >/dev/null 2>&1; then FORMAT=ipk
elif command -v dpkg >/dev/null 2>&1; then FORMAT=deb
else echo "AIO: no opkg/dpkg available" >&2; exit 1; fi
case "$KEY:$FORMAT" in
  jedi:ipk)
    PACKAGE='enigma2-plugin-extensions-jedimakerxtream'; VER='6.37.20240530'
    NAME='enigma2-plugin-extensions-jedimakerxtream_6.37_all.ipk'
    URL='https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/third_party/enigma2-plugin-extensions-jedimakerxtream_6.37_all.ipk'
    EXPECTED_SHA='0f83ff218885767aba50b978eba7b9c72a489f0bba0a1aa3c6ce73b3c8189ec5'
    ;;
  jedi:deb)
    PACKAGE='enigma2-plugin-extensions-jedimakerxtream'; VER='6.37-20240530'
    NAME='enigma2-plugin-extensions-jedimakerxtream_6.37_all.deb'
    URL='https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/third_party/enigma2-plugin-extensions-jedimakerxtream_6.37_all.deb'
    EXPECTED_SHA='2a3af502e34823ff5ee190a2c36b473603c25345cb79afe920b7f4e0c165f821'
    ;;
  chocho:ipk)
    PACKAGE='enigma2-plugin-extensions-chocholousek-picons'; VER='5.0.240904'
    NAME='enigma2-plugin-extensions-chocholousek-picons_5.0.240904_all.ipk'
    URL='https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/third_party/enigma2-plugin-extensions-chocholousek-picons_5.0.240904_all.ipk'
    EXPECTED_SHA='ed89bd4a4ac3b450585ff28ceb8d8a7ce263c47753f4d781f5304b4102daef86'
    ;;
  chocho:deb)
    PACKAGE='enigma2-plugin-extensions-chocholousek-picons'; VER='5.0.240904'
    NAME='enigma2-plugin-extensions-chocholousek-picons_5.0.240904_all.deb'
    URL='https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/third_party/enigma2-plugin-extensions-chocholousek-picons_5.0.240904_all.deb'
    EXPECTED_SHA='2587696ccb20e3b41c9cd933eae688071abaa32711adf0e7cd740f485878e8af'
    ;;
  *) echo "AIO: unsupported plugin/format" >&2; exit 2 ;;
esac
LOG='/tmp/aio_github_plugin_install.log'
FILE="/tmp/PanelAIO/${NAME%.$FORMAT}_$$.$FORMAT"
mkdir -p /tmp/PanelAIO || exit 1
: > "$LOG" || exit 1
cleanup(){ rm -f "$FILE"; aio_release_lock; }
trap cleanup EXIT HUP INT TERM
log(){ printf "[AIO Mirror] %s\n" "$*" | tee -a "$LOG"; }
fail(){ log "ERROR: $*"; tail -n 45 "$LOG" >&2; exit 1; }
aio_acquire_lock opkg || fail "another package operation is running"
log "Downloading mirrored publisher package: $NAME"
aio_secure_download "$URL" "$FILE" 180 3 >> "$LOG" 2>&1 || fail "download failed"
aio_not_html "$FILE" || fail "download returned HTML"
SUM=$(aio_sha256 "$FILE") || fail "cannot hash downloaded file"
[ "$SUM" = "$EXPECTED_SHA" ] || fail "SHA256 mismatch: mirror file differs from verified package"
PY=$(aio_python 2>/dev/null || true); [ -n "$PY" ] || fail "Python required for package validation"
META=$("$PY" "$ROOT/core/third_party_package_validator.py" "$FILE" "$PACKAGE" "$VER" 2>> "$LOG") || fail "package metadata rejected"
log "Verified: $META; SHA256: $SUM"
PV=$(printf "%s\n" "$META" | cut -d "|" -f3)
RC=0
if [ "$FORMAT" = ipk ]; then
  if [ "$KEY" = chocho ]; then
    opkg --force-reinstall --force-downgrade install "$FILE" >> "$LOG" 2>&1 || RC=$?
  else
    opkg --force-reinstall install "$FILE" >> "$LOG" 2>&1 || RC=$?
  fi
  INSTALLED=$(opkg list-installed "$PACKAGE" 2>/dev/null | awk -v p="$PACKAGE" '$1==p {print $3; exit}')
  STATE=$(opkg status "$PACKAGE" 2>/dev/null | awk -F': ' '$1=="Status" {print $2; exit}')
else
  dpkg -i "$FILE" >> "$LOG" 2>&1 || RC=$?
  INSTALLED=$(dpkg-query -W -f='${Version}' "$PACKAGE" 2>/dev/null || true)
  STATE=$(dpkg-query -W -f='${Status}' "$PACKAGE" 2>/dev/null || true)
fi
log "Package manager rc=$RC; installed version=$INSTALLED; state=$STATE"
[ "$INSTALLED" = "$PV" ] && [ "$STATE" = "install ok installed" ] || fail "installation not verified; see $LOG"
if [ "$RC" -ne 0 ]; then log "WARNING: package manager returned $RC, but package is installed and verified"; fi
log "SUCCESS: $PACKAGE $PV; restart Enigma2 GUI manually if required"
exit 0
