# AIO Panel 13.0.2

Poprawka zachowująca numer wersji **13.0.2** dla ciągłości GitHub.

## Ważne

Ta paczka bazuje bezpośrednio na działającej poprawce 13.0.4.  
Nie cofnięto mechanizmu instalacji list kanałów.

## Zmiany

- Zachowano działające pobieranie i instalację list kanałów.
- Dodano automatyczne przeładowanie list kanałów/bukietów po udanej instalacji.
- Dodano odświeżenie przez `eDVBDB`, aktywny `servicelist` oraz lokalne `servicelistreload` przez wget/curl.
- Numer wersji pozostaje 13.0.2.

## Instalacja

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-panelaio_13.0.2_all.ipk
```
