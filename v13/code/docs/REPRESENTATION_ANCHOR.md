# WP-U5 Representation Anchor als Stabilitäts-Regler (§69, §48.10)

Je Gewichts-Trainings-Batch (AG6, `agi/weights.train`) setzt `v13/anchor.py` die Stärke des KL-zur-Basis-Ankers.

**Neuheit:** 1 − mittlere beste Relevanz jeder Batch-Frage zu den aktiven Erinnerungen außerhalb des Batches. Gibt es keine anderen Erinnerungen, ist die Neuheit 1.

**Stabilität:** Merkmal `stability` des N10-Pfads `weights`.

**Multiplikator:** m = 1 + `protected_old_skill_weight` · Stabilität − `new_domain_relaxation` · Neuheit · (1 − Stabilität). Der Wert wird begrenzt:
- Untergrenze `pretrained_geometry_weight`,
- bei geteilten Layern (dichte FFN-/Attention-LoRA, Live-Ziele w1–w3) Untergrenze `shared_layer_priority`,
- Obergrenze 2.

**Wirkung:**
- **SHADOW** (Standard): Die Policy steht im Batch (`anchor`); trainiert wird mit dem gemessenen Anker (Live 8).
- **ACTIVE**: Nur per `:anchor active` (Mensch). Dann wird `anchor_weight` für diesen Batch mit m skaliert und danach zurückgesetzt.

Drift-Grenzen (WP-S5, `stability_envelope`) werden nie gelockert.

**Befehle:** `:anchor [status|shadow|active]`.
**Tests:** `tests/test_anchor.py` (3).
**Grenze:** Die ANCHOR-Werte sind BOOT-Werte aus §69 und nicht gemessen. Ob ein schwächerer Anker bei neuen Domänen das Gate besteht, ist offen (Lauf mit Modell, `scripts/ag6_live_bench.py`).
