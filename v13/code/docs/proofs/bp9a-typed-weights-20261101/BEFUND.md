# WP-BP9a BEFUND: typisierte Einzelgewichte an einem echten Update: `BP9a_FAIL` (Gewichte allein reichen nicht, Weglassen wirkt)

Vorregistrierung `PREREG.md` (Commit 972f31b78, vor jeder Zahl). Roh: `bench-results/bp9a-typed-weights-20261101/bp9a-seed{1,2,3}.json`.
Aufbau: B1 LFM2.5-1.2B, Adapter-Weg (`BodyJepaTrainer`, 30 Schritte, lr 5e-4), 16 Fakten je Seed in 4 Gruppen à 4, 3 Seeds, 4 Arme. fp32-Master, greedy, 4 CPU, ca. 17-22 Min je Arm.
Getippte Gewichte (`sample_labels.modulate`): Mensch .45, echtes Ergebnis 1,0, Eigen (richtig und falsch) .06.

Mittel über 3 Seeds (Anteil des Trainingsziels, das wiedergegeben wird; bei `own_wrong` ist das Ziel FALSCH, hoher Wert = schlecht):

| Arm | falsches Eigen-Etikett übernommen | Mensch+Ergebnis richtig | Eigen richtig | Allgemeinfragen | Nah-Fehlgriff (Leck) |
|---|---|---|---|---|---|
| uniform (alle 1) | **1,00** (1,0 / 1,0 / 1,0) | 1,00 | 1,00 | .94 | .56 |
| typed | **0,83** (0,5 / 1,0 / 1,0) | 1,00 | 1,00 | .96 | .54 |
| no_own (Eigen weg) | 0 (nicht trainiert) | 1,00 | - | .94 | **.25** |
| shuffled (Kontrolle) | 1,00 | .96 | 1,00 | .94 | .58 |

Kriterien: K1 Schutz (typed <= uniform - 0,30): **FAIL** (-0,17, nur Seed 1 schützt). K2 Kosten: ok (0 Verlust). K3 Quelle zählt: ok (shuffled 1,0). K4 Behalten: ok.
Urteil nach Regel: `BP9a_FAIL`. Platz war da (uniform übernimmt falsche Etiketten zu 100 %).

## Was es zeigt
- Ein Gewicht von .06 genügt nicht: Der Adapter lernt 16 Beispiele in 30 Schritten auch mit kleinem Gewicht fast sicher (AdamW skaliert die Schrittgröße mit der Steigung, nicht mit dem Gewicht). Eigen-Etiketten sind richtig wie falsch gleich gelernt (`own_right` 1,00 in allen Armen), die Typisierung unterscheidet nicht nach Richtigkeit.
- Wirksam ist nur das Weglassen der Quelle (`no_own`): Dazu kommt ohne Zusatzkosten ein deutlich kleineres Leck auf Nachbarfragen (.25 gegen .56). Nicht vorregistriert, daher Beobachtung, kein Gewinn. Die Eigen-Gruppe scheint das Leck zu treiben.
- Folge für §63: Typisierte Gewichte als Schrittgrößen-Regler sind bei diesem Trainer unwirksam. Zulassen/Ablehnen je Quelle (Zulassung, Quote) wirkt. `sample_modulation` bleibt aus. Gate/Quote vor dem Training (Mischregel `mix_for_training`) bleibt der Schutz.
- Offen (neue Vorregistrierung nötig, keine Wiederholung): Gewichte, die die Schrittgröße wirklich binden (z. B. Gradienten-Clipping je Quelle oder Gewicht in der Lernrate je Beispiel, weniger Schritte), Messung mit Eigen-Etiketten, die nur teilweise falsch sind (realistischer als 100 % falsch).
Grenzen: erfundene Fakten, Eigen-Etiketten absichtlich 100 % falsch in der Gruppe, 3 Seeds, ein Körper, fp32-Master, kein Handy.
