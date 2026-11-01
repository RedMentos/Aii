# STEP2-Produzent: B2 ohne body_state — Vorregistrierung (Thread O, 2026-10-12, vor jeder Inferenz)

## Anlass
STEP2 auf W1-Draht (`step2-wire-rebind/BEFUND.md`): 41/50 B2-Offers (Qwen3.5-0.8B) fassen nur den eigenen Zustand
zusammen („NO_COMPLETED_OWN_DIGITAL_ACTIONS … no prior knowledge“, aus `bodyview.body_state`, WP-T5), obwohl die
frühere Regel in 24/30 „Regel behalten“-Offers in `earlier_context` liegt. Unter dem alten Draht waren es 21/50.
Mit Werkzeug (`step2-tool-replay`) erreicht die frühere Regel C3 in 0/36 nötigen Zeilen.

## Arm (fest)
`scripts/step2_body_state_ablation.py` (sha256 `c99f73c6f571ba452658d4ff5e54b62704407ca0da0dda5e3037c511ef41bae9`): unveränderter STEP2-Harness (`a5a00d1f…`), W1-Draht,
`bodyview.body_state` liefert für B2_GIST zur Laufzeit None; B1 unverändert. Gleiche Modelle/Runner/Fixtures/Seed wie
`bench-results/step2-wire-rebind-20261012/step2_w1.json` (Vergleichsarm). Danach `scripts/step2_tool_replay.py` auf
den neuen Nachrichten (gleiche Extraktion, `eligibility-v2-anchored`).

## Messgrößen
- Primär: STEP2-Gate (`scoped_utility_gate_pass`) ohne und mit Werkzeug, je unverändert.
- Sekundär (vorab): (a) B2-Offers über eigenen Zustand (Vergleich 41/50); (b) Zeilen, in denen ein verifiziertes Zitat
  `Budget <früheres Budget> euros` C3 erreicht, getrennt nach „Regel behalten“ (Vergleich 0/30 B2-Zeilen) und Überschreibung;
  (c) mit Werkzeug: entscheidungs-exakte Zeilen je Variante (Vergleich 5/10) und falsch festgelegte (Vergleich 0).

## Erwartung (vorab)
(a) fällt deutlich. (b) steigt in „Regel behalten“ nur, wenn Qwen die frühere Quelle wörtlich zitiert; wegen der
57-Zeichen-Zitatkappe fehlt dann meist `local_only` → mit Werkzeug trotzdem UNKNOWN. Gate bleibt FAIL, auch weil B1 in diesen
Fixtures keine eigene Information hat (b1_only kann nie allein gewinnen).
Was es ändern würde: sinkt (a) und steigt (b), ist body_state im B2-Prompt ein echter Störfaktor → body_state für B2 nach
hinten/abschaltbar machen (eigener Kandidat). Bleibt (b) bei 0, liegt der Engpass im Modell, nicht im Prompt.
