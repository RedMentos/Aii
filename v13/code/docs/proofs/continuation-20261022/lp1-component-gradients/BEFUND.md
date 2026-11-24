# WP-LP1 Befund: latenter Lernterm erreicht die Parameter, bringt aber keinen Nutzen

Lauf 2026-10-22, Linux-Cloud-CPU, vorregistriert (`PREREG.md`, Commit `c5e837a` vor dem Lauf). Master `LiquidAI/LFM2.5-350M`
(sha256 `1c9c77a4…`; AG6 vom 10.10. nutzte `9e6c6ccf…`, die HF-Revision hat sich seitdem geändert). 3 Arme × 3 Saaten,
je 30 Schritte, ~250 s je Lauf. Rohdaten `bench-results/lp1-component-gradients-20261022/` (`rows.jsonl`, `report.json`).

**Urteil laut Regel: `LP1_NO_ATTRIBUTABLE_GAIN`** (H1 erfüllt, H2 nicht).

| Arm (Summe 3 Saaten) | gelernt /24 | Umformulierung /18 | Fast-Fragen-Leck /15 (kleiner besser) | vergessen | KL zur Basis (Mittel) | latenter Kosinus nachher |
| --- | --- | --- | --- | --- | --- | --- |
| CE (+KL) | 24 | **14** | 11 | 0 | **.017** | .25 |
| JEPA_OK | 24 | 13 | 12 | 0 | .035 | .79 |
| JEPA_WRONG (falsches Ziel) | 24 | 13 | 10 | 0 | .041 | .75 |

- **H1 erfüllt:** der Term erreicht die LoRA-Parameter. Anteil am angewendeten Gradienten 8 % in Schritt 1, wächst auf
  19–23 % in Schritt 30 (alle 3 Saaten). Richtung zu CE anfangs gleich (Kosinus +.35), ab Schritt 20 entgegengesetzt (−.1 bis −.3).
- **H2 nicht erfüllt:** kein Gewinn bei Umformulierungen (13 vs 14 vs 13), Leck gleich, beide JEPA-Arme verdoppeln die Drift
  zur Basis (KL .017 → .035/.041).
- **Wichtigster Nebenbefund:** auch das **falsch zugeordnete** Ziel hebt den latenten Kosinus fast genauso (.25 → .75 statt .79).
  Der Kosinus misst also vor allem, dass sich die Zustände in eine gemeinsame Richtung bewegen, kaum die richtige Zuordnung.
  Er taugt nicht als Lernbeleg (bestätigt und verschärft GPTs Audit, PR #29).
- Grenzen: 8 Fakten, Master statt Q4-Pfad, Ziel = eingefrorener Mittelwert (kein Predictor, kein EMA). Gilt für diesen Term,
  nicht für den geplanten Body-JEPA-Pfad mit Predictor/Slow-Target.

Folgen: `jepa_weight` bleibt 0 im Live-Trainer. Für einen echten Body-JEPA-Test braucht es (a) ein Ziel, das die richtige
Zuordnung belohnt (z. B. kontrastiv gegen andere Items, oder Predictor + Slow-Target wie `predictor_worker.py`), (b) als
Messgröße Nutzen auf neuen Aufgaben, nie den Kosinus allein, (c) eine Drift-Grenze, weil der Term die Drift verdoppelt.
