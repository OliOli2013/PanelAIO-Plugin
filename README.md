# AIO Panel 10.0.3

Nowość: `aio_tips.txt`

Plik `aio_tips.txt` pozwala dodawać i edytować Tip dnia bez zmiany `plugin.py`.

## Format pliku

- plik UTF-8
- komentarze zaczynające się od `#` lub `;` są ignorowane
- użyj sekcji `[PL]` i `[EN]`
- jeden tip = jedna linia

## Przykład

```
[PL]
To jest przykładowy tip po polsku.

[EN]
This is an example tip in English.
```


## 10.0.3
Tip dnia otwiera się teraz w dedykowanym oknie AIO zamiast w systemowym MessageBox.
