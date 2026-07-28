#!/bin/sh
set -eu
VERSION=$(cat version.txt)
[ "$VERSION" = "15.0.0" ] || { echo "Unexpected version: $VERSION" >&2; exit 1; }
PKG="enigma2-plugin-extensions-panelaio_${VERSION}-r2_all.ipk"
WORK="/tmp/panelaio-build-$$"
OUT="$(pwd)/release/$PKG"
DST="$WORK/data/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO"
cleanup(){ rm -rf "$WORK"; }
trap cleanup EXIT HUP INT TERM
rm -rf "$WORK"
mkdir -p "$DST" "$WORK/control" "$(dirname "$OUT")"
# Copy the repository source as the runtime tree, then remove packaging-only data.
cp -a . "$DST/"
rm -rf "$DST/control" "$DST/release" "$DST/releases" "$DST/.git" "$DST/.github" "$DST/packaging" 2>/dev/null || true
rm -f "$DST"/*.ipk "$DST/build_ipk.sh" "$DST/SHA256SUMS.txt" "$DST/update.json" "$DST/PLIKI_DO_PODMIANY.txt" 2>/dev/null || true
find "$DST" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$DST" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true
for F in plugin.py legacy_plugin.py version.txt BUILD_ID.txt install_e2iplayer.sh ui/modern.py ui/screens/connect.py assets/modern/qr_site.png assets/modern/qr_community.png assets/modern/qr_report.png; do
    [ -s "$DST/$F" ] || { echo "Missing runtime file: $F" >&2; exit 1; }
done
cp control/control control/preinst control/postinst control/postrm "$WORK/control/"
chmod 755 "$WORK/control/preinst" "$WORK/control/postinst" "$WORK/control/postrm"
printf '2.0\n' > "$WORK/debian-binary"
(
  cd "$WORK/control"
  tar --owner=0 --group=0 -cJf "$WORK/control.tar.xz" control preinst postinst postrm
)
(
  cd "$WORK/data"
  tar --owner=0 --group=0 -cJf "$WORK/data.tar.xz" .
)
rm -f "$OUT"
(
  cd "$WORK"
  ar r "$OUT" debian-binary control.tar.xz data.tar.xz >/dev/null
)
chmod 644 "$OUT"
echo "Built: $OUT"
