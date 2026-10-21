# STEP2 mit Eignungs-Werkzeug (Replay der W1-Nachrichten) — Befund (Thread O, 2026-10-12)

Vorregistrierung `report.preregistration.json` (sha256 `5feb687e…71e5c`, Commit `e0b3489`, vor der Inferenz gepusht).
Eingabe: die 70 aufgezeichneten C3-Nachrichten aus `bench-results/step2-wire-rebind-20261012/step2_w1.json` (echte B1/B2-Offers und verifizierte Zitate, bytegleich).
C3 LFM2.5-350M liest nur typisierte Werte (WP-W2 `EXTRACT_SCHEMA`), `v13.agi.eligibility.decide` (`eligibility-v2-anchored`, Thread H) entscheidet. Baseline = aufgezeichnete W1-Antworten derselben Nachrichten. 70/70 RECORDED, Artefakte unverändert. Linux-Cloud, kein Redmi.

## Primär: TOOL_UTILITY_FAIL
Alle sieben Varianten haben **identisch** Nutzen .708 und 5/10 entscheidungs-exakt (Cygnus, Equinox, Gemini, Indigo = Regeln stehen in der aktuellen Quelle; Juno = richtig UNKNOWN). both_exact ist nicht größer als best_solo → Gate FAIL.

## Sekundär
| | entscheidungs-exakt | falsch festgelegt | UNKNOWN |
|---|---|---|---|
| ohne Werkzeug (W1, je Variante) | 0/10 | 7–9/10 | 1–3/10 |
| mit Werkzeug (jede Variante) | 5/10 | **0/10** | 6/10 (davon 1 richtig) |

- Das Werkzeug beseitigt alle falschen Entscheidungen (56 → 0 über 70 Zeilen) und löst jede Episode, deren Regeln in der aktuellen Quelle stehen. Die Offline-Probe vor der Inferenz (Orakel-Extraktion) löst 10/10, wenn die frühere Regel als verifiziertes Zitat ankommt.
- **Die frühere Regel kommt in keiner der 6 „Regel behalten“-Episoden bei C3 an, in keiner Variante.** Alle 8 Zeilen, in denen ein Zitat der früheren Regel C3 erreichte, sind Überschreibungs-Episoden (Regel dort überholt); das Werkzeug hat sie dort richtig ignoriert (aktuelle Regel gewinnt).
- Zusätzlich sind die Zitate abgeschnitten: `offer_schema(160)` begrenzt jedes Zitat auf 57 Zeichen, ein vollständiger Regelsatz („Project Aurora. Budget 100 euros. Deadline 5 days. Local-only requirement: true.“) hat ~80. Beobachtet: „…Deadline 11 days. Local“. Selbst ein Zitat der richtigen Regel würde damit `local_only` verlieren → UNKNOWN.

## Folgen
- STEP2 bleibt UTILITY_FAIL. Mit Werkzeug ist die Konsumentenseite gelöst; der Zwei-Körper-Nutzen ist jetzt allein durch den Regel-Transport der Körper begrenzt (0/36 nötige Zeilen).
- Zwei konkrete Produzenten-Engpässe für das nächste vorregistrierte Paket: (1) Körper zitieren die frühere Regel nicht, wenn die aktuelle Quelle nur „Decide from the earlier project rules“ sagt; (2) Zitat-Obergrenze 57 Zeichen < ein Regelsatz. (2) allein bringt auf STEP2 heute 0 Gewinn, weil (1) nie ein Zitat liefert.
- Passt zu Thread H (WP-W2d): Konsumentenseite gelöst, Engpass Regel-Transport.
