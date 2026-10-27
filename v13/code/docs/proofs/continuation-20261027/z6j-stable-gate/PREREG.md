# WP-Z6j Vorregistrierung: stabilere Freigabe-Prüfung für den lernenden Routen-Kopf (vor dem Lauf committet)

Anlass: Z6i (`Z6I_HEAD_LEARNS_FAIL`, Teilerfolg). Mit Wort-Kanal + Gewichtung lernte der Kopf die geänderte Vorliebe
selbst (fixed+lex+rec: Hälfte 0,25 -> 1,00, gesamt 0,95), aber die Prüfung im Worker misst auf je ~4 neuesten
Korrekturen pro Route: zwei schlechtere Köpfe kamen durch (Phase 1), gute Kandidaten wurden abgelehnt (adaptive Phase 2).

Änderung (Schalter `route_gate_folds`, Standard 0 = alte Prüfung): die neueste Hälfte der Korrekturen jeder Route wird
außerhalb der Stichprobe bewertet (4 Teile; jede bewertete Korrektur beurteilt ein Kandidat, der sie nicht gelernt hat;
ältere Korrekturen lernen immer mit, gewichtet, haben aber kein Veto gegen eine geänderte Vorliebe). Freigabe nur, wenn
bewertete Genauigkeit steigt, Verlust sinkt, ≥ 0,75, ≥ Gerüst, und je Route höchstens max(0,02, ein Element) Verlust.
Der freigegebene Kandidat lernt danach auf allen Korrekturen. Die Prüfung ist im Code fest (kein Bench-Zugriff).

Messung: `code/scripts/z6b_lifecycle_bench.py <home> <out> --seed S --policies fixed,fixed+lex+rec,fixed+lex+rec+cv,adaptive+lex+rec+cv`
für drei frische Seeds S = 89, 97, 101 (je eigene Ausgabe-Datei). Sonst wie Z6i (Harness gibt geeignete Kandidaten frei,
kein `:ersetze`, 16 neue Prüf-Formulierungen beschreibend).

Kriterien (`Z6J_STABLE_GATE_PASS` nur wenn in **allen drei** Seeds alle gelten; Haupt-Arme fixed+lex+rec+cv und adaptive+lex+rec+cv):
- J1 Kopf selbst am Ende ≥ 80 % Hälfte-Fragen, beide Haupt-Arme.
- J2 Behalten unveränderter Fragen ≥ 90 % des Stands Ende Phase 1, beide Haupt-Arme.
- J3 keine falsche Freigabe, beide Haupt-Arme.
- J4 Rücknahme der letzten Freigabe exakt, beide Haupt-Arme.
- J5 Kontrolle fixed (nur Needle) < 50 % Hälfte-Fragen.
- J6 Laufzeitpfad in fixed+lex+rec+cv ≥ 80 % Hälfte-Fragen.

Beschreibend: Vergleich fixed+lex+rec (alte Prüfung) gegen +cv je Seed (falsche Freigaben, Ablehnungen guter
Kandidaten, Korrekturen bis Hälfte ≥ 80 %); half_novel / detail_near. Grenzen wie Z6i.
