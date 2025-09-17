#!/bin/sh

echo "--- ROZPOCZYNAM PRZEŁADOWANIE BUKIETÓW (WERSJA ZAWANSOWANA) ---"

# Metoda 1: Użycie WGET (Web Interface)
echo "[Metoda 1] Próba przeładowania przez Web Interface..."
wget -qO - "http://127.0.0.1/web/servicelistreload?mode=0" >/dev/null 2>&1
WGET_STATUS_1=$?
wget -qO - "http://127.0.0.1/web/servicelistreload?mode=4" >/dev/null 2>&1
WGET_STATUS_2=$?

if [ "$WGET_STATUS_1" -eq 0 ] && [ "$WGET_STATUS_2" -eq 0 ]; then
    echo "[Metoda 1] SUKCES: Polecenia WGET wysłane pomyślnie."
    echo "--- ZAKOŃCZONO PRZEŁADOWANIE BUKIETÓW ---"
    exit 0
else
    echo "[Metoda 1] BŁĄD: Nie udało się połączyć z Web Interface (kody wyjścia: $WGET_STATUS_1, $WGET_STATUS_2)."
fi

# Metoda 2: Użycie DBUS (komunikacja systemowa) - jako fallback
if command -v dbus-send >/dev/null 2>&1; then
    echo "[Metoda 2] Próba przeładowania przez DBUS..."
    dbus-send --type=signal / org.openpli.Enigma2.reloadSettings
    DBUS_STATUS=$?
    if [ "$DBUS_STATUS" -eq 0 ]; then
        echo "[Metoda 2] SUKCES: Sygnał DBUS wysłany pomyślnie."
        echo "--- ZAKOŃCZONO PRZEŁADOWANIE BUKIETÓW ---"
        exit 0
    else
        echo "[Metoda 2] BŁĄD: Wystąpił problem z wysłaniem sygnału DBUS (kod wyjścia: $DBUS_STATUS)."
    fi
else
    echo "[Metoda 2] POMINIĘTO: Polecenie 'dbus-send' nie jest dostępne w systemie."
fi

echo "OSTRZEŻENIE: Żadna z metod automatycznego przeładowania list nie powiodła się."
exit 1
