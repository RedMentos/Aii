# WP-Z6d Vorregistrierung: Wörter des Menschen als feste Routen-Vorgabe beim Antworten (vor dem Lauf committet)

Anlass: Z6c — Ersetzen alter Korrekturen wirkt, aber der Routen-Kopf auf Needle-Embeddings kann die neue Grenze
(Hälfte-Fragen → simple, andere Rechenfragen → detail) nicht lernen.

Neu: `:ersetze route <Route> <Wörter> --sofort` — dieselben Wörter leiten passende Fragen beim Antworten direkt auf die
Route (fester Wort-Leser in `episodic_route.for_turn` vor Gerüst und Kopf, Quelle `HUMAN_ROUTE_RULE`); `:ersetze undo`
nimmt es zurück. Ohne `--sofort` ändert sich das Antworten nicht.

Messung: `code/scripts/z6b_lifecycle_bench.py --seed 79 --policies fixed,fixed+now,adaptive+now` (frischer Seed). In den
`+now`-Armen gibt der simulierte Mensch zu Beginn von Phase 2 einmal
`:ersetze route simple hälfte,halbiere,geteilt durch zwei --sofort` ein. Gemessen wird über den echten Antwort-Weg
`Runtime._route` auf dem Held-out-Satz am Ende, dann Regel zurücknehmen und mit demselben Kopf erneut messen.

Kriterien (`Z6D_RULE_ROUTE_PASS` nur wenn alle gelten):
- D1 Hälfte-Fragen über den echten Antwort-Weg ≥ 90 % richtig in beiden `+now`-Armen.
- D2 Die Regel ändert keine andere Frage: mit demselben Kopf sind alle übrigen Routen mit Regel = ohne Regel.
- D3 Rücknahme vollständig: danach keine Entscheidung mehr mit Quelle `HUMAN_ROUTE_RULE`; vorher trugen alle
  Hälfte-Fragen diese Quelle.
- D4 Kontrolle `fixed` ohne Regel: Hälfte-Fragen über den Antwort-Weg < 50 %.
Beschreibend: Genauigkeit der übrigen Fragen über die Zeit (der Kopf lernt in Phase 2 weiter, kann dabei kippen, Z6c).
Vorlauf (Dev-Seed 5, nur fixed+now, nicht gewertet): Hälfte 100 %, Regel ändert 0 andere Fragen, Rücknahme vollständig.
Grenzen: fester Wort-Leser (Schreibvarianten ohne die Wörter fallen durch), nur Routen-Wahl, ein Seed, Cloud.
