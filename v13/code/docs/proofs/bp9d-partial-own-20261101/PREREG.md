# WP-BP9d PREREG: Eigen-Etiketten nur TEILWEISE falsch, Gewicht schließt die Quelle nicht aus (Nachfolger von WP-BP9c, SGD)

Festgelegt VOR der Messung (Aufbau-Tests laufen, keine Modellzahl gesehen).

**Vorabüberlegung (Nutzerregel).** BP9c: Mit SGD und Eigen-Gewicht .06 lernt der Körper die Eigen-Quelle gar nicht (richtig 0, falsch 0), also Ausschluss statt Unterscheidung. Praxisnäher: Eigen-Etiketten sind meistens richtig und nur selten falsch.
Die offene Frage: Gibt es ein Eigen-Gewicht, bei dem die richtigen Eigen-Etiketten gelernt werden, die falschen aber deutlich weniger? Platz für Gewinn: uniform_sgd übernimmt falsche Etiketten zu ~0,9 (BP9c), und richtige Eigen-Etiketten gehen bei .06 verloren; dazwischen liegt der Spielraum.
**Ausdrückliche Erwartung vorab:** Eher kein Gewinn. Ob ein Etikett gelernt wird, hängt am Gewicht und nicht an seiner Richtigkeit; der Körper kennt die erfundenen Fakten nicht und kann falsch von richtig nicht trennen. Das Ergebnis ist trotzdem nötig, weil es die Kurve (Gewicht gegen Lernen/Übernahme) liefert, aus der der Nutzer entscheidet, ob Eigen-Etiketten im Alltag mit SGD eingebunden werden. Ein Selbstkonsistenz-Signal (echte Unterscheidung) wäre ein eigener Schritt.

**Aufbau.** Seeds 1, 2, 3; je 16 Fakten: `human` 4 (Gewicht .45), `outcome` 4 (1,0), `own_right` 6, `own_wrong` 2 (Eigen-Gewicht w). Fakten und Verfahren wie BP9c (Pool, SGD lr 0,01 Momentum 0,9, 30 Schritte, KL-Anker, resident Sitzung, greedy-Bewertung).
Arme: `uniform_sgd` (alle 1) | `own015_sgd` (w .15) | `own030_sgd` (w .30). Insgesamt 6 falsche Eigen-Etiketten und 18 richtige je Arm über die Seeds.

**Kriterien** je Eigen-Gewicht (Mittel über 3 Seeds; Übernahme = Wiedergabe des FALSCHEN Etiketts):
- K1 Nutzen: own_right-Wiedergabe minus Übernahme falscher Etiketten >= 0,25.
- K2 Schutz: Übernahme falscher Etiketten <= uniform_sgd - 0,30.
- K3 Kosten: Mensch+Ergebnis >= uniform_sgd - 0,10.
- K4 Behalten: Allgemeinfragen >= uniform_sgd - 0,05.
Urteil `BP9d_PASS`, wenn mindestens ein Gewicht K1-K4 erfüllt; sonst `BP9d_FAIL`. `BP9d_NO_SIGNAL`, wenn uniform_sgd falsche Etiketten < 0,5 übernimmt.
Auflösungsgrenze: 6 falsche Etiketten insgesamt, Schritte von 0,17; Unterschiede darunter sind Rauschen. Nichts wird aktiviert. Grenzen: erfundene Fakten, 3 Seeds, ein Körper, fp32, kein Handy.
