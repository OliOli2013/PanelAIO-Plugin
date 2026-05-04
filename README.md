# AIO Panel 12.0.0

![Wersja](https://img.shields.io/badge/version-12.0.0-blue)
![Enigma2](https://img.shields.io/badge/platform-Enigma2-darkgreen)
![Python](https://img.shields.io/badge/python-2%20%2F%203-yellow)
![Licencja](https://img.shields.io/badge/license-GPL--3.0-lightgrey)

**AIO Panel** to wtyczka dla odbiorników **Enigma2**, przygotowana jako panel typu „wszystko w jednym” do obsługi list kanałów, softcamów, repozytoriów, narzędzi systemowych, aktualizacji, naprawy konfiguracji oraz dodatków dla różnych image/systemów Enigma2.

Wtyczka działa w środowiskach **Python 2** i **Python 3** oraz jest pakowana jako plik **IPK**.

---

## Najważniejsze funkcje

- instalacja i aktualizacja list kanałów,
- obsługa softcamów,
- dostęp do wtyczek online,
- konfigurator ustawień AIO Panel,
- narzędzia systemowe,
- feedy i repozytoria,
- naprawa oraz backup,
- skiny i skórki,
- informacje o systemie i aktualizacjach,
- sekcja AIO Extra,
- obsługa języka polskiego i angielskiego,
- zgodność z wieloma image Enigma2.

---

## Nowości w wersji 12.0.0

W wersji **12.0.0** dodano automatyczne premiowanie najnowszych list kanałów wybranych twórców.

Premiowani twórcy list:

- Bzyk83,
- Anom,
- Paweł Pawełek,
- JakiTaki,
- Fullkiler / Fullkiller,
- Koncior,
- Twarek,
- Conrado,
- Dominiko / Dominico.

### Automatyczne sortowanie list kanałów

Listy kanałów wymienionych twórców są wyświetlane na samej górze menu **Listy Kanałów** od najnowszej do najstarszej.

Mechanizm działa automatycznie: jeżeli twórca doda nowszą listę, wtyczka wykrywa datę z nazwy, wersji lub adresu URL i przenosi tę listę wyżej. Pozostałe listy kanałów nadal są dostępne, ale pojawiają się po listach premiowanych.

Celem tej zmiany jest promowanie aktywnych twórców i zachęcenie do częstszej aktualizacji list kanałów.

### Naprawa widoczności w menu tunera

Naprawiono opcję:

```text
Widoczność w menu tunera: ON/OFF
```

Opcja zapisuje teraz stan, odświeża etykietę ON/OFF w panelu oraz korzysta z dodatkowego fallbacku zapisu w pliku:

```text
/etc/enigma2/.panelaio_show_in_menu
```

---

## Instalacja IPK

Skopiuj paczkę IPK do katalogu `/tmp` w odbiorniku, a następnie wykonaj przez SSH:

```sh
opkg install /tmp/enigma2-plugin-extensions-panelaio_12.0.0_all.ipk
```

Po instalacji zrestartuj GUI Enigma2:

```sh
init 4
init 3
```

Na systemach korzystających z `systemd` można użyć:

```sh
systemctl restart enigma2
```

---

## Lokalizacja po instalacji

Wtyczka instaluje się w katalogu:

```text
/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO/
```

---

## Aktualizacja z GitHuba

Przy aktualizacji z repozytorium należy podmienić całe drzewo wtyczki, nie tylko pojedynczy plik `plugin.py`.

Nie pomijaj katalogów:

```text
core/
ui/
data/
```

oraz plików pomocniczych, takich jak:

```text
legacy_plugin.py
installer.sh
install_archive_script.sh
custom_updates.json
version.txt
```

---

## Układ repozytorium

```text
PanelAIO/
├── plugin.py                  # entry point wtyczki
├── legacy_plugin.py           # główna logika i zgodność runtime
├── version.txt                # numer wersji
├── changelog.txt              # lista zmian
├── custom_updates.json        # definicje aktualizacji niestandardowych
├── installer.sh               # skrypt instalacyjny
├── install_archive_script.sh  # instalacja archiwów i dodatków
├── update_satellites_xml.sh   # aktualizacja satellites.xml
├── core/                      # helpery systemowe, sieciowe i bezpieczeństwa
├── data/                      # menu, tłumaczenia i skiny
├── ui/                        # ekrany i warstwa UI
└── control/                   # pliki kontrolne do budowy IPK
```

---

## Zgodność

Wtyczka jest przygotowana do pracy na odbiornikach Enigma2 z obsługą:

- Python 2,
- Python 3,
- pakietów IPK,
- standardowej struktury pluginów Enigma2.

---

## Licencja

Projekt jest udostępniany na licencji **GPL-3.0**. Szczegóły znajdują się w pliku [`LICENSE`](LICENSE).

---

## Autor i kontakt

**AIO Panel**  
Autor / maintainer: **Paweł Pawełek**  
Kontakt: **aio-iptv@wp.pl**

---

## Wsparcie projektu

Jeżeli chcesz wesprzeć rozwój wtyczki, użyj kodu QR dostępnego w repozytorium lub w panelu wtyczki.

```text
(https://ko-fi.com/pawelpawlek)
[qr_support.png](https://buycoffee.to/pawelpawelek)
```

---

## Ważna informacja

AIO Panel wykonuje operacje systemowe oraz pobiera zewnętrzne pliki, listy i dodatki. Używaj wtyczki świadomie i zawsze wykonuj kopię zapasową konfiguracji odbiornika przed większymi zmianami.
