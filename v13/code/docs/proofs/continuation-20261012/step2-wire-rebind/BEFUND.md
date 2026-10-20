# STEP2 neu gebunden nach WP-W1 — Befund (Thread O, 2026-10-12)

Vorregistrierung: `PREREG.md` (Commit `c0fc000`, vor jeder Inferenz gepusht). Rohdaten:
`v13/bench-results/step2-wire-rebind-20261012/step2_{w1,sorted}.json` (sha256 in `SHA256SUMS`), Logs daneben.
Linux-Cloud x86_64, 4 CPU, b10964-Release-Binary `79e31218…`, B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B, C3 LFM2.5-350M. Kein Redmi.

## Primär: beide Arme UTILITY_FAIL
Alle 140 Zeilen RECORDED, Quellen/Artefakte unverändert, alle Strukturprüfungen bestanden. **0 exakte Entscheidungen in 140 Zeilen.**

| Variante | w1 (Reihenfolge erhalten) | sorted (alter Draht) | 2026-10-09 (alter Draht, alter C3) |
|---|---|---|---|
| b1_only | .608 | .558 | .500 |
| b2_only | .608 | .067 | .092 |
| both_none | .625 | .500 | .292 |
| both_exact (primär) | .558 | .442 | .342 |
| both_control | .625 | .492 | .142 |
| same_policy_dual | .608 | .550 | .467 |
| prompt_only_dual | .633 | .483 | — |

w1: both_exact .558 < best_solo .608 → Gate FAIL. sorted: .442 < .558 → FAIL.

## Sekundär (vorregistriert)
- **D1 Draht-Effekt sitzt im Konsumenten, nicht im Körper-Transport.** Unter `sorted` erzeugt C3 in jeder Option die Zahlen vor `entity` (alphabetisch) und schreibt danach oft zweimal `"B"` → 20/70 Antworten ungültig (b2_only 9/10), Nutzen 0. Unter `w1` steht `entity` zuerst: 0/70 ungültig. Fast der ganze Nutzenzuwachs (b2_only .07 → .61) ist dieser Strukturgewinn.
- **D2 Regel-Transport bleibt schwach:** Ein verifiziertes Zitat mit der früheren Budgetregel erreicht C3 in w1 8/70, in sorted 6/70 Zeilen (nur B2-Varianten; B1 nie). W1 behebt den Produzenten-Engpass nicht.
- **D3 Konsument rechnet nicht:** C3 antwortet fast immer NONE/UNKNOWN (w1: 61/70), `remaining` für beide Optionen richtig nur 5/70 (w1) bzw. 0/50 gültige (sorted). Feld `project` ist in jeder Zeile falsch („Project Aurora“ statt „Aurora“), bekannter Bewertungshinweis, ändert das Gate nicht.

## Folgen
- W1 ist für den Konsumenten nützlich (keine ungültigen Optionen mehr) und bleibt. STEP2 UTILITY_FAIL bleibt bestehen, jetzt auf dem W1-Draht neu gebunden.
- Die Erwartung aus der Vorregistrierung trifft zu: Engpass ist zuerst C3-Rechnung (0 exakt), dann Produzent (Regel erreicht C3 in ≤ 3/10 Episoden).
- Nächster sinnvoller vorregistrierter Arm: STEP2 mit Werkzeug (WP-W2/W2c Wächter + Rezept, sobald Thread H es als READ_LOCAL einbindet). Erst dann misst STEP2 den Körper-Beitrag statt der C3-Arithmetik.
