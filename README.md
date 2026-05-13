# AIO Panel 12.0.2

AIO Panel dla Enigma2 / Python 2 i Python 3. Wersja 12.0.2 zachowuje zmiany z 12.0.1, ale usuwa ryzyko bootloopa podczas startu GUI na części image, szczególnie OpenATV 8 / beta.

## Najważniejsza poprawka 12.0.2

- odchudzono `plugin.py`, aby podczas startu Enigma2 nie ładował całej warstwy runtime `legacy_plugin.py`,
- pełna logika AIO Panel jest teraz ładowana dopiero po ręcznym otwarciu wtyczki,
- menu AIO Panel i `sessionstart` działają lekko i bezpiecznie podczas bootowania,
- Auto RAM Cleaner nadal może odtworzyć ustawienie po restarcie bez importowania całego panelu,
- dodano bezpieczny komunikat błędu, jeśli runtime wtyczki nie uruchomi się po wejściu do AIO Panel,
- zaktualizowano metadane do wersji 12.0.2.

## Zachowane zmiany z 12.0.1

- usunięto dublowanie list Bzyk83, JakiTaki,
- listy tych autorów są pobierane tylko z jednego repozytorium,
- ukryto listy kanałów starsze niż 2026,
- zachowano sortowanie list od najnowszej do najstarszej,
- dodano instalator Bouquet Maker Xtream,
- poprawiono działanie Backup List Kanałów,
- poprawiono działanie Restore Listy Kanałów,
- backup obejmuje pełne pliki list: `lamedb`, `lamedb5`, `bouquets.tv`, `bouquets.radio`, `userbouquet.*`,
- Restore czyści stare listy i przywraca pełną kopię,
- dodano informację o dostępnej aktualizacji AIO Panel na dole ekranu,
- dodano podgląd listy zmian przed aktualizacją,
- dodano wybór TAK/NIE przy aktualizacji, bez wymuszania instalacji,
- dodano funkcję Czyszczenie niedziałających wtyczek,
- czyszczenie usuwa uszkodzone wtyczki z systemu,
- poprawiono widoczność wtyczki na skinach Infinity Neo i MyMetrix-neo,
- poprawiono czytelność zaznaczonej funkcji w menu,
- poprawiono kolory, tła i warstwy ekranu wtyczki,
- uzupełniono opisy funkcji po polsku i angielsku,
- uzupełniono dolne informacje, co robi dana funkcja,
- dodano automatyczne przeładowanie list kanałów po instalacji bez wymuszania restartu GUI.

## Instalacja z IPK

```sh
opkg remove enigma2-plugin-extensions-panelaio
opkg install /tmp/enigma2-plugin-extensions-panelaio_12.0.2_all.ipk
reboot
```

## Aktualizacja z GitHuba

```sh
wget -qO- https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh | /bin/sh
```

## Struktura repozytorium

- `plugin.py` — lekki i bezpieczny entry point ładowany przy starcie Enigma2,
- `legacy_plugin.py` — pełna logika AIO Panel ładowana dopiero po otwarciu wtyczki,
- `core/`, `ui/`, `data/` — moduły architektury AIO,
- `installer.sh` — aktualizacja z GitHuba.
