#!/bin/sh
set -e
VERSION=$(cat version.txt)
PKG="enigma2-plugin-extensions-panelaio_${VERSION}_all.ipk"
WORK="/tmp/panelaio-build-$$"
OUT="$(pwd)/$PKG"
DST="$WORK/data/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO"
mkdir -p "$DST" "$WORK/control"
cp -a . "$DST/"
rm -rf "$DST/control" "$DST/releases" "$DST/.git" "$DST/.github"
find "$DST" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$DST" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true
rm -f "$DST"/*.ipk "$DST"/build_ipk.sh "$DST"/SHA256SUMS.txt "$DST"/update.json
cp control/control control/preinst control/postinst "$WORK/control/"
printf '2.0\n' > "$WORK/debian-binary"
( cd "$WORK/control" && tar --owner=0 --group=0 -czf "$WORK/control.tar.gz" control preinst postinst )
( cd "$WORK/data" && tar --owner=0 --group=0 -czf "$WORK/data.tar.gz" . )
( cd "$WORK" && ar r "$OUT" debian-binary control.tar.gz data.tar.gz >/dev/null )
rm -rf "$WORK"
echo "Built: $PKG"
