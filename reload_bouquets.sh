#!/bin/sh
set -e
echo "--- Przeładowywanie list kanałów (reload_bouquets.sh) ---"

# Metoda 1: Poprzez OpenWebIF (preferowana, jeśli WebIF jest aktywny)
if command -v wget >/dev/null 2>&1; then
    echo "DEBUG (reload_bouquets): Próbuję przeładować przez OpenWebIF (mode=2)..."
    if wget -q -O - 'http://127.0.0.1/web/servicelistreload?mode=2' > /dev/null; then
        echo "Listy kanałów przeładowane przez OpenWebIF (tryb 2)."
        exit 0
    elif wget -q -O - 'http://127.0.0.1/web/servicelistreload?mode=0' > /dev/null; then # Fallback na inny tryb
        echo "Listy kanałów przeładowane przez OpenWebIF (tryb 0)."
        exit 0
    else
        echo "OSTRZEŻENIE (reload_bouquets): Przeładowanie przez OpenWebIF nie powiodło się."
    fi
else
    echo "OSTRZEŻENIE (reload_bouquets): Narzędzie 'wget' niedostępne, nie można użyć OpenWebIF."
fi

# Metoda 2: Poprzez SIGHUP do Enigma2 (bardziej bezpośrednia)
if command -v killall >/dev/null 2>&1; then
    echo "DEBUG (reload_bouquets): Próbuję wysłać SIGHUP do enigma2..."
    if killall -SIGHUP enigma2; then
       echo "Wysłano SIGHUP do enigma2 w celu przeładowania list."
       exit 0
    else
        echo "BŁĄD (reload_bouquets): Nie udało się wysłać SIGHUP do enigma2."
    fi
else
    echo "OSTRZEŻENIE (reload_bouquets): Narzędzie 'killall' niedostępne, nie można wysłać SIGHUP."
fi

echo "KRYTYCZNY BŁĄD (reload_bouquets): Nie udało się automatycznie przeładować list kanałów znanymi metodami."
echo "Może być konieczny restart GUI lub dekodera."
exit 1
