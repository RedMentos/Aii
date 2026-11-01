# B2-Offer-Kandidat gegen STEP2 + Werkzeug — Vorregistrierung (Thread O, 2026-10-13, vor jeder Inferenz)

Kandidat (nicht live): `cognition.patch` (sha256 `d09c2ed2ea63adc6b370e59b9170bfc9eba985c8b39571f9a7e378b18e74116c`) gegen live `v13/cognition.py`
(`d68df49a947b7211a5cf273a29ca620b0f9a7b5fd9d75497cf46c04e9504b5d7`), geladen nur im Messprozess über `scripts/b2_offer_candidate.py`.
Schalter an: `b2_offer_body_state=False` (B2 ohne WP-T5-body_state; B1 unverändert), `offer_quote_min_chars=90`
(Zitatkappe 57 → 90 Zeichen, Platz kommt aus der Zusammenfassung 128 → 64, gleiches Worst-Case-Budget 286 Zeichen).

Lauf: `scripts/step2_b2_offer_candidate.py` = unveränderter STEP2-Harness (`a5a00d1f…`) auf einem Geschwister-Home
(Modelle/Runner per Symlink identisch zu `step2-wire-rebind`), W1-Draht, danach `scripts/step2_tool_replay.py`
auf den neuen Nachrichten. Vergleich: `step2-wire-rebind` w1 (live) und `step2-body-state-ablation` (nur body_state).

## Primär
STEP2-Gate mit Werkzeug (`paired_utility` auf den Werkzeug-Antworten). Erwartung **FAIL**: b2_only wird allein am besten,
B1 hat in diesen Fixtures keine eigene Information.

## Kandidaten-Kriterien (entscheiden über Übergabe zur Live-Integration)
1. Mit Werkzeug 0 falsch festgelegte Entscheidungen in allen 7 Varianten.
2. „Regel behalten“-Zeilen der B2-Varianten (b2_only, both_none, both_exact, both_control = 24 Zeilen) entscheidungs-exakt
   mit Werkzeug: **mindestens 8/24** (live 0/24, nur body_state 0/24).
3. B2-Offers über eigenen Zustand ≤ 5/50 (live 41/50).
4. Alle 70 STEP2-Zeilen RECORDED, Artefakte unverändert.
Alle vier erfüllt → Patch an den Besitzer der Live-Kette übergeben (Standard der Schalter bleibt aus bis dahin).
Sonst: nicht integrieren, Befund festhalten.

## Erwartung (vorab)
Kriterien 1, 3, 4 erfüllt. Kriterium 2 unsicher: Qwen kann mit längerer Kappe trotzdem früher abbrechen oder mit kürzerer
Zusammenfassung schlechter zitieren; Gegenprobe aus der body_state-Ablation (13/13 bei vollständigem Satz) ist eine obere Schranke.
