# WP-Z6i Vorregistrierung: der Routen-Kopf lernt die geänderte Grenze selbst (vor dem Lauf committet)

Anlass: Z6b (neue menschliche Korrekturen werden nie übernommen), Z6c (Ersetzen wirkt, aber der Kopf auf eingefrorenen
Needle-Embeddings sieht den Unterschied zwischen Hälfte-Fragen und anderen Rechenfragen nicht) und Z6d (feste
Wort-Regel des Menschen wirkt sofort, ist aber kein Lernen; Kopf selbst 0 %). Ziel ist echtes Dazulernen: der Kopf
übernimmt die neue Vorliebe nur aus Korrekturen, ohne dass der Mensch Wörter oder Geltungsbereich nennt.

Änderung (`v13/route_features.py`, `learning_worker.py`, `learning.py`, Schalter `route_word_channel`,
`route_recency_half_life`, beide Standard 0 = Verhalten unverändert):
1. Wort-Kanal: feste, deterministische Hash-Merkmale der Frage (Wörter, Wortpaare, Buchstaben-4-Gramme in Wörtern;
   Zahlen ausgeblendet) neben dem Needle-Embedding. Die Gewichte darauf lernt nur der bestehende Shadow-Job aus
   expliziten Korrekturen, unter den bestehenden Prüfungen; keine Regel entscheidet eine Route. Ein alter Needle-Kopf
   wird mit Null-Zeilen erweitert (gleiche Vorhersagen) und lernt weiter.
2. Neuere Evidenz zählt mehr: Trainingsgewicht halbiert sich je 16 Korrekturen Alter (Mittel 1, Schrittbudget gleich).

Messung: `code/scripts/z6b_lifecycle_bench.py <home> <out> --seed 83 --policies fixed,fixed+lex,fixed+rec,fixed+lex+rec,adaptive+lex+rec,fixed+lex+sup`
(frischer Seed, gleicher Strom wie Z6b: Phase 1 sechs Stapel, Phase 2 vier Stapel mit Hälfte -> simple; Harness gibt
jeden geeigneten Kandidaten frei). Kein `:ersetze` außer im Arm `+sup` (Vergleich mit Z6c).
Zusätzlich 16 neue Prüf-Fragen aus Formulierungen, die nie im Training oder im Haupt-Prüfsatz vorkommen:
8 Hälfte-Fragen in neuen Worten (`half_novel`, nach der Verschiebung simple) und 8 nahe andere Rechenfragen mit
geteilten Wörtern (`detail_near`: Viertel, durch 4, drei Teile, 25 Prozent; bleiben detail).

Kriterien (`Z6I_HEAD_LEARNS_PASS` nur wenn alle gelten; Haupt-Arme fixed+lex+rec und adaptive+lex+rec):
- I1 Kopf selbst (nicht Regel) am Ende ≥ 80 % der Hälfte-Fragen im Haupt-Prüfsatz, beide Haupt-Arme.
- I2 Behalten unveränderter Fragen ≥ 90 % des Stands am Ende von Phase 1, beide Haupt-Arme.
- I3 keine falsche Freigabe (Gesamt nicht −1 Punkt, Unverändert nicht −5 Punkte), beide Haupt-Arme.
- I4 Rücknahme der letzten Freigabe stellt die gemessene Eltern-Genauigkeit exakt her, beide Haupt-Arme.
- I5 Kontrolle fixed (nur Needle, kein Wort-Kanal, keine Gewichtung) < 50 % Hälfte-Fragen.
- I6 Laufzeitpfad (Runtime._route, keine Regel) in fixed+lex+rec ≥ 80 % Hälfte-Fragen.

Beschreibend, keine Bestehens-Kriterien (Hypothesen vorab): `half_novel` ≥ 50 % und `detail_near` ≥ 75 % im Arm
fixed+lex+rec; Ablation: fixed+lex (nur Wörter) und fixed+rec (nur Gewichtung) — erwartet: Wörter tragen den
Hauptteil, Gewichtung allein reicht nicht. fixed+lex+sup zeigt, ob die Wort-Angabe des Menschen noch nötig ist.
Grenzen: nur Routen-Kopf, generierte deutsche Umschreibungen, ein Seed, Mensch durch Harness ersetzt, Cloud, kein Handy.
