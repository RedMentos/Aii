# STEP2-Produzent: B2 ohne body_state — Befund (Thread O, 2026-10-13)

Vorregistrierung `PREREG.md` (Commit `1d8b739`, vor Inferenz gepusht). Daten `v13/bench-results/step2-body-state-ablation-20261012/step2_nobs.json`,
Werkzeug-Replay `tool_report.json` (+ Prereg). 70 + 70 Zeilen RECORDED, Artefakte unverändert, Linux-Cloud, kein Redmi.
Vergleichsarm: `step2-wire-rebind` w1 (gleiche Modelle, Runner, Fixtures, Seed; nur `body_state` für B2 entfernt).

## Sekundär (a)–(c) — Erwartung bestätigt
| | w1 mit body_state | B2 ohne body_state |
|---|---|---|
| B2-Offers über eigenen Zustand | 41/50 | **0/50** |
| frühere Regel als Zitat bei C3, „Regel behalten“ | 0 Zeilen | **13 Zeilen** (b2_only 5/6 Episoden) |
| frühere Regel als Zitat, Überschreibung | 8 | 11 |
| mit Werkzeug entscheidungs-exakt je Variante | 5/10 | 4–5/10 |
| mit Werkzeug falsch festgelegt | 0 | 0 |

- **body_state kapert den B2-Prompt:** ohne ihn zitiert Qwen3.5-0.8B die frühere Regel in 13 Zeilen statt 0, und die Extraktion liest in allen 13 Zeilen Budget/Frist/Lokal richtig.
- **Die 57-Zeichen-Zitatkappe frisst den Rest:** alle 13 Zitate enden bei „… Local-“ oder früher → Wächter lehnt `local_only` ab → UNKNOWN. Daher mit Werkzeug kein Gewinn.
- **Gegenprobe (nicht vorregistriert, obere Schranke, offline):** setzt man in diesen 13 Zeilen statt des abgeschnittenen Zitats den vollständigen Satz ein, mit dem das Zitat beginnt, sind **13/13 entscheidungs-exakt** (b2_only +5, both_none +3, both_control +3, both_exact +2).

## Primär
- Ohne Werkzeug meldet der Harness **UTILITY_PASS_SCOPED** (both_exact .667 > best_solo .650 > prompt_only .642 > same_policy .617; B1 und B2 gewinnen je eine Episode). **Nicht als Nutzen werten:** 0/70 exakte Entscheidungen, Vorsprung .017 bei n=10, reine Teilpunkte (C3 sagt 63/70 NONE). Der Harness zählt Teilpunkte; dieser PASS ist ein Rauschen-Treffer, kein Kanon-Gate (`canonical_gate_pass` bleibt false).
- Mit Werkzeug **TOOL_UTILITY_FAIL** (alle Varianten ≤ .708, both_exact = best_solo).
- Auch mit vollständigen Zitaten würde das Gate fallen: b2_only wäre allein am besten; B1 hat in diesen Fixtures keine eigene Information.

## Folgen
1. Kandidat für den Live-Code (getrennt vorregistrieren): `body_state` aus dem B2-Offer-Prompt nehmen (oder nach `earlier_context`) **und** die Zitatkappe in `cognition.offer_schema` auf mindestens einen Regelsatz (~90 Zeichen) heben.
2. STEP2-Fixtures prüfen keine B1-Komplementarität; für eine echte Zwei-Körper-Aussage braucht es Fixtures mit B1-eigener Information (Detail außerhalb der B2-Sicht).
