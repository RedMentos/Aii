# WP-N5 Aufmerksamkeit (F1, §4B, §5.1, A4, §60) — Übergabe

Code `v13/attention.py`, Tests `tests/test_attention.py`, Befehl `:attention [status|edge <Kante>|shadow|active]`.

## Live im Durchlauf
- `runtime._turn`: A4-Spannensalienz nach `percept()`, High-Res-Re-looks als `AttentionRequest` (A4 → A_SOURCE), Zulassung unter Event-Budget × Ressourcendruck.
- `focal.FocalLoop.run`: pro Zyklus `modulate` aus B1/B2-Konflikt, World-Fehler und den N10-Modulatoren der letzten 3 Turns der Sitzung (`recent_modulators`, Zerfall `RELAX` je Turn); Fokus-Gain setzt die Kopplung, Workspace-Gain die Koalitionsschwelle; Interrupt ab Salienz .6. Gezielte Re-entry läuft als JEF-Request mit Ergebnis (in Koalition: +.5, sonst −.25).
- Nach einer Modellantwort: `source_outcome` bewertet jeden gewährten High-Res-Span über die Abdeckung seiner exakten Cues (Zahlen, Zitate, Verneinungen): Nutzen = .75·Abdeckung − .25. Spans ohne Cues bekommen kein Label. Exakte Kopien/feste Regeln lernen nicht.
- C5 (`ActionGate.select`): `gain_action` aus der thalamischen Action-Gain ersetzt die Konstante; Vorsicht senkt das Gewicht der Fokus-Unterstützung. Im Paket als `action_gain`.

## Grenzen
- Gelernter Nutzen-Prior bleibt SHADOW, ACTIVE nur per `:attention active` (ausdrücklich).
- Gain hat keine Wahrheits-/Konfidenz-Autorität; native Attention wird nie gepatcht.
- Offen: MEMORY/WORLD-Provider (zweiter Abruf bei hoher Salienz), Nutzen-Messung mit echten Modellen (WP-N12).

## Nachtrag 2026-10-10: MEMORY-Provider
- `FocalLoop._attended_recall`: bei Konflikt ≥ `disagreement_trigger` einmal pro Turn ein JEF→MEMORY-Request (Grund `recall`, Budget 32). Provider = `Memory.recall` mit den zwei widersprüchlichsten Body-Offers als Cue, höchstens 2 neue Erinnerungen. Sie konkurrieren sofort in der Koalition; Ergebnis +.5 (in Koalition) / −.25 (nicht) geht an `outcome`.
- WORLD-Provider bewusst nicht gebaut: World-Vorhersagen betreffen eigene Aktionen, nicht Koalitions-Inhalte.
