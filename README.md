# AIO Panel 11.0

Ta paczka zawiera kompletną wersję repozytorium AIO Panel przygotowaną do publikacji na GitHubie oraz do budowy paczki IPK.

## Najważniejsze założenia wersji 11.0

- ujednolicone wersjonowanie całego projektu do `11.0`
- usunięte pozostałości po starszych wersjach z plików metadanych, README, ekranów i helperów
- poprawiona aktualizacja z GitHuba: instalator pobiera pełne drzewo repozytorium, a nie tylko wybrane pliki
- wzmocnione pobieranie danych repozytorium list kanałów: retry, fallback do cache i bardziej tolerancyjny parser manifestu
- zaktualizowany `aio_tips.txt` z zewnętrznego pliku użytkownika
- zachowana zgodność z Python 2 / Python 3 i dotychczasową logiką menu

## Układ repozytorium

- `plugin.py` — entry point
- `legacy_plugin.py` — pełna warstwa zgodności runtime
- `core/` — helpery systemowe, sieciowe i bezpieczeństwa
- `ui/` — ekrany i most do nowej architektury
- `data/` — menu, tłumaczenia i skiny
- `control/` — pliki do budowy IPK

## Ważne

Aktualizacja z GitHuba w wersji 11.0 pobiera i podmienia całe drzewo wtyczki, więc nie pomija katalogów `core`, `ui`, `data` ani plików pomocniczych.
