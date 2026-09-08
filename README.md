# AIO Panel 16.0.2

Poprawka aktualizacji oscam.srvid/srvid2 i SoftCam.Key, pierwszej zakładki Listy kanałów oraz stałych komunikatów wykonywania operacji. Szczegóły: docs/POPRAWKI_16.0.2.txt.

# AIO Panel 16.0.1

Maintenance release based on 16.0.0. Existing third-party installer commands are preserved.

See `docs/AUDYT_16.0.1.md` and `docs/INSTALACJA_16.0.1.txt` for findings, validation scope and publication instructions.
Upload the replacement tree including `release/enigma2-plugin-extensions-panelaio_16.0.1_all.ipk` and `SHA256SUMS.txt` together. The updater requires an IPK and does not copy source over a failed package installation.

# AIO Panel 16.0.0

AIO Panel to zestaw narzędzi All-In-One dla odbiorników Enigma2. Wersja 16.0.0 jest stabilnym wydaniem opartym na przetestowanej linii 15.0.2 i porządkuje architekturę, aktualizacje, diagnostykę oraz bezpieczeństwo instalatorów.

## Instalacja

```sh
wget -q -O - https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh | /bin/sh
```

Instalator 16.0.0 działa również na tunerze bez wcześniejszej instalacji AIO Panel. Preferuje paczkę IPK z katalogu `release/`, a instalację źródłową wykorzystuje tylko jako ścieżkę awaryjną.

## Najważniejsze funkcje

- listy kanałów AIO i obsługa bezpiecznego rollbacku,
- Softcam/OSCam oraz Super Konfigurator,
- instalatory wtyczek i skórek,
- E2iPlayer, IPTV Dream, PiconUpdater, MyUpdater, S4aUpdater,
- AIO Connect i lokalny raport diagnostyczny,
- wyszukiwarka AIO, Ulubione, Ostatnio używane,
- Health Check źródeł,
- Stable/Test update channel,
- backup/restore list kanałów i Oscam,
- diagnostyka systemu, logi, usługi, cron i konserwacja AIO.

## Architektura 16.x

`plugin.py` pozostaje lekkim entry pointem Enigma2. Aktywny backend znajduje się w `runtime.py`, natomiast `legacy_plugin.py` istnieje wyłącznie dla zgodności starszych importów. Nowe akcje użytkowe są rejestrowane i kierowane przez moduły `core/` zamiast dalszego powiększania warstwy legacy.

## Bezpieczeństwo instalatorów

Zdalne instalatory są ograniczone do jawnego Trusted Source Registry. Dla wybranych instalatorów AIO pobiera skrypt do prywatnego pliku w `/tmp`, sprawdza odpowiedź i profil źródła, zapisuje SHA-256, a dopiero potem uruchamia skrypt. S4aUpdater jest świadomym wyjątkiem legacy HTTP i jest dodatkowo oznaczany ostrzeżeniem.

## Python

AIO Panel zachowuje kompatybilność z Python 2 dla istniejących funkcji legacy. Rozwój nowych modułów jest ukierunkowany na Python 3; funkcje wymagające Python 3 są ukrywane lub blokowane na starszych obrazach.

Autor: **Paweł Pawełek**  
Kontakt: `aio-iptv@wp.pl`
