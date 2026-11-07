# AIO Panel 18.0.0 — informacje o wydaniu

Data: 7 listopada 2026 r.
Autor: Paweł Pawełek | AIO Team

## Najważniejsze zmiany

- Stabilizacja mechanizmu aktualizacji wyłącznie SAT na bazie pozytywnie przetestowanego r3. Zachowywane są lokalne usługi DVB-T/T2, DVB-C, własne FAVOURITES, IPTV, nazwy i numeracja kanałów; walidacja i automatyczne wycofanie przy błędach.
- Nowa zakładka **Moje projekty** bezpośrednio pod **Listy kanałów** (PL/EN), zawierająca wszystkie 10 projektów oprogramowania Enigma2 z konta `OliOli2013` (w tym AIO Panel i AIOHD NEXT).
- Brak powtórzeń instalatorów tych projektów w innych zakładkach.
- OSCam Levi45: wersja źródłowa z aktualnego instalatora GitHub (11968 / Emu r803 według stanu na 7.11.2026); wersja lokalna tunera nie jest już błędnie prezentowana jako najnowsza.
- OSCam-Emu z feedu: wersja dostępna w feedzie tunera jest pokazywana osobno.
- AIO Connect raportuje aktualną wersję wtyczki zamiast stałego `17.0.3`.
- Ochrona instalatorów wtyczek wymagających Python 3 na starszych systemach Python 2.

## Projekty w nowej zakładce

AIO Panel, IPTV Dream, MyUpdater, PiconUpdater, Simple IPTV EPG, NeoRadio, PP Channel Sync, E2 Doctor, AIOHD NEXT Skin, OpenCamView.

Strona `aio-iptv-projekt` i repozytorium `PanelAIO-Lists` nie są wtyczkami; lista kanałów pozostaje w osobnej zakładce.

## Testy i ograniczenia

- Potwierdzono składnię wszystkich 46 plików Python bez generowania bytecode.
- Test własny AIO Panel przeszedł.
- Testy PL/EN dla nowej zakładki potwierdzają pozycję nr 2, 10 unikatowych pozycji i brak duplikatów.
- Instalatory repozytoriów sprawdzono na GitHub; weryfikacja nie jest testem ich instalacji na fizycznym odbiorniku.
- Przetestowano budowanie IPK oraz DEB, metadane, skrypty instalacyjne i zgodność zawartości pakietów.
- Nie przeprowadzono testu GUI na rzeczywistym tunerze ani wykonawczego testu Python 2.

Przed wdrożeniem na większą liczbę tunerów zalecana instalacja na jednym Ustym 4K Pro oraz odbiorniku z DPKG.
