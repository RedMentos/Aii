# WP-Z6c Vorregistrierung: Mensch ersetzt alte Korrekturen (vor dem Lauf committet)

Anlass: Z6b — der Routen-Lerner übernimmt geänderte menschliche Evidenz nie, weil alte widersprechende Labels im
Trainings-/Prüfsatz bleiben; Ersetzen nach Embedding-Nähe geht nicht (Z6b-Nachtrag).

Neu: `v13/route_supersede.py` + `:ersetze route <Route> <Wörter> [--notiz]` (fester Wort-Leser, kein Modell). Ältere
Routen-Korrekturen, deren Frage eines der Wörter enthält und die eine andere Route tragen, trainieren und prüfen den Kopf
nicht mehr; nichts wird gelöscht, das Shadow-Manifest nennt jede ersetzte Korrektur, `:ersetze undo` stellt alles her.
Eingebaut in `learner.shadow()`; ohne Regel ändert sich nichts.

Messung: `code/scripts/z6b_lifecycle_bench.py --seed 73 --policies fixed,fixed+sup,adaptive+sup` (frischer Seed,
gleicher Strom-Aufbau wie Z6b). In den `+sup`-Armen gibt der simulierte Mensch zu Beginn von Phase 2 genau einmal
`:ersetze route simple hälfte,halbiere,geteilt durch zwei` ein. `fixed` ohne Regel ist die Kontrolle.

Kriterien (`Z6C_SUPERSEDE_PASS` nur wenn alle gelten):
- S1 Hälfte-Fragen im Held-out am Ende ≥ 80 % in beiden `+sup`-Armen.
- S2 Behalten der unveränderten Fragen ≥ 90 % (Ende/Ende Phase 1) in beiden `+sup`-Armen.
- S3 Rücknahme der letzten Freigabe stellt die gemessene Eltern-Genauigkeit exakt her (beide `+sup`-Arme; jetzt erfasst).
- S4 keine falsche Freigabe in den `+sup`-Armen.
- S5 Kontrolle `fixed` ohne Regel: Hälfte-Fragen < 50 %.

Vorlauf vor dieser Vorregistrierung (Dev-Seed 5, nur fixed+sup, nicht gewertet): Hälfte-Fragen 100 %, aber Behalten
75 % und 1 falsche Freigabe; Rücknahme stellt her. Bekanntes Risiko: die Needle-Embeddings trennen Hälfte-Fragen kaum von
anderen Rechenfragen, das Umlernen kann andere Rechenfragen mitziehen.
Grenzen: nur Routen-Kopf, generierte deutsche Umschreibungen, ein Seed, Mensch durch Regel ersetzt, Cloud.
