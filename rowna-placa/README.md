# Równa Płaca

Narzędzie HR do przygotowania firmy na jawność wynagrodzeń (dyrektywa UE 2023/970, nowelizacja Kodeksu pracy z 24.12.2025):

- **Wartościowanie stanowisk**: 10 kryteriów w 4 grupach (umiejętności, wysiłek, odpowiedzialność, warunki pracy), skala 1–5, punkty → kategorie pracy o jednakowej wartości.
- **Luka płacowa K/M**: ogółem i w kategoriach (średnia, mediana, tylko zasadnicze), kwartyle płac, linia polityki płacowej.
- **Kategorie**: statusy i uzasadnienia luk ≥ 5%.
- **Pracownicy**: edycja i import CSV (`id;stanowisko;plec;zasadnicze;zmienne;etat;staz`), wskaźnik wynagrodzenia do mediany kategorii.
- **Widełki**: przedziały do ogłoszeń z gotowym tekstem.
- **Wyrównanie**: koszt zamknięcia luki (miesięcznie, rocznie z ZUS) i lista podwyżek.
- **Obowiązki**: terminy, obowiązek raportowania wg liczby pracowników, lista kontrolna.

Pliki: `src.html` (strona), `data.json` (dane), `generate_sample.py` (dane przykładowe), `build.py` (składa `index.html`).
