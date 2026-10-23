# 📺 AIO Panel 17.0.2 – Enigma2

**Aktualizacja: 23 października 2026 r.**
**Autor: Paweł Pawełek | AIO Team**

AIO Panel to rozbudowane centrum narzędzi dla odbiorników Enigma2, umożliwiające wygodne zarządzanie listami kanałów, wtyczkami, skórkami, piconami, emulatorami oraz ustawieniami systemowymi.

Wersja **17.0.2** naprawia instalację E2iPlayer i walidację składni Pythona, zachowując funkcje wersji 17.0.1.

## 🔧 Naprawy w wersji 17.0.2

- Instalator E2iPlayer najpierw sprawdza feed systemowy, a w razie awarii stosuje kontrolowaną instalację z oficjalnego archiwum oe-mirrors.
- Walidacja składni w `postinst` i instalatorach archiwów nie wymaga `compileall` ani `py_compile`.
- Przełączanie instalacji z zachowaniem poprzedniej wersji w razie błędu.

## Funkcje odziedziczone z 17.0.1

### 🖼️ Nowy wybór zestawów piconów

Dodano możliwość wyboru jednego z trzech zestawów:

- **Hot Bird 13°E** – picony satelitarne wraz z piconami IPTV.
- **Astra 19.2°E** – zestaw piconów dla satelity Astra.
- **Hot Bird 13°E + Astra 19.2°E** – wspólny zestaw piconów satelitarnych.

Po wybraniu zestawu użytkownik może wskazać katalog docelowy instalacji.

Dotychczasowa obsługa piconów w Super Konfiguratorze pozostaje bez zmian.

### 🎨 Nowa skórka Obsidian FHD

Dodano **Obsidian FHD** do sekcji „Skórki”, umożliwiając jej instalację bezpośrednio z poziomu AIO Panel.

### ℹ️ Poprawione informacje o wtyczce

- Naprawiono wyświetlanie historii aktualizacji (changelog).
- Zaktualizowano adres projektu w interfejsie.
- Odświeżono kody QR do strony, społeczności AIO i zgłaszania problemów.
- Usunięto nieaktualne oznaczenia.

### 🔧 Poprawki techniczne

- Ujednolicono numer wersji 17.0.2 w plikach i metadanych.
- Poprawiono kontrolę poprawności budowania pakietów IPK/DEB.
- Zachowano działające instalatory, Super Konfigurator oraz dotychczasową strukturę menu.
- Zachowano polską i angielską wersję interfejsu.

## 📥 Aktualizacja i instalacja

### 🔵 Aktualizacja z obecnej wersji

1. Uruchom **AIO Panel** na odbiorniku Enigma2.
2. Naciśnij **niebieski przycisk na pilocie – „Aktualizacja”**.
3. Potwierdź aktualizację i wykonuj instrukcje wyświetlane na ekranie.

### 📦 Instalacja ręczna

Można również pobrać i zainstalować odpowiedni pakiet:

- **[AIO Panel 17.0.2 – IPK](release/enigma2-plugin-extensions-panelaio_17.0.2_all.ipk)**
- **[AIO Panel 17.0.2 – DEB](release/enigma2-plugin-extensions-panelaio_17.0.2_all.deb)**

Wybierz pakiet zgodny z systemem i menedżerem pakietów odbiornika.

## ✅ Kontrola jakości

Poniższe wyniki dotyczą wcześniejszego audytu 17.0.1 (wersja 17.0.2 wymaga testów na tunerach):

- **62 kontrole zakończone pomyślnie.**
- **0 błędów podczas audytu.**
- Potwierdzono integralność archiwów piconów.
- Zweryfikowano strukturę pakietów instalacyjnych.
- Potwierdzono działanie interfejsu na OpenATV z Pythonem 3.14.

Zgodność działania na wszystkich odbiornikach i starszych systemach Python 2 wymaga dalszej weryfikacji.

## 📌 Ważne

Wersja 17.0.2 zmienia instalator E2iPlayer i mechanizm walidacji składni. Super Konfigurator i pozostałe funkcje nie były modyfikowane.

---

**AIO Panel – Wszystko w jednym miejscu dla Enigma2.**

**© AIO Team | Paweł Pawełek**
