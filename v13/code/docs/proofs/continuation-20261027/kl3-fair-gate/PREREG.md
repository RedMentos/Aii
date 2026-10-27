# WP-KL3 Vorregistrierung: faire Freigabe-Prüfung bei geänderter Vorliebe (vor dem Lauf committet)

Anlass: KL2 (`KL2_STABLE_GATE_FAIL`). Diagnose mit protokollierten Prüf-Kennzahlen (Wiederholung Seed 97, nur
Diagnose, `scratchpad`, kein Ergebnis): Die neue Prüfung lehnte in Phase 2 gute Kandidaten ab, weil unter den
bewerteten neuesten Detail-Korrekturen noch alte „Hälfte -> detail“-Labels lagen; der Kandidat, der die neue Vorliebe
gelernt hat, „verliert“ genau diese (detail 1,00 -> 0,67/0,71). Dazu Gleichstände (Kandidat = Eltern) bei
niedrigerem Verlust abgelehnt.

Änderung (Schalter `route_gate_outvoted`, nur mit `route_gate_folds`, Standard 0): bewertete Labels, die selbst
das auf allen Korrekturen gewichtet trainierte Modell ablehnt, gelten als von neuerer Evidenz überstimmt; sie zählen
weder als Rückschritt noch als Erfolg (höchstens 25 % der bewerteten Labels je Route, älteste zuerst; Anzahl im
Protokoll). Gleichstand der bewerteten Genauigkeit darf bei niedrigerem Verlust durch. Alles andere wie KL2.
Die Bench protokolliert jetzt die Prüf-Kennzahlen jedes Jobs (`gate`).

Messung: `code/scripts/z6b_lifecycle_bench.py <home> <out> --seed S --policies fixed,fixed+lex+rec+cv,fixed+lex+rec+cv+ov,adaptive+lex+rec+cv+ov`
für drei frische Seeds S = 103, 107, 109; Ausgabe `v13/bench-results/kl3-fair-gate-20261027/kl3-seed<S>.json`.

Kriterien (`KL3_FAIR_GATE_PASS` nur wenn in **allen drei** Seeds alle gelten; Haupt-Arme fixed+lex+rec+cv+ov, adaptive+lex+rec+cv+ov):
- L1 Kopf selbst am Ende ≥ 80 % Hälfte-Fragen, beide Haupt-Arme.
- L2 Behalten unveränderter Fragen ≥ 90 % des Stands Ende Phase 1, beide Haupt-Arme.
- L3 keine falsche Freigabe, beide Haupt-Arme.
- L4 Rücknahme der letzten Freigabe exakt, beide Haupt-Arme.
- L5 Kontrolle fixed (nur Needle) < 50 % Hälfte-Fragen.
- L6 Laufzeitpfad in fixed+lex+rec+cv+ov ≥ 80 % Hälfte-Fragen.
Beschreibend: Vergleich mit KL2-Prüfung (+cv), Anzahl überstimmter Labels, half_novel/detail_near. Grenzen wie KL1.
