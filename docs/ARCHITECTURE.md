# AIO Panel 16.0.0 — architektura

## Warstwy

1. `plugin.py` — lekki punkt wejścia Enigma2, konfiguracja minimalna i zadania startowe.
2. `ui/` — interfejs HD/FHD/compact i AIO Connect.
3. `core/action_dispatcher.py` + `core/action_registry.py` — routing i metadane nowych akcji.
4. `core/` — logowanie, walidacja, sieć, bezpieczeństwo, wyniki, stan aktywności i źródła.
5. `runtime.py` — kompatybilny backend istniejących, przetestowanych workflow.
6. `legacy_plugin.py` — wyłącznie shim kompatybilności starszych importów.

Nowe funkcje nie powinny być dopisywane bezpośrednio do `legacy_plugin.py`. Jeśli nowa funkcja nie wymaga ścisłego sprzężenia z istniejącym backendem, powinna trafiać do `core/`, `services/` lub `ui/` i być rejestrowana w dispatcherze.
