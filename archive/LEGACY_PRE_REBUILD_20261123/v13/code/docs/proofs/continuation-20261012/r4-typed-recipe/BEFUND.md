# R4 Teil 5: Typisierte Werte + festes Rezept statt Körper wecken (2026-10-13, Thread K)

**Verdikt: CALC_SUPPORTED.** Vorregistrierung `preregistration.json` (sha256 `6c077592…`, Commit `84a58a3`, vor Seed 17), Bericht `report.json`.

**Aufbau.** Echte C3 LFM2.5-350M, R4-BENCH_CFG, Beobachter aus, keine Runtime-Änderung. Je Aufgabe: (1) normaler Runtime-Turn mit Ziffern-Unsicherheit, (2) eine feste BOOT-Regel (wie der Regex-Vorschlag in `toolstep.py`) wählt die Rechenart aus der Frage („how many … more … than“ → größter minus kleinster Wert, „total/sum“ → Summe, sonst nichts); C3 liest per JSON-Schema nur Name + Zahl je Posten; Zahlen-Wächter wie WP-W2 (jede Zahl als exaktes Token im Text); das Rezept rechnet und nennt größten/kleinsten Posten, (3) frischer Turn mit angehängtem exakten Ergebnis. Entwicklung in drei Runden nur auf Seed 7/11 (C3 wählte die Rechenart selbst unzuverlässig: immer „total“ oder immer „none“; deshalb die feste Regel).

**Frische Aufgaben (Seed 17, 60).**

| Politik | bestanden | summary | compare | Rezept benutzt | Zeit/Turn |
|---|---|---|---|---|---|
| C3 allein | 40 | 9 | 5 | 0 | 5,3 s |
| immer Rezept | **51** | 13 | **12** | 30 | 9,0 s |
| Rezept bei Unsicherheit (vorregistriert) | **50** | 13 | 11 | 24 | 8,2 s |

Gepaart gegen C3 allein: **11 gewonnen, 1 verloren, netto +10, Vorzeichentest p = 0,006**, keine Aufgabenart verliert → Kriterium erfüllt. Zum Vergleich R4 Teil 1 (Seed 7): Körper wecken (Heuristik) 0,53, immer A+B 0,58, C3 allein 0,68; hier 0,83–0,85.

**Lesart.**
1. C3 liest die Zahlen zuverlässig (frisch 29/30 richtige Rezeptwerte), kann aber weder rechnen noch die Rechenart wählen. Arbeitsteilung „Modell liest, festes Rezept rechnet“ (wie WP-W2 bei Budgets) wirkt auch hier.
2. Der Unsicherheits-Auslöser spart wenig (24 statt 30 Rezept-Turns) und kostet eine Aufgabe; die Schwelle liegt nahe „immer“. Für Rechenfragen ist „immer Rezept, wenn die Regel greift“ einfacher.
3. Verbleibender Fehler: C3 nennt trotz richtiger Differenz einmal die falsche Stadt.
4. Die Weck-Frage aus R4 ist damit beantwortet: für diese Aufgaben hilft ein lokales Werkzeug, Körper nicht.

**Grenzen.** Generierte englische Aufgaben mit festen Formulierungen; die Rechenart-Regel deckt genau diese Formulierungen ab (für andere Fragen greift sie nicht oder falsch). Ergebnis als angehängter Nutzertext statt TOOL_RESULT-Schicht, Cloud-CPU, kein Redmi. Keine Runtime-Änderung.

**Nächster Schritt (offen, Vorschlag).** In `toolstep.py` einen zweiten BOOT-Vorschlag „Rechenfrage über aufgezählte Werte“ mit C3-Werteauslese + Rezept als READ_LOCAL-Werkzeug (`calc`-Familie, Age-Recht wie heute) anlegen, SHADOW zuerst, mit anders formulierten und deutschen Fragen neu messen.

Reproduktion: `scripts/r4_typed_recipe.py capture|prereg|evaluate`, Tests `tests/test_r4_typed_recipe.py` (4).
