# WP-BP9d BEFUND: Eigen-Etiketten zu 25 % falsch, Gewicht schließt die Quelle nicht aus: `BP9d_FAIL`

Vorregistrierung `PREREG.md` (vor der Messung, mit Erwartung "eher kein Gewinn"). Roh: `bench-results/bp9d-partial-own-20261101/bp9d-seed{1,2,3}.json`.
Echter Körper B1, 3 Seeds, je 16 Fakten (Mensch 4, Ergebnis 4, Eigen richtig 6, Eigen falsch 2), SGD lr 0,01, 30 Schritte. Mittel über 3 Seeds (18 richtige, 6 falsche Eigen-Etiketten je Arm):

| Arm | Eigen richtig gelernt | Eigen FALSCH übernommen | Mensch+Ergebnis | Allgemeinfragen | Nah-Fehlgriff |
|---|---|---|---|---|---|
| uniform_sgd | .94 | 1,00 | 1,00 | .94 | .65 |
| own015_sgd (w .15) | .17 | 0,00 | .92 | .98 | .35 |
| own030_sgd (w .30) | .33 | .17 | .92 | .98 | .42 |

Kriterien je Gewicht: K1 Nutzen (richtig - falsch >= 0,25): w .15 -> .17, w .30 -> .17: **nicht erfüllt**. K2 Schutz: erfüllt (0,00 / .17 gegen 1,00). K3 Kosten (Mensch+Ergebnis >= 0,90): .92 erfüllt. K4 Behalten: erfüllt.
Urteil nach Regel: **`BP9d_FAIL`** (K1 bei beiden Gewichten verfehlt).

## Was es zeigt
- Die erwartete Kurve: Mit SGD nimmt das Eigen-Gewicht den Eigen-Etiketten die Lernfähigkeit schnell: bei .15 lernt der Körper nur 1 von 6 richtigen und kein falsches, bei .30 2 von 6 richtigen und 1 von 6 falschen, bei Gewicht 1 fast alles (.94 / 1,00). Zwischen "ausgeschlossen" und "alles übernommen" liegt kein Bereich, in dem richtige deutlich über falschen stehen (Abstand höchstens .17, auf 6 falschen Etiketten kein belastbarer Unterschied).
- Das bestätigt die Vorab-Erwartung: Das Gewicht entscheidet über Lernen oder nicht Lernen, nicht über Richtigkeit. Ohne unabhängiges Zuverlässigkeits-Signal (z. B. Selbstkonsistenz, Übereinstimmung mit Mensch/Ergebnis) lässt sich die Eigen-Quelle mit Einzelgewichten nicht nutzen, nur ausschließen.
- Praktische Folge für den Bauplan: Die Eigen-Quelle (Selbst-Etiketten) wird im Gewichts-Lernen wie bisher durch Zulassen/Ablehnen und Quote behandelt (BP9a: Weglassen wirkt; BP9c: SGD+kleines Gewicht entspricht Ausschluss). Getippte Einzelgewichte bringen für diese Quelle nichts darüber hinaus. Für Mensch und Ergebnis genügt .45/1,0 wie gemessen.
- Offen (eigener Schritt, ohne Okay machbar): Zuverlässigkeits-Signal Selbstkonsistenz an echten Eigen-Antworten (kein erfundener Fakt): Wiederholte Antworten stimmen überein = hohes Gewicht. Das braucht echte Eigen-Etiketten (SDFT), nicht erfundene Fakten.
Grenzen: 6 falsche Etiketten, erfundene Fakten, 3 Seeds, ein Körper, fp32, kein Handy.
