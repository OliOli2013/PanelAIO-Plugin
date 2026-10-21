# 📺 AIO Panel 17.0.1 – Enigma2

**Aktualizacja: 21 października 2026 r.**  
**Autor: Paweł Pawełek | AIO Team**

AIO Panel to rozbudowane centrum narzędzi dla odbiorników Enigma2, umożliwiające wygodne zarządzanie listami kanałów, wtyczkami, skórkami, piconami, emulatorami oraz ustawieniami systemowymi.

Wersja **17.0.1** rozwija funkcjonalność wydania 17.0.0, wprowadzając nowe możliwości instalacji piconów oraz poprawki interfejsu i informacji o wtyczce.

## 🆕 Co nowego w wersji 17.0.1?

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

- Ujednolicono numer wersji 17.0.1 w plikach i metadanych.
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

- **[AIO Panel 17.0.1 – IPK](release/enigma2-plugin-extensions-panelaio_17.0.1_all.ipk)**
- **[AIO Panel 17.0.1 – DEB](release/enigma2-plugin-extensions-panelaio_17.0.1_all.deb)**

Wybierz pakiet zgodny z systemem i menedżerem pakietów odbiornika.

## ✅ Kontrola jakości

Przed publikacją przeprowadzono audyt statyczny wersji 17.0.1:

- **62 kontrole zakończone pomyślnie.**
- **0 błędów podczas audytu.**
- Potwierdzono integralność archiwów piconów.
- Zweryfikowano strukturę pakietów instalacyjnych.
- Potwierdzono działanie interfejsu na OpenATV z Pythonem 3.14.

Zgodność działania na wszystkich odbiornikach i starszych systemach Python 2 wymaga dalszej weryfikacji.

## 📌 Ważne

Wersja 17.0.1 nie zmienia działania Super Konfiguratora ani istniejących instalatorów. Jest aktualizacją funkcjonalną i techniczną względem wydania 17.0.0.

---

**AIO Panel – Wszystko w jednym miejscu dla Enigma2.**

**© AIO Team | Paweł Pawełek**
