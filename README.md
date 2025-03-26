# PACKIT 4.0

## Optymalizacja załadunku palet transportowych z wykorzystaniem metod uczenia maszynowego

Projekt mający na celu optymalizację procesu załadunku palet transportowych przy wykorzystaniu różnych algorytmów i metod uczenia maszynowego.

### Główne funkcjonalności

- Implementacja różnych algorytmów załadunku (XZ-Axis, X-Distribution, Z-Distribution)
- Zastosowanie uczenia ze wzmocnieniem do optymalizacji załadunku
- Wizualizacja 3D procesu załadunku z interaktywnym interfejsem
- Analiza efektywności przestrzennej różnych metod załadunku
- Weryfikacja i walidacja rozkładu masy oraz kolizji

### Instalacja

```bash
pip install -r requirements.txt
```

### Uruchomienie

```bash
python src/main.py
```

### Struktura projektu

- `src/` - kod źródłowy projektu
  - `algorithms/` - implementacje algorytmów załadunku
  - `models/` - modele uczenia maszynowego
  - `visualization/` - komponenty do wizualizacji 3D
  - `data/` - zarządzanie danymi
  - `utils/` - narzędzia pomocnicze
- `data/` - pliki danych
- `docs/` - dokumentacja
- `tests/` - testy 