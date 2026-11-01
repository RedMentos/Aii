# WP-BP9a PREREG: getrennte Lernsignale an echten Updates (Blueprint §12.4, §14.5, §63; Z6k-Folge)

Festgelegt VOR jeder Messung (nur Lauffähigkeit per Smoke, 2 Schritte, keine Auswertung).

**Vorabüberlegung (Nutzerregel).** Voraussetzungen jetzt da: BP2f liefert Quelle je Beispiel (`sample_labels.modulate`, Gewichte Mensch .45 / Eigen .06 / echtes Ergebnis 1,0),
der echte Körper B1 (LFM2.5-1.2B) lernt über den Adapter-Weg (`BodyJepaTrainer`, Gewicht je Beispiel wird im Verlust benutzt), und der Verbraucher ist die
echte Wirkung des Updates (Antwort des Körpers). Frühere Z6k-Tests liefen an einem schwankenden Hilfs-Lerner (Niveau .52-.56 gegen Decke .82). Platz für Gewinn:
Der Weg ohne Typen lernt falsche Etiketten genauso sicher wie richtige (BJ1: gelernte Fakten 1,00 nach 30 Schritten), also ist die Übernahme falscher
Eigen-Etiketten dort ~1,0 und die Typisierung kann sichtbar bis zu ~1,0 Punkte senken. Nicht erwartet: Gewinn, wenn die Eigen-Gewichte (.06) trotz Adam
die falschen Etiketten dennoch vollständig lernen lassen -> das wäre dann das Ergebnis (BP9a_FAIL), nicht ein Fehler des Aufbaus.
Sichtbarkeit: je Seed 4 Fakten je Gruppe, 3 Seeds -> 12 Fakten je Gruppe und Arm; Unterschiede unter 0,17 (2 von 12) gelten als Rauschen.

**Aufbau.** 16 Fakten je Seed aus dem BJ1-Pool in 4 Gruppen à 4: `human` (richtig, Mensch), `outcome` (richtig, deterministisches Ergebnis),
`own_right` (richtig, vom Modell geschrieben), `own_wrong` (FALSCHES Ziel = Antwort eines anderen Faktums, vom Modell geschrieben).
Arme (gleiche Schleife, Schritte 30, lr 5e-4, Anker, Fakten): `uniform` (alle Gewicht 1) | `typed` (`modulate`) | `no_own` (Eigen weggelassen) |
`shuffled` (getippte Gewichte zufällig auf die Beispiele vertauscht; Kontrolle, dass die QUELLE zählt und nicht nur kleinere Gewichte).
Messung am fp32-Master, greedy: Wiedergabe des Trainingsziels je Gruppe (bei `own_wrong` = Übernahme des falschen Etiketts), Allgemeinfragen (Behalten), Nah-Fehlgriff.

**Kriterien** (Mittel über Seeds 1, 2, 3; typed gegen uniform):
- K1 Schutz: Übernahme falscher Etiketten typed <= uniform - 0,30.
- K2 Kosten: Wiedergabe der richtigen Gruppen human+outcome typed >= uniform - 0,10.
- K3 Quelle zählt: shuffled-Übernahme falscher Etiketten >= typed + 0,15.
- K4 Behalten: Allgemeinfragen typed >= uniform - 0,05.
Urteil: BP9a_PASS bei K1-K4; BP9a_PARTIAL bei K1 und K2 ohne K3 (Gewichte wirken, aber nicht wegen der Quelle) oder K1 ohne K4; sonst BP9a_FAIL.
Sonderfall BP9a_NO_SIGNAL, wenn uniform die falschen Etiketten zu < 0,5 übernimmt (nichts zu schützen).
Mit angegeben, aber nicht bewertet: `own_right` (Kosten der Typisierung: richtige Eigen-Etiketten werden mit .06 kaum gelernt), `no_own` als Obergrenze.
Nichts wird aktiviert; `sample_modulation` bleibt Standard aus. Grenzen: erfundene Fakten, ein Körper, fp32-Master statt Q4, kein Handy, 3 Seeds.
