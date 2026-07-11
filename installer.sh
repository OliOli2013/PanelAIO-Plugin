#!/bin/sh
# PanelAIO 14.0.0 - bezpieczna instalacja/aktualizacja z GitHuba dla Python 2/3
# Poprawka: BusyBox unzip na starszych obrazach/Python 2 wymaga wcześniejszego utworzenia katalogu -d.
set -e

REPO="OliOli2013/PanelAIO-Plugin"
BRANCH="main"
ZIP_PRIMARY="https://github.com/${REPO}/archive/refs/heads/${BRANCH}.zip"
ZIP_FALLBACK="https://codeload.github.com/${REPO}/zip/refs/heads/${BRANCH}"

BASE="/usr/lib/enigma2/python/Plugins"
DST="$BASE/SystemPlugins/PanelAIO"
OLD="$BASE/Extensions/PanelAIO"
TMP="/tmp/panelaio_github_update"
ZIP="$TMP/repo.zip"
EXTRACT="$TMP/extract"
SRC=""

download() {
    url="$1"
    out="$2"
    if command -v wget >/dev/null 2>&1; then
        wget -4 -U "Enigma2" -T 30 -t 3 -O "$out" "$url" && return 0
        wget -4 --no-check-certificate -U "Enigma2" -T 30 -t 3 -O "$out" "$url" && return 0
    fi
    if command -v curl >/dev/null 2>&1; then
        curl -L --ipv4 -A "Enigma2" --max-time 30 -o "$out" "$url" && return 0
        curl -L -k --ipv4 -A "Enigma2" --max-time 30 -o "$out" "$url" && return 0
    fi
    return 1
}

find_source_root() {
    base="$1"
    for d in \
        "$base" \
        "$base/AIO-Panel" \
        "$base/PanelAIO-Plugin-main" \
        "$base/PanelAIO-Plugin-main/AIO-Panel" \
        "$base/PanelAIO-Plugin-${BRANCH}" \
        "$base/PanelAIO-Plugin-${BRANCH}/AIO-Panel"
    do
        if [ -f "$d/plugin.py" ] && [ -f "$d/version.txt" ]; then
            echo "$d"
            return 0
        fi
    done
    found=$(find "$base" -type f -name plugin.py 2>/dev/null | head -n 1)
    if [ -n "$found" ]; then
        dirname "$found"
        return 0
    fi
    return 1
}

echo "[PanelAIO] Aktualizacja z GitHuba: ${REPO}/${BRANCH}"
rm -rf "$TMP"
mkdir -p "$TMP" "$EXTRACT"

if ! download "$ZIP_PRIMARY" "$ZIP"; then
    echo "[PanelAIO] Główny URL ZIP nie odpowiada, próbuję codeload..."
    download "$ZIP_FALLBACK" "$ZIP" || { echo "[PanelAIO] Nie udało się pobrać archiwum repozytorium."; exit 1; }
fi

if [ ! -s "$ZIP" ]; then
    echo "[PanelAIO] Pobrany plik ZIP jest pusty lub uszkodzony. Przerywam."
    exit 1
fi

if ! command -v unzip >/dev/null 2>&1; then
    echo "[PanelAIO] Brak unzip - instaluję pakiet unzip i próbuję ponownie..."
    opkg update >/dev/null 2>&1 || true
    opkg install unzip >/dev/null 2>&1 || true
fi

if ! command -v unzip >/dev/null 2>&1; then
    echo "[PanelAIO] Brak narzędzia unzip. Instalacja przerwana."
    echo "[PanelAIO] Uruchom ręcznie: opkg update && opkg install unzip"
    exit 1
fi

rm -rf "$EXTRACT"
mkdir -p "$EXTRACT" || { echo "[PanelAIO] Nie mogę utworzyć katalogu $EXTRACT"; exit 1; }

if ! unzip -oq "$ZIP" -d "$EXTRACT"; then
    echo "[PanelAIO] Błąd rozpakowywania ZIP. Czyszczę katalog i kończę instalację błędem."
    rm -rf "$TMP"
    exit 1
fi

SRC=$(find_source_root "$EXTRACT") || {
    echo "[PanelAIO] Nie znaleziono katalogu źródłowego pluginu w archiwum GitHub."
    exit 1
}

echo "[PanelAIO] Źródło: $SRC"
rm -rf "$DST.new"
mkdir -p "$DST.new"
cp -R "$SRC"/. "$DST.new/"

# Nie instaluj katalogów technicznych repozytorium na tunerze.
rm -rf "$DST.new/release" "$DST.new/releases" "$DST.new/control" "$DST.new/packaging" "$DST.new/.git" "$DST.new/.github" 2>/dev/null || true
find "$DST.new" -maxdepth 1 -type f \( -name "*.ipk" -o -name "build*.sh" -o -name "SHA256SUMS*" \) -delete 2>/dev/null || true

# Usuń starą lokalizację po dawnych paczkach Extensions/PanelAIO.
rm -rf "$OLD" 2>/dev/null || true

# Nie zostawiaj starych cache Pythona.
find "$DST" -type d -name __pycache__ -exec rm -rf {} \; 2>/dev/null || true
find "$DST" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true

rm -rf "$DST.bak" 2>/dev/null || true
[ -d "$DST" ] && mv "$DST" "$DST.bak" || true
mv "$DST.new" "$DST"
rm -rf "$DST.bak" 2>/dev/null || true

find "$DST" -type d -name __pycache__ -exec rm -rf {} \; 2>/dev/null || true
find "$DST" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true

find "$DST" -type f -name '*.sh' -exec chmod 755 {} \; 2>/dev/null || true
find "$DST" -type f -name '*.py' -exec chmod 644 {} \; 2>/dev/null || true
find "$DST" -type f -name '*.txt' -exec chmod 644 {} \; 2>/dev/null || true
find "$DST" -type f -name '*.png' -exec chmod 644 {} \; 2>/dev/null || true

rm -rf "$TMP" 2>/dev/null || true
sync || true

echo "[PanelAIO] Zainstalowano wersję $(cat "$DST/version.txt" 2>/dev/null || echo unknown)"
echo "[PanelAIO] Gotowe. Instalator nie wymusza restartu odbiornika."
echo "[PanelAIO] Zalecenie: wykonaj ręczny restart GUI lub pełny restart wtedy, gdy tuner działa stabilnie."

exit 0
