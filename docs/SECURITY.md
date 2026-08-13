# Bezpieczeństwo AIO Panel 16.0.0

- zdalny skrypt nie jest uznawany za zaufany tylko dlatego, że pochodzi z GitHuba;
- generic `remote_script:` wymaga dokładnego wpisu w `core/source_registry.py`;
- dedykowane instalatory PiconUpdater, MyUpdater i IPTV Dream używają profili walidacji;
- skrypty są pobierane do `/tmp/PanelAIO`, sprawdzane jako tekst, hash SHA-256 trafia do logu, następnie wykonywany jest lokalny plik;
- S4aUpdater używa legacy HTTP — integralność transportu nie może być zagwarantowana; AIO ogranicza URL do dokładnego adresu wydawcy i blokuje najbardziej destrukcyjne operacje;
- instalacja list kanałów i restore wykorzystują staging/rollback;
- AIO Connect nie wysyła raportu automatycznie i maskuje pełny adres IP.
