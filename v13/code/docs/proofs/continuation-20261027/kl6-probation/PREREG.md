# WP-KL6 Vorregistrierung: Probezeit für einen neuen Routen-Kopf vor der Freigabe (vor dem Lauf committet)

Anlass: KL2–KL3b. Keine feste Schwelle auf den wenigen eigenen Korrekturen des Shadow-Jobs übernimmt zugleich
immer und verschlechtert nie kurz (streng = lernt nicht; locker = seltene kurze Rückschritte), weil der Eltern-Kopf
auf Labels bewertet wird, die er gelernt hat.

Änderung (`v13/route_probation.py`, `:probation status|start`, Haken in `:feedback route`): ein freigabefähiger
Kandidat (Prüfung wie KL3, `route_gate_outvoted=1`) geht zuerst in Probezeit. Jede **neue** menschliche
Routen-Korrektur, die weder Kandidat noch aktiver Kopf gesehen haben, zählt einen Treffer für den, der sie richtig
vorhergesagt hätte (ohne aktiven Kopf: Gerüst). Nach 8 Korrekturen: READY, wenn Kandidat ≥ Eltern, ≥ 75 % und
(strikt besser oder 8/8), sonst REJECT. Ein neuerer Kandidat ersetzt eine laufende Probezeit. Freigabe bleibt
`:approve` (in der Bench: Harness gibt READY frei, lehnt REJECT ab). Feste Regel, kein Modell.

Messung: `code/scripts/z6b_lifecycle_bench.py <home> <out> --seed S --policies fixed,fixed+lex+rec+cv+ov,fixed+lex+rec+cv+ov+prob,adaptive+lex+rec+cv+ov+prob`,
frische Seeds S = 137, 139, 149; Ausgabe `v13/bench-results/kl6-probation-20261027/kl6-seed<S>.json`.

Kriterien (`KL6_PROBATION_PASS` nur wenn in **allen drei** Seeds alle gelten; Haupt-Arme die beiden `+prob`-Arme):
P1 Kopf selbst ≥ 80 % Hälfte-Fragen am Ende; P2 Behalten ≥ 90 %; P3 keine falsche Freigabe; P4 Rücknahme exakt;
P5 Kontrolle fixed < 50 %; P6 Laufzeitpfad fixed+…+prob ≥ 80 % Hälfte-Fragen (Definitionen wie KL3 L1–L6).
Beschreibend: Verzögerung bis zur Übernahme gegen KL3-Prüfung ohne Probezeit, READY/REJECT-Zählung, half_novel.
Grenzen wie KL1; die Probezeit-Korrekturen sind die normalen nächsten Korrekturen des Stroms.
