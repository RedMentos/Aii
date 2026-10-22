# WP-Z6a Vorregistrierung: §24.23 Adaptive Reasoning Effort mit echten Modellen

Geschrieben und committet **vor** dem ersten Lauf (2026-10-22, Thread „Offene Ziel-Pakete Z6 bis Z12“).

## Frage
§24.23 verlangt den Vergleich fixed low / fixed medium-high / fixed max / adaptive / user-forced und misst
Quality-Cost-Pareto, Unterdenken bei schweren Aufgaben, Überdenken bei leichten, Body-Wakes und Kalibrierung der
Eskalation. Bisher nur Existenz-Tests (`test_effort`). R4 (12.10.) hatte nur C3 allein / immer A+B / Heuristik.

## Aufbau
Echte Modelle (C3 LFM2.5-350M, B1/B2 aus `config/models.json`, llama.cpp b10964), echte `Runtime`, Bench-Modus
wie WP-T3b/R4 (`utility_bench2.BENCH_CFG`: Temperatur 0, 600 s Frist, 180 s Beobachter), frisches Home je Arm,
RECORD_ONLY, keine History. Aufgaben: `utility_bench2.tasks(seed=23)` — 60 Aufgaben (4 Arten × 15), **frischer Seed**
(R4 nutzte 7 und 11). Arme = `effort.set_mode` vor dem ersten Turn: `disabled` (0, C-nativ), `low` (.15),
`adaptive` (ausgelieferte Heuristik, Standard), `high` (.70), `max` (.95, = user-forced). Je Turn: bestanden (Regex wie
WP-T3b), Turnzeit, Body-Angebote, EffortDecision (Band, Wake, Effort).

## Kriterien (Z6A_EFFORT_ADAPTIVE_PASS nur wenn A1–A3 gelten, sonst Z6A_EFFORT_ADAPTIVE_FAIL mit Angabe)
- A1 nicht dominiert: kein fester Arm mit mehr bestandenen Aufgaben (Vorzeichentest auf ungleichen Paaren p < 0,05) **und**
  mittlerer Turnzeit ≤ adaptive.
- A2 kein Verlust gegen den billigsten Weg: adaptive besteht nicht signifikant weniger als `disabled` (Vorzeichentest p < 0,05).
- A3 wenig Überdenken: von den Aufgaben, die `disabled` besteht, weckt adaptive in ≤ 50 % einen Body.
Beschreibend (ohne Schwelle): Unterdenken = Aufgaben, die adaptive nicht besteht, `max` aber schon, und bei denen adaptive
niedriger eskaliert als max; Eskalations-Kalibrierung = Anteil der adaptive-Wakes, bei denen `disabled` scheitert und
`max` besteht; Pass/Zeit je Art; Bänder je Arm.

## Grenzen (vorab)
Generierte englische Aufgaben, Regex auf der Endantwort, ein Seed, Cloud-CPU (Zeiten nur relativ, keine Energie).
Ein FAIL bleibt FAIL; keine nachträgliche Schwelle.
