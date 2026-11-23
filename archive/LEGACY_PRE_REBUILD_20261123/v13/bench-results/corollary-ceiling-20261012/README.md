# Kandidat: Corollary-Zuordnung mit Toleranz-Obergrenze (Thread L, 2026-10-12) — **FAIL**

Skript `code/scripts/corollary_ceiling_candidate.py`, Vorregistrierung `preregistration.json` (Commit `d3f40c6`, vor dem Lauf gepusht), Rohdaten `report.json`.
Idee: `selfmodel.attribute` bleibt unverändert; ein MIXED-Ergebnis mit Abweichung > K × Toleranz wird zu EXTERNAL. `selfmodel.py` nicht geändert.

K auf Kalibrier-Saaten 101–105 gewählt: Balanced Accuracy 4 → .724, 6 → .839, 8 → .849, 12 → .864, **20 → .917** (gewählt).

| Test-Saaten 13–17 | Balanced Acc. | fremd → MIXED | eigener Fehlschlag verpasst |
|---|---|---|---|
| Standard, unverändert | .767 | .606 | .049 |
| Standard, Kandidat K=20 | **.903** | **0** | .248 |
| Stress (Fehlschläge bis 40×), unverändert | .766 | .606 | .053 |
| Stress, Kandidat K=20 | .787 | **0** | **.596** |

Kriterien: (1) 5/5 ✓, (2) 5/5 auf beiden Strömen ✓, (3) Anstieg verpasster Fehlschläge .54 > .10 ✗ und 2/5 Saaten schlechter ✗ → **FAIL**, nicht integrieren.

Befund:
- Die Obergrenze beseitigt die Fehlzuordnung fremder Ereignisse vollständig, verliert aber echte eigene Fehlschläge.
- **Auch im Standard-Strom** (Fehlschläge höchstens 6× Toleranz) gehen 25 % der Fehlschläge verloren. Ursache in `attribute`: Bei mehreren offenen eigenen Aktionen auf demselben Kanal wird die Abweichung gegen den **ersten** Kandidaten gerechnet, nicht gegen die nächstliegende Vorhersage. Die Abweichung ist dann groß, obwohl die passende Aktion nur knapp verfehlt hat.
- Folge: Vor jeder Obergrenze muss `attribute` die Abweichung gegen die nächstliegende offene Vorhersage rechnen. Erst dann ist eine Obergrenze messbar. Beides als neuer Kandidat getrennt vorregistrieren.
