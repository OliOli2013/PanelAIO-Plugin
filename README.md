# AIO Panel 10.0.3

[10.0.3]
- Poprawiono okno "Tip dnia AIO": zamiast systemowego MessageBox otwiera się dedykowane okno AIO.
- Usunięto licznik timeout z tytułu typu "Informacje (12)", który był widoczny na części skinów.
- Dodano wygodniejszy odczyt wskazówek: OK/EXIT zamyka, LEFT/RIGHT przełącza tipy, UP/DOWN przewija dłuższy tekst.
- Zmiana ma charakter UI-only i nie ingeruje w mechanikę instalacji ani pozostałe funkcje wtyczki.

[10.0.2]
Data wydania: 05.04.2026
- Dodano zewnętrzny plik aio_tips.txt do obsługi funkcji "Tip dnia AIO" bez ingerencji w plugin.py.
- Dodano parser sekcji [PL]/[EN] z bezpiecznym fallbackiem do tipów wbudowanych.
- Dodano startowy zestaw przykładowych tipów dla użytkowników.
- Zaktualizowano installer.sh, aby pobierał nowy plik aio_tips.txt z repozytorium.

[10.0.1]
Data wydania: 05.04.2026
- Hotfix dla instalatorów uruchamianych w oknie Console (m.in. TV Garden, XStreamity i inne pozycje bash_raw).
- Usunięto błąd modalny po zamknięciu Console: „Modal open are allowed only from a screen which is modal!”.
- Okno pytania o pełny restart po instalacji otwierane jest teraz z bezpiecznym opóźnieniem po całkowitym zamknięciu Console.
- Sama instalacja wtyczek przebiegała poprawnie już wcześniej; poprawka dotyczy komunikatu końcowego i stabilności GUI po instalacji.
