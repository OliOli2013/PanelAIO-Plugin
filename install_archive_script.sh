#!/bin/sh

# Skrypt do instalacji archiwum listy kanałów lub piconów z Panelu AIO
# Argumenty: $1 - ścieżka do archiwum, $2 - typ archiwum (zip lub tar.gz)

ARCHIVE_PATH="$1"
ARCHIVE_TYPE="$2"
E2_DIR="/etc/enigma2"
PICONS_DIR="/usr/share/enigma2/picon" # Zakładamy domyślną ścieżkę picon

echo ">>> Rozpoczynam instalację archiwum: $ARCHIVE_PATH"
echo ">>> Typ archiwum: $ARCHIVE_TYPE"

# Sprawdzenie, czy plik istnieje
if [ ! -f "$ARCHIVE_PATH" ]; then
    echo "!!! BŁĄD: Plik archiwum nie istnieje: $ARCHIVE_PATH"
    exit 1
fi

# --- Sekcja czyszczenia STARYCH plików listy kanałów ---
# Wykonujemy tylko jeśli to NIE jest archiwum piconów
# Zakładamy, że archiwa picon mają 'picon' w nazwie (mało precyzyjne, ale powinno działać)
if ! echo "$ARCHIVE_PATH" | grep -qi "picon"; then
    echo "--> Wykryto instalację listy kanałów. Czyszczę stare pliki..."
    # Usuwamy pliki lamedb oraz wszystkie pliki bukietów
    # UWAGA: To usunie WSZYSTKIE bukiety, w tym te stworzone przez użytkownika!
    rm -f "$E2_DIR/lamedb" >> /tmp/aio_install.log 2>&1
    rm -f "$E2_DIR/lamedb5" >> /tmp/aio_install.log 2>&1
    rm -f "$E2_DIR/blacklist" >> /tmp/aio_install.log 2>&1
    rm -f "$E2_DIR/whitelist" >> /tmp/aio_install.log 2>&1
    rm -f "$E2_DIR/bouquets.tv" >> /tmp/aio_install.log 2>&1
    rm -f "$E2_DIR/bouquets.radio" >> /tmp/aio_install.log 2>&1
    rm -f "$E2_DIR/userbouquet.*.tv" >> /tmp/aio_install.log 2>&1
    rm -f "$E2_DIR/userbouquet.*.radio" >> /tmp/aio_install.log 2>&1
    echo "--> Zakończono czyszczenie."
else
    echo "--> Wykryto instalację piconów. Pomijam czyszczenie list kanałów."
fi
# --- Koniec sekcji czyszczenia ---


# Rozpakowywanie archiwum
echo "--> Rozpakowuję archiwum..."
if [ "$ARCHIVE_TYPE" = "zip" ]; then
    # Sprawdź czy to picony
    if echo "$ARCHIVE_PATH" | grep -qi "picon"; then
        echo "--> Rozpakowuję picony (zip) do $PICONS_DIR..."
        mkdir -p "$PICONS_DIR"
        unzip -o -q "$ARCHIVE_PATH" -d "$PICONS_DIR"
        # Dodatkowa logika przenoszenia, jeśli picony są w podkatalogu 'picon' w zipie
        if [ -d "$PICONS_DIR/picon" ]; then
            echo "--> Przenoszę picony z podkatalogu..."
            mv -f "$PICONS_DIR/picon/"* "$PICONS_DIR/" >> /tmp/aio_install.log 2>&1
            rmdir "$PICONS_DIR/picon" >> /tmp/aio_install.log 2>&1
        fi
    else
        echo "--> Rozpakowuję listę kanałów (zip) do $E2_DIR..."
        unzip -o -q "$ARCHIVE_PATH" -d "$E2_DIR"
    fi
elif [ "$ARCHIVE_TYPE" = "tar.gz" ]; then
     # Sprawdź czy to picony (mniej prawdopodobne dla tar.gz, ale dodajemy)
    if echo "$ARCHIVE_PATH" | grep -qi "picon"; then
        echo "--> Rozpakowuję picony (tar.gz) do $PICONS_DIR..."
        mkdir -p "$PICONS_DIR"
        tar -xzf "$ARCHIVE_PATH" -C "$PICONS_DIR"
        # Logika dla podkatalogu 'picon' w tar.gz (jeśli potrzebna)
        # Można dodać podobne sprawdzenie i mv jak dla zip
    else
        echo "--> Rozpakowuję listę kanałów (tar.gz) do $E2_DIR..."
        tar -xzf "$ARCHIVE_PATH" -C "$E2_DIR"
    fi
else
    echo "!!! BŁĄD: Nieznany typ archiwum: $ARCHIVE_TYPE"
    rm -f "$ARCHIVE_PATH" # Usuń pobrane archiwum w razie błędu
    exit 1
fi

# Sprawdzenie wyniku rozpakowania
if [ $? -eq 0 ]; then
    echo "--> Archiwum rozpakowane pomyślnie."
else
    echo "!!! BŁĄD: Wystąpił błąd podczas rozpakowywania archiwum."
    rm -f "$ARCHIVE_PATH" # Usuń pobrane archiwum w razie błędu
    exit 1
fi

# Usuń pobrane archiwum po udanym rozpakowaniu
echo "--> Usuwam pobrane archiwum..."
rm -f "$ARCHIVE_PATH"

echo ">>> Instalacja zakończona."
sleep 3 # Krótka pauza, aby użytkownik zdążył zobaczyć komunikat

exit 0
