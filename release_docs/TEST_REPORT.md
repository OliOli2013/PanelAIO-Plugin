# Raport testów — AIO Panel 14.0.0 Full Repair

Data testów: 23 lipca 2026 r.

## Testy zakończone wynikiem pozytywnym

1. Kompilacja wszystkich modułów Python 3.
2. Kontrola składni wszystkich skryptów POSIX shell oraz skryptów `preinst`, `postinst` i `postrm`.
3. Walidacja poprawnego archiwum ZIP.
4. Odrzucenie archiwum z próbą wyjścia poza katalog docelowy.
5. Transakcyjna instalacja poprawnej listy kanałów.
6. Odrzucenie paczki bez wymaganej zawartości bez utraty starej listy.
7. Poprawny restore listy w katalogu izolowanym.
8. Odrzucenie uszkodzonego restore z zachowaniem dotychczasowych plików.
9. Instalacja piconów znajdujących się w zagnieżdżonym katalogu.
10. Odrzucenie dwóch różnych piconów o identycznej nazwie docelowej.
11. Odrzucenie zdalnego skryptu zawierającego pobieranie bezpośrednio do powłoki.
12. Odrzucenie nieszyfrowanego adresu HTTP w zdalnym instalatorze.
13. Kontrolowane przepisanie wyłącznie historycznego prefiksu Softcam z HTTP na HTTPS i pozytywna walidacja wyniku.
14. Pełny backup list kanałów wraz z plikami XML.
15. Backup wielu lokalizacji OSCam w izolowanym rootfs.
16. Restore OSCam z utworzonego backupu.
17. Sprawdzenie kompletnego pokrycia wszystkich 48 widocznych komend `CMD:` przez obsługujące je funkcje.
18. Brak surowych działań `bash_raw` w danych aktywnego menu.
19. Brak `--no-check-certificate`, `curl -k`, `CERT_NONE` i niezabezpieczonego kontekstu SSL w gotowym payloadzie.
20. Brak poleceń `wget/curl | sh` w gotowych skryptach.
21. Walidacja metadanych finalnego IPK:
    - pakiet: `enigma2-plugin-extensions-panelaio`,
    - wersja: `14.0.0`,
    - architektura: `all`.
22. Porównanie bitowe katalogu runtime z zawartością finalnego IPK.
23. Potwierdzenie braku `__pycache__`, `.pyc`, `.pyo`, kopii roboczych i dokumentów deweloperskich w IPK.
24. Ponowna kompilacja kodu i kontrola shell po rozpakowaniu finalnego IPK.

Wynik automatycznego zestawu regresji: `ALL_TESTS_PASSED`.

## Zakres, którego nie można było zasymulować w kontenerze

- fizyczne uruchomienie na wszystkich modelach tunerów;
- rzeczywiste GUI Enigma2 i renderowanie na każdym skinie SD/HD/FHD;
- pełny test pod interpreterem Python 2, którego nie ma w środowisku wykonawczym;
- zachowanie wszystkich zewnętrznych feedów i serwerów podczas awarii sieci;
- różnice między managerami Softcam każdego obrazu.

Z tego powodu nie można uczciwie zagwarantować absolutnych 100% zgodności z każdym istniejącym obrazem Enigma2. Pakiet został jednak zabezpieczony tak, aby błąd zewnętrzny kończył operację, pozostawiał log i — tam, gdzie zmieniane są dane użytkownika — uruchamiał rollback zamiast kontynuować destrukcyjną procedurę.
