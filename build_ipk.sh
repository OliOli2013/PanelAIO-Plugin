#!/bin/sh
# AIO Panel 18.0.0 — release builder for GitKraken/Linux.
# Creates real OPKG-compatible .ipk and dpkg-compatible .deb packages.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VERSION=$(tr -d '\r\n ' < "$ROOT/version.txt")
[ "$VERSION" = 18.0.0 ] || { echo 'Expected AIO Panel 18.0.0' >&2; exit 1; }
PKG=enigma2-plugin-extensions-panelaio
OUTDIR="$ROOT/release"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/panelaio18-build.XXXXXX")
cleanup(){ rm -rf "$WORK"; }
trap cleanup EXIT HUP INT TERM
DST="$WORK/ipk/data/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO"
mkdir -p "$DST" "$WORK/ipk/control" "$OUTDIR"
for d in assets core data ui; do
    [ -d "$ROOT/$d" ] || { echo "Missing $d" >&2; exit 1; }
    cp -a "$ROOT/$d" "$DST/$d"
done
for F in "$ROOT"/*.py "$ROOT"/*.sh "$ROOT"/*.png "$ROOT"/*.jpg "$ROOT"/*.txt "$ROOT"/*.json "$ROOT"/LICENSE "$ROOT"/oscam.dvbapi.poland; do
    [ -f "$F" ] || continue
    N=$(basename "$F")
    case "$N" in
        SHA256SUMS.txt|TEST_*|AIO_18*|GITKRAKEN_*|build_ipk.sh|build_deb.sh) continue ;;
    esac
    cp -a "$F" "$DST/$N"
done
cp -a "$ROOT/control/." "$WORK/ipk/control/"
find "$DST" -type d -name __pycache__ -prune -exec rm -rf {} \; 2>/dev/null || true
find "$DST" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true
find "$DST" -type f -name '*.sh' -exec chmod 755 {} \;
find "$DST" -type f -name '*.py' -exec chmod 644 {} \;
chmod 755 "$WORK/ipk/control"/preinst "$WORK/ipk/control"/postinst "$WORK/ipk/control"/postrm
[ "$(sed -n 's/^Version: //p' "$WORK/ipk/control/control")" = "$VERSION" ] || { echo 'Control/version mismatch' >&2; exit 1; }
python3 "$DST/core/python_syntax_check.py" "$DST"
find "$DST" -type f -name '*.sh' -exec sh -n {} \;
python3 "$DST/core/selftest.py" "$DST"
if [ -f "$ROOT/tests/test_release_18.py" ]; then
    python3 "$ROOT/tests/test_release_18.py" "$ROOT"
fi
if [ -n "${AIO_TEST_PYTHON2:-}" ]; then
    "$AIO_TEST_PYTHON2" "$DST/core/python_syntax_check.py" "$DST"
    "$AIO_TEST_PYTHON2" "$DST/core/selftest.py" "$DST"
fi
printf '2.0\n' > "$WORK/ipk/debian-binary"
( cd "$WORK/ipk/control"; tar --owner=0 --group=0 -czf "$WORK/ipk/control.tar.gz" . )
( cd "$WORK/ipk/data"; tar --owner=0 --group=0 -czf "$WORK/ipk/data.tar.gz" . )
OUT_IPK="$OUTDIR/${PKG}_${VERSION}_all.ipk"
( cd "$WORK/ipk"; ar r "$OUT_IPK" debian-binary control.tar.gz data.tar.gz >/dev/null )
# Build canonical dpkg DEB with the same installed payload and lifecycle scripts.
[ -x "$(command -v dpkg-deb || true)" ] || { echo 'dpkg-deb is required to build .deb' >&2; exit 1; }
mkdir -p "$WORK/deb/DEBIAN"
chmod 755 "$WORK/deb/DEBIAN"
cp -a "$WORK/ipk/data/." "$WORK/deb/"
cp -a "$WORK/ipk/control/." "$WORK/deb/DEBIAN/"
chmod g-s "$WORK/deb/DEBIAN"
chmod 755 "$WORK/deb/DEBIAN"
chmod 755 "$WORK/deb/DEBIAN"/preinst "$WORK/deb/DEBIAN"/postinst "$WORK/deb/DEBIAN"/postrm
OUT_DEB="$OUTDIR/${PKG}_${VERSION}_all.deb"
dpkg-deb --build "$WORK/deb" "$OUT_DEB" >/dev/null
( cd "$ROOT"; sha256sum "release/$(basename "$OUT_IPK")" "release/$(basename "$OUT_DEB")" > SHA256SUMS.txt )
echo "Built: $OUT_IPK"
echo "Built: $OUT_DEB"
cat "$ROOT/SHA256SUMS.txt"
