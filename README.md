# AIO Panel 12.0.0

Ta paczka zawiera kompletną wersję repozytorium AIO Panel przygotowaną do publikacji na GitHubie oraz do budowy paczki IPK.

## Najważniejsze zmiany wersji 12.0.0

- dodano automatyczne premiowanie list kanałów twórców: Bzyk83, Anom, Paweł Pawełek, JakiTaki, Fullkiler/Fullkiller, Koncior, Twarek, Conrado i Dominiko/Dominico
- premiowane listy są pokazywane na górze od najnowszej do najstarszej na podstawie daty wykrytej w nazwie, wersji lub URL
- pozostałe listy kanałów pozostają w menu po premiowanych pozycjach
- naprawiono akcję „Widoczność w menu tunera (ON/OFF)” — komenda jest teraz obsługiwana, zapisuje stan i odświeża etykietę ON/OFF w panelu
- zachowana zgodność z Python 2 / Python 3 oraz dotychczasową logiką instalacji archiwów, bukietów M3U/REF i narzędzi systemowych

## Układ repozytorium

- `plugin.py` — entry point
- `legacy_plugin.py` — pełna warstwa zgodności runtime
- `core/` — helpery systemowe, sieciowe i bezpieczeństwa
- `ui/` — ekrany i most do nowej architektury
- `data/` — menu, tłumaczenia i skiny
- `control/` — pliki do budowy IPK

## Ważne

Aktualizacja z GitHuba pobiera i podmienia całe drzewo wtyczki, więc nie pomija katalogów `core`, `ui`, `data` ani plików pomocniczych.
