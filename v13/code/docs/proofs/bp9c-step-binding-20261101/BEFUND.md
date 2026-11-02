# WP-BP9c BEFUND: Gewicht pro Quelle bindet das Update mit SGD: `BP9c_PASS` (mit klarer Einschränkung)

Vorregistrierung `PREREG.md` (vor den Gruppen-Messungen; Kalibrierung auf dem vollen Batch, Seed 91, `bench-results/bp9b-step-binding-20261101/pilot-full-batch-seed91.json`). Roh: `bench-results/bp9b-step-binding-20261101/bp9c-seed{1,2,3}.json`.
Echter Körper B1, 3 Seeds, 16 Fakten je Seed (Mensch, Ergebnis, Eigen richtig, Eigen FALSCH, je 4), 30 Schritte, SGD lr 0,01 Momentum 0,9, Kontrolle AdamW 5e-4. Mittel über 3 Seeds:

| Arm | falsches Eigen-Etikett übernommen | Mensch+Ergebnis richtig | Eigen richtig | Allgemeinfragen | Nah-Fehlgriff (Leck) |
|---|---|---|---|---|---|
| uniform_sgd | **0,92** | 1,00 | 1,00 | .94 | .60 |
| typed_sgd | **0,00** | .92 | **0,00** | .96 | **.29** |
| typed_adamw | 0,92 | 1,00 | 1,00 | .98 | .60 |

Kriterien: K1 Schutz (typed_sgd <= uniform_sgd - 0,30): 0,00 gegen 0,92 -> erfüllt. K2 Kosten (Mensch+Ergebnis >= uniform - 0,10 und >= 0,8): .92 gegen 1,00 -> erfüllt (ein Mensch-Fakt in 2 von 3 Seeds nicht gelernt). K3 Optimierer zählt (typed_adamw >= typed_sgd + 0,20): 0,92 -> erfüllt. K4 Behalten: .96 gegen .94 -> erfüllt.
Urteil nach Regel: **`BP9c_PASS`**.

## Was es zeigt (und was nicht)
- Bestätigt die Vermutung aus BP9a: AdamW rechnet das kleine Gewicht wieder hoch (typed_adamw = uniform), mit SGD bindet das Gewicht.
- **Einschränkung:** Mit Gewicht .06 lernt SGD in 30 Schritten GAR keine Eigen-Etiketten (richtig 0,00, falsch 0,00). Das ist kein Unterscheiden von richtig und falsch, sondern ein Ausschluss der ganzen Eigen-Quelle, bezahlt mit den richtigen Eigen-Etiketten und einem Mensch-Fakt (.75 in zwei Seeds). Das passt zum BP9a-Befund (Weglassen der Quelle schützt), nur dass das Gewicht es jetzt ohne Quote leistet.
- Nebenbefund (nicht vorregistriert): Nah-Fehlgriff sinkt von .60 auf .29, wie beim Weglassen der Eigen-Quelle in BP9a.
- Aussage über den Bauplan: Getippte Einzelgewichte wirken nur mit einem Optimierer, der die Gewichtsgröße behält (SGD). Der Alltagstrainer nutzt AdamW; `sample_modulation` bleibt aus. Ein Einbau braucht SGD (oder eine Gewichts-Bindung im Optimierer) plus Prüfung auf Q4, Vergessen, Lernrate (Rate lag nahe an der Divergenzgrenze: lr 0,05 zerstörte den Gleich-Gewicht-Arm).
- Offen, neue Vorregistrierung nötig: Eigen-Etiketten, die teils richtig, teils falsch sind, mit einem Gewicht, das sie nicht komplett ausschließt (z. B. .2-.3), und der Trennung richtig/falsch über Selbstkonsistenz.
Grenzen: erfundene Fakten, Eigen-Gruppe zu 100 % falsch in der Falsch-Gruppe, 3 Seeds, ein Körper, fp32, kein Handy, SGD-Rate eng.
