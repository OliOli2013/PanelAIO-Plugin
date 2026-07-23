# Macierz realizacji audytu AIO Panel 14.0.0

| Nr | Problem z audytu | Stan po naprawie |
|---:|---|---|
| 1 | Softcam przez HTTP | Naprawiono: bootstrap HTTPS, dokładna zamiana starego prefiksu na HTTPS, walidacja, pin SHA-256; pozostałe HTTP blokowane. |
| 2 | Dowolny `install_cmd` ze zdalnego manifestu | Naprawiono: pole jest ignorowane/usuwane, komenda generowana lokalnie z allowlisty. |
| 3 | Restore może pozostawić GUI zatrzymane | Naprawiono: odłączony worker, trap, restart GUI po sukcesie i błędzie, rollback. |
| 4 | Nieweryfikowana kopia przed instalacją list | Naprawiono: liczba i kompletność backupu są sprawdzane przed usunięciem danych. |
| 5 | `preinst` kasuje działającą wersję | Naprawiono: brak kasowania w `preinst`; sprzątanie starej ścieżki dopiero po walidacji w `postinst`. |
| 6 | Callback ignoruje kod wyjścia | Naprawiono: strukturalny wynik z kodem, stdout/stderr i zatrzymaniem kolejki. |
| 7 | Niespójny Super Konfigurator | Naprawiono: spójne komunikaty, retry/anuluj, brak fałszywego restartu i sukcesu. |
| 8 | FULL zawsze instaluje picony do flasha | Naprawiono: wybór miejsca i kontrola pojemności. |
| 9 | Wyłączona walidacja TLS | Naprawiono: usunięto wszystkie niebezpieczne flagi i konteksty. |
| 10 | Bezpośrednie nadpisywanie `satellites.xml` | Naprawiono: HTTPS, `.new`, walidacja XML, backup, atomowy `mv`. |
| 11 | Kruche akcje M3U/BOUQUET | Naprawiono: kodowany payload JSON, walidacja i brak dynamicznego surowego shella. |
| 12 | Ciche błędy importu M3U | Naprawiono w krytycznej ścieżce: staging, jawny rezultat, backup i atomowy zapis. |
| 13 | Backup list nie obejmuje wszystkich zmienianych plików | Naprawiono: wspólny, kompletny zbiór list i XML. |
| 14 | Backup na niezamontowanym `/media/*` | Naprawiono w selektorze: wykrycie mountpointu; ścieżka własna jest jawnie oznaczona. |
| 15 | Podwójny plik backupu | Naprawiono: wskaźnik `.latest` zamiast pełnej kopii. |
| 16 | Sztywny backup/restore OSCam | Naprawiono: wiele lokalizacji i wykrycie parametru `-c`. |
| 17 | Niepełny restart OSCam | Naprawiono: wspólny kontroler kilku nazw i managerów. |
| 18 | Edycja ustawień podczas pracy GUI | Naprawiono: API konfiguracji Enigma2 i rollback aktywnego softcamu. |
| 19 | Ukryta instalacja zależności przy otwieraniu | Naprawiono: pytanie użytkownika, jedna operacja OPKG i kontrola wyniku. |
| 20 | Timery działają po zamknięciu ekranów | Naprawiono: `onClose`, `stop()` i guard zamkniętego ekranu. |
| 21 | Auto RAM nietrwały i używa `drop_caches` | Naprawiono: session-start, GC, wyłącznie własne pliki. |
| 22 | Monolityczny `legacy_plugin.py` | Ryzyko operacyjne usunięto przez wydzielenie wszystkich niebezpiecznych operacji; pełny podział GUI pozostawiono etapowy dla kompatybilności. |
| 23 | Martwe moduły | Ograniczono: nowe moduły bezpieczeństwa są aktywnie używane; kompatybilne wrappery pozostają. |
| 24 | Szerokie `except` maskują błędy | Naprawiono w operacjach krytycznych przez status/log/rollback; warstwa zgodności GUI nadal zawiera defensywne handlery. |
| 25 | Nazwa `extensions` i katalog `SystemPlugins` | Uporządkowano przez `Section: systemplugins` i `Provides`; nazwa pakietu zachowana dla aktualizacji istniejących instalacji. |
| 26 | Brak `postrm` | Naprawiono: bezpieczny `postrm` zachowujący dane użytkownika. |
| 27 | Zbyt szerokie czyszczenie `/tmp` | Naprawiono: tylko własne pliki AIO i limit wieku. |
| 28 | Smart Cleanup usuwa cudze logi/listy OPKG | Naprawiono: usunięto destrukcyjne cele. |
| 29 | Broken Plugin Cleaner usuwa wtyczki | Naprawiono: wyłącznie raport, bez automatycznego kasowania. |
| 30 | Widoczne hasło root | Naprawiono: maskowanie i plik 600. |
| 31 | Service Manager próbuje wiele usług | Naprawiono: wykrycie `LoadState=loaded` lub jednego skryptu init. |
| 32 | Ekrany zbyt szerokie dla SD | Naprawiono dla wskazanych ekranów przez adaptacyjne warianty. |
| 33 | Język nie jest zapisywany | Naprawiono: zapis konfiguracji PL/EN. |
| 34 | Niepełne tłumaczenia | Główne komunikaty GUI i błędy operacji są dwujęzyczne; techniczne logi skryptów zachowano jako diagnostyczne. |
| 35 | Picon rozpoznawany po tytule | Naprawiono: jawna akcja `picons:`. |
| 36 | Brak blokady instalatora piconów | Naprawiono: lock. |
| 37 | Nadpisanie zduplikowanych nazw piconów | Naprawiono: konflikt różnych plików zatrzymuje instalację. |
| 38 | Staging piconów może zapełnić flash | Naprawiono: wybór zapisywalnego systemu plików z wymaganym zapasem. |
| 39 | Brak wspólnych blokad operacji | Naprawiono: osobne locki dla OPKG, list, piconów, OSCam i aktualizacji. |
| 40 | Backup awaryjny pozostaje w `/tmp` | Naprawiono: trap i cleanup po sukcesie/błędzie. |
| 41 | Bezpieczeństwo zależne od BusyBox | Naprawiono: własny walidator wpisów ZIP/TAR przed użyciem narzędzi systemowych. |
| 42 | `core/executor.py` niezgodny z Python 2 | Naprawiono: fallback timeoutu oparty na `Timer`, bez wymogu `communicate(timeout=...)`. |
