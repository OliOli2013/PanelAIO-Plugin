#!/bin/sh
# Reproducible AIO Panel IPK builder for Linux Mint / GitHub Actions.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VERSION=$(tr -d '\r\n ' < "$ROOT/version.txt")
PKG='enigma2-plugin-extensions-panelaio'
OUTDIR="$ROOT/release"
OUT="$OUTDIR/${PKG}_${VERSION}_all.ipk"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/panelaio-build.XXXXXX")
PLUGIN="$WORK/data/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO"
CONTROL="$WORK/control"
cleanup(){ rm -rf "$WORK"; }
trap cleanup EXIT HUP INT TERM
mkdir -p "$PLUGIN" "$CONTROL" "$OUTDIR"

# Copy repository source, then remove files which are repository/build-only.
(
  cd "$ROOT"
  tar -cf - \
    --exclude='./.git' --exclude='./.github' --exclude='./release' --exclude='./releases' \
    --exclude='./control' --exclude='./docs' --exclude='./tests' --exclude='./tools' \
    --exclude='./build_ipk.sh' --exclude='./README.md' --exclude='./RELEASES.md' \
    --exclude='./GITKRAKEN_16.0.0.txt' --exclude='./SHA256SUMS.txt' --exclude='./update.json' \
    --exclude='./Picony.zip' --exclude='./__pycache__' --exclude='*.pyc' --exclude='*.pyo' \
    .
) | tar -xf - -C "$PLUGIN"

cp -a "$ROOT/control/." "$CONTROL/"

# IPK should contain runtime assets, not repository metadata.
find "$PLUGIN" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$PLUGIN" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true
find "$PLUGIN" -type f -name '*.sh' -exec chmod 755 {} \;
find "$PLUGIN" -type f -name '*.py' -exec chmod 644 {} \;
find "$PLUGIN" -type f \( -name '*.png' -o -name '*.jpg' -o -name '*.json' -o -name '*.txt' -o -name 'LICENSE' \) -exec chmod 644 {} \; 2>/dev/null || true
chmod 755 "$CONTROL"/preinst "$CONTROL"/postinst "$CONTROL"/postrm 2>/dev/null || true
chmod 644 "$CONTROL"/control

# Validate the staged payload before packaging.
python3 -m compileall -q "$PLUGIN"
find "$PLUGIN" -type f -name '*.sh' -print0 | xargs -0 -n1 /bin/sh -n
python3 "$PLUGIN/core/selftest.py" "$PLUGIN"
find "$PLUGIN" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$PLUGIN" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true

# Build standard opkg/deb-format archives. AIO 15.x used xz and tested receivers accept it.
printf '2.0\n' > "$WORK/debian-binary"
(
  cd "$CONTROL"
  tar --owner=0 --group=0 -cJf "$WORK/control.tar.xz" .
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

[ -s "$OUT" ] || { echo 'Build failed: IPK is empty.' >&2; exit 1; }
if command -v sha256sum >/dev/null 2>&1; then
  HASH=$(sha256sum "$OUT" | awk '{print $1}')
else
  HASH=$(python3 - "$OUT" <<'PY'
import hashlib, sys
h=hashlib.sha256()
with open(sys.argv[1],'rb') as f:
    for chunk in iter(lambda:f.read(65536), b''):
        h.update(chunk)
print(h.hexdigest())
PY
)
fi
printf '%s  %s\n' "$HASH" "release/$(basename "$OUT")" > "$ROOT/SHA256SUMS.txt"
echo "Built: $OUT"
echo "SHA256: $HASH"
