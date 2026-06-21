# AIO Panel 13.0.0 Final

AIO Panel dla Enigma2 / Python 2 i Python 3.

## Najważniejsze zmiany 13.0.0 Final

- naprawa problemu ze skinem Algare FHD i podobnymi skinami: AIO nie używa już ryzykownego `MessageBox(enable_input=False)` przy zadaniach w tle,
- bezpieczny fallback dla okien MessageBox — jeśli skin nie potrafi narysować okna, wtyczka nie powinna wywalić Enigma2,
- poprawione funkcje Oscam: `oscam.dvbapi Poland`, czyszczenie `oscam.dvbapi`, `oscam.srvid/srvid2`, `SoftCam.Key` oraz czyszczenie hasła,
- wykrywanie realnego katalogu aktywnego Oscama z procesu `/proc/<pid>/cmdline` i parametru `-c`,
- zabezpieczenie dla Oscam jej@n / S4Updater — AIO przerywa operację, jeśli nie potrafi jednoznacznie wykryć katalogu konfiguracji,
- kopie bezpieczeństwa przed podmianą plików Oscam,
- dodany instalator `Oscam Levi45` w zakładce Softcamy,
- menu pokazuje prostą nazwę `Oscam Levi45` oraz wykryty numer lokalnej binarki Oscam.

## Instalacja IPK

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-panelaio_13.0.0_all.ipk
```

Po instalacji wykonaj ręcznie restart GUI lub pełny restart tunera.
