#!/bin/sh
# AIO Panel 15.0.0 - dedicated E2iPlayer installer/update wrapper.
# Keep this command identical to the command used over FTP/SSH.
URL="https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh"
LOG="/tmp/aio_e2iplayer_install.log"

: > "$LOG" 2>/dev/null || true

echo "[AIO Panel] E2iPlayer - instalacja/aktualizacja" | tee -a "$LOG"
echo "[AIO Panel] Źródło: $URL" | tee -a "$LOG"
if ! command -v wget >/dev/null 2>&1; then
    echo "[AIO Panel] BŁĄD: brak polecenia wget." | tee -a "$LOG" >&2
    exit 127
fi

# Exact working command:
wget -q "https://raw.githubusercontent.com/oe-mirrors/e2iplayer/refs/heads/python3/e2iplayer_install.sh" -O - | /bin/sh
RC=$?

if [ "$RC" -ne 0 ]; then
    echo "[AIO Panel] BŁĄD: instalator E2iPlayer zakończył się kodem $RC." | tee -a "$LOG" >&2
    exit "$RC"
fi

echo "[AIO Panel] E2iPlayer został zainstalowany lub zaktualizowany." | tee -a "$LOG"
exit 0
