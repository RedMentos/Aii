# WP-Z6a Befund: §24.23 Effort-Modi — `Z6A_EFFORT_ADAPTIVE_FAIL`

Vorregistriert in `PREREG.md` (inkl. Nachtrag vor dem Hauptlauf). Skript `code/scripts/z6a_effort_bench.py`,
Daten `v13/bench-results/z6a-effort-20261022/` (z6a.json, run.log). 60 Aufgaben (utility_bench2, Seed 23,
summary/long/notes/compare je 15), Bench-Dekodierung deterministisch, Cloud-CPU, ein Seed.

| Modus | bestanden/60 | Zeit bis FINAL (Mittel) | Body geweckt | Band |
|---|---|---|---|---|
| disabled | 42 | 2,38 s | 0 % | DIRECT_C_NATIVE |
| low | 42 | 2,37 s | 0 % | DIRECT_C_NATIVE |
| adaptive | 39 | 6,60 s | 100 % | FOCAL_TARGETED |
| high | 33 | 6,51 s | 100 % | FOCAL_TARGETED |
| max | 35 | 15,19 s | 100 % | DEEP_FOCAL |

Kriterien:
- A1 adaptive nicht dominiert: **PASS** (kein Modus ist zugleich besser und schneller).
- A2 kein Verlust gegen disabled: **PASS** (Vorzeichentest 10:7, p = 0,63; 42 vs. 39 liegt im Rauschen).
- A3 wenig Überdenken (adaptive weckt auf ≤ 50 % der Aufgaben, die disabled schon besteht): **FAIL, 42/42 = 100 %**.

Urteil: **`Z6A_EFFORT_ADAPTIVE_FAIL`**. FAIL bleibt FAIL.

Deutung: „adaptive“ ist auf diesen Aufgaben nicht adaptiv. Es weckt in 60/60 Turns einen Körper (immer
`FOCAL_TARGETED`), kostet 2,8-mal so viel Zeit und gewinnt nichts. Nur 4 der 60 Weckungen waren nötig (Aufgabe
von disabled nicht, von adaptive schon gelöst; Kalibrierung 6,7 %). Mehr Aufwand hilft hier nicht: high und max
sind schlechter als disabled (compare 3–4 vs. 5). Der Grund liegt vor dem Effort-Modus: das Band wird aus der
Aufgabenart gewählt, nicht aus einer Unsicherheit der eigenen C3-Antwort. Unterdenken (disabled besteht, adaptive
nicht) in 6 Aufgaben: summary06/11/13, notes03/05/08.

Nächster Schritt (neu vorregistrieren, nicht Teil dieses Urteils): adaptive weckt nur, wenn ein Signal aus dem
C3-Entwurf (Prüfer-Fail, Unsicherheit aus R4-Teil 3) es verlangt; dieselben 60 Aufgaben plus frischer Seed.
Grenzen: generierte englische Aufgaben, Regex-Prüfung, ein Seed, Cloud statt Redmi (Handy-Zeiten fehlen).
