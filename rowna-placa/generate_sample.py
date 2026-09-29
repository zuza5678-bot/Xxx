"""Generuje przykładowe dane (data.json) dla narzędzia Równa Płaca."""
import json, random

random.seed(2026)

CRITERIA = [
    # id, grupa, nazwa, max pkt, opis
    ("wiedza", "Umiejętności", "Wiedza i wykształcenie", 150, "Poziom wiedzy specjalistycznej i kwalifikacji wymaganych na stanowisku."),
    ("doswiadczenie", "Umiejętności", "Doświadczenie", 100, "Okres praktyki potrzebny do samodzielnej pracy."),
    ("interpersonalne", "Umiejętności", "Umiejętności interpersonalne", 100, "Komunikacja, negocjacje, obsługa trudnych rozmów, empatia."),
    ("umyslowy", "Wysiłek", "Wysiłek umysłowy", 100, "Złożoność problemów, koncentracja, analiza."),
    ("fizyczny", "Wysiłek", "Wysiłek fizyczny", 50, "Dźwiganie, praca w ruchu, pozycja wymuszona."),
    ("ludzie", "Odpowiedzialność", "Za ludzi", 150, "Kierowanie, koordynacja i rozwój innych osób."),
    ("zasoby", "Odpowiedzialność", "Za finanse i zasoby", 100, "Budżet, mienie, sprzęt, dane."),
    ("decyzje", "Odpowiedzialność", "Za decyzje i ich skutki", 100, "Wpływ błędu na klienta, firmę, bezpieczeństwo."),
    ("srodowisko", "Warunki pracy", "Środowisko pracy", 75, "Hałas, temperatura, zmianowość, zagrożenia."),
    ("psychiczne", "Warunki pracy", "Obciążenie psychiczne", 75, "Presja czasu, kontakt z trudnym klientem, stres."),
]
KEYS = [c[0] for c in CRITERIA]

# id, nazwa, dział, poziomy (10 kryteriów), nK, nM, stawka bazowa, współczynnik K, udział zmiennych
POSITIONS = [
    ("s01", "Specjalista / Specjalistka ds. obsługi klienta", "Obsługa klienta", [2,2,4,2,1,1,1,2,2,4], 6, 2, 6200, 1.00, 0.05),
    ("s02", "Magazynier / Magazynierka", "Logistyka", [1,2,1,1,5,1,2,2,4,2], 1, 6, 5600, 0.98, 0.06),
    ("s03", "Operator / Operatorka wózka widłowego", "Logistyka", [2,2,1,2,4,1,3,3,4,2], 0, 5, 7300, 1.00, 0.06),
    ("s04", "Księgowy / Księgowa", "Finanse", [4,3,2,4,1,1,4,3,1,3], 5, 1, 8600, 1.00, 0.04),
    ("s05", "Specjalista / Specjalistka ds. kadr i płac", "HR", [4,3,4,3,1,1,3,3,1,3], 4, 1, 8200, 1.00, 0.04),
    ("s06", "Programista / Programistka", "IT", [5,3,2,5,1,1,2,3,1,3], 1, 6, 13500, 0.90, 0.05),
    ("s07", "Tester / Testerka QA", "IT", [4,3,2,4,1,1,1,3,1,3], 2, 2, 8000, 0.97, 0.04),
    ("s08", "Handlowiec B2B", "Sprzedaż", [3,3,5,3,2,1,4,3,2,4], 2, 4, 9000, 0.96, 0.28),
    ("s09", "Koordynator / Koordynatorka logistyki", "Logistyka", [3,4,3,3,2,3,3,3,2,4], 2, 2, 9800, 0.93, 0.06),
    ("s10", "Kierownik / Kierowniczka zmiany", "Produkcja", [3,4,4,3,3,4,3,4,3,4], 1, 3, 11200, 0.97, 0.10),
    ("s11", "Pracownik / Pracownica produkcji", "Produkcja", [1,1,1,2,5,1,2,2,4,3], 4, 8, 5300, 0.97, 0.06),
    ("s12", "Asystent / Asystentka zarządu", "Zarząd", [3,3,4,2,1,1,2,2,1,3], 3, 0, 6600, 1.00, 0.03),
    ("s13", "Kierownik / Kierowniczka działu finansów", "Finanse", [5,5,4,4,1,5,5,5,1,4], 1, 2, 17500, 0.95, 0.12),
    ("s14", "Analityk / Analityczka danych", "IT", [5,3,3,5,1,1,2,4,1,3], 2, 2, 11500, 0.98, 0.05),
]

def r50(x):
    return int(round(x / 50.0) * 50)

employees = []
n = 1
for pid, name, dept, lv, nk, nm, base, fk, var in POSITIONS:
    for sex, cnt in (("K", nk), ("M", nm)):
        for _ in range(cnt):
            tenure = round(random.uniform(0.5, 14), 1)
            b = base * (1 + 0.012 * tenure) * random.gauss(1, 0.035) * (fk if sex == "K" else 1.0)
            v = b * var * random.uniform(0.6, 1.3) * (0.85 if sex == "K" and var > 0.2 else 1.0)
            fte = 1.0
            if random.random() < (0.18 if sex == "K" else 0.05):
                fte = random.choice([0.5, 0.75])
            employees.append({
                "id": f"P-{n:03d}", "pos": pid, "sex": sex,
                "base": r50(b * fte), "variable": r50(v * fte), "fte": fte, "tenure": tenure,
            })
            n += 1
random.shuffle(employees)
employees.sort(key=lambda e: e["id"])

data = {
    "version": 1,
    "sample": True,
    "company": {"name": "Przykładowa Sp. z o.o.", "headcount": 182, "zus": 20.48,
                 "threshold": 5, "bands": [0, 400, 500, 600, 700, 800]},
    "criteria": [{"id": c[0], "group": c[1], "name": c[2], "max": c[3], "desc": c[4]} for c in CRITERIA],
    "positions": [{"id": p[0], "name": p[1], "dept": p[2], "levels": dict(zip(KEYS, p[3]))} for p in POSITIONS],
    "employees": employees,
    "notes": {
        "3": {"status": "review", "text": "Rynkowa premia dla programistów: do udokumentowania raportem płacowym, sama różnica rynkowa nie usprawiedliwia luki wewnątrz stanowiska."}
    },
    "checklist": {"widelki": True, "nazwy": True},
}
out = json.dumps(data, ensure_ascii=False, indent=1)
open("data.json", "w", encoding="utf-8").write(out)
print(len(employees), "pracowników")
