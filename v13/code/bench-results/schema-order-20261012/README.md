# WP-W1: Schema-Reihenfolge auf dem Draht (2026-10-12, Thread H)

Befund: `common.dumps` sortiert Schlüssel; llama-server (b10964) baut die JSON-Schema-Grammatik in Property-Reihenfolge. Damit erzwang die Runtime z. B. bei `offer_schema` die Reihenfolge `needs_reentry, quotes, summary, uncertainty`: das Modell entschied über Wiedereintritt, bevor es die Zusammenfassung schrieb.

Fix: `v13/runners.py: wire_json` (Reihenfolge erhalten) für alle drei Request-Bodies; Hashes/Logs bleiben bei der sortierten `common.dumps`. Als Glied `schema_order` in `scripts/integrated_candidates.py` eingehängt, damit die gebundenen Kandidaten-Regressionen die Live-Quellen weiter akzeptieren.

Nativer Beleg (Linux Cloud, llama-server b10964, EuroMoE Q4_K_M, temp 0, `check.py`, `euromoe-offer-order.json`):
- sortiert gesendet: Ausgabe-Reihenfolge `needs_reentry, quotes, summary, uncertainty`
- `wire_json`: `summary, quotes, uncertainty, needs_reentry` (= Schema)

Folge: alle strukturierten Ausgaben ändern sich. Frühere Messungen mit strukturierten Ausgaben (STEP2, Offer-/Kontrakt-Benches) gelten für den alten Draht und sind bei Wiederholung neu zu binden. Suite: 1257 OK.
