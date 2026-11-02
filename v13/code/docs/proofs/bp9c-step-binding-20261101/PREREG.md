# WP-BP9c PREREG: wie WP-BP9b, aber Lernrate auf dem VOLLEN Batch kalibriert (Nachfolger von WP-BP9b, `BP9b_NO_SIGNAL`)

Festgelegt VOR den Messläufen. WP-BP9b scheiterte am Aufbau: lr 0,05 (auf 8 Fakten kalibriert) ließ uniform_sgd auf dem 16er-Batch divergieren. Neue Kalibrierung auf Seed 91 mit dem vollen Batch (alle 16 Beispiele, Gewicht 1), bewertet nur an den Mensch- und Ergebnis-Fakten (nicht an der Messgröße Übernahme falscher Etiketten): lr 0,02 -> Treffer .90/1,0/1,0 bei Schritt 10/20/30; lr 0,01 -> .81/.96/1,0. Beide stabil.

**Vorabüberlegung (Nutzerregel).** BP9a: Gewicht .06 hielt falsche Eigen-Etiketten nicht aus dem Update (typed .83, uniform 1,00). Mechanismus-Vermutung: AdamW teilt durch die Wurzel der Gradienten-Größe; sobald die Beispiele mit großem Gewicht gelernt sind (Verlust ~0),
bestimmt der kleine Gradient der Eigen-Beispiele allein die Richtung und wird auf volle Schrittgröße hochgerechnet. Einfaches SGD hat diese Skalierung nicht: Schritt proportional zum gewichteten Gradienten. Verbraucher: der echte Adapter auf B1.
Platz für Gewinn: uniform gibt 1,00 Übernahme falscher Etiketten, also bis ~1,0 zu holen. Kalibrierung (Seed 91, nur Mensch- und Ergebnis-Fakten, SGD Momentum 0,9, 30 Schritte, Teacher-Forcing-Treffer): lr 0,05 -> 1,0 ab Schritt 10; lr 0,2 -> 0,0 (divergiert).
Regel (schon in BP9b festgelegt, hier auf das erweiterte Gitter angewandt): kleinste Lernrate mit Treffer >= 0,9 bei Schritt 30 -> **lr 0,01** (kleinere Raten werden nicht geprüft). Der Fehler von BP9b war die Kalibrierung auf einer Teilmenge, nicht die Regel.

**Aufbau.** Wie BP9a (16 Fakten je Seed in 4 Gruppen à 4: Mensch richtig, Ergebnis richtig, Eigen richtig, Eigen FALSCH; Seeds 1, 2, 3; gleiche Fakten wie dort), aber in der resident Sitzung `lora_session.py` (30 Schritte, KL-Anker wie BJ1), fp32-Master, greedy-Bewertung wie BP9a.
Arme: `uniform_sgd` (alle Gewicht 1, SGD 0,01) | `typed_sgd` (getippte Gewichte Mensch .45 / Ergebnis 1,0 / Eigen .06, SGD 0,01) | `typed_adamw` (Kontrolle im selben Aufbau, AdamW 5e-4).

**Kriterien** (Mittel über 3 Seeds, typed_sgd gegen uniform_sgd):
- K1 Schutz: Übernahme falscher Eigen-Etiketten typed_sgd <= uniform_sgd - 0,30.
- K2 Kosten: Wiedergabe Mensch+Ergebnis typed_sgd >= uniform_sgd - 0,10 (und >= 0,8 absolut, sonst wurde nichts gelernt).
- K3 Optimierer zählt: typed_adamw-Übernahme falscher Etiketten >= typed_sgd + 0,20.
- K4 Behalten: Allgemeinfragen typed_sgd >= uniform_sgd - 0,05.
Urteil: `BP9b_PASS` bei K1-K4; `BP9b_PARTIAL` bei K1 und K2 ohne K3 (Gewicht bindet, aber nicht wegen SGD); sonst `BP9b_FAIL`. `BP9b_NO_SIGNAL`, wenn uniform_sgd falsche Etiketten < 0,5 übernimmt (nichts zu schützen) oder Mensch+Ergebnis in uniform_sgd < 0,8 (Lernrate lernt nicht).
Nichts wird aktiviert, `sample_modulation` und der Trainer-Optimierer bleiben unverändert. Grenzen: erfundene Fakten, Eigen-Etiketten absichtlich zu 100 % falsch in der Gruppe, 3 Seeds, ein Körper, fp32, kein Handy; bei PASS braucht ein Einbau in den Alltagstrainer eine eigene Prüfung (Q4, Vergessen).
