# Befund WP-Z2c: gezielte Körper-Frage als Live-Schalter (2026-10-21)

Folge von WP-Z2b (gezielte Frage +.23 both_exact, CI > 0, 0 falsch festgelegt). Linux-Cloud x86_64, 4 CPUs, **kein Redmi**.
Gleiche Modelle/Runner wie Z2b (frisch per `v13.bootstrap` installiert), gleiche 10 Z2-Episoden, Arm-C-Einstellungen, Seed 14.

## Schalter (Code, Commit `061d778`)
- `cfg body_question_b1` / `cfg body_question_b2`: Text 0–400 Zeichen, **Standard `''` = aus = Live-Pfad unverändert**.
- An: jedes Körper-Angebot dieser Rolle ohne Rückfrage-Fokus bekommt die feste Frage als `jef_query` (kind `FILL_GAP`,
  reason `CFG_STANDING_QUESTION`, authority `EXECUTIVE_QUESTION_NOT_FACT`) – derselbe QUERY_PACKET-Pfad wie der Z2b-Skript-Patch.
  Ein echter Rückfrage-Fokus (Re-Entry) gewinnt immer. Frage ist nie Fakt.
- Kettenglied `integrated_candidates.body_question`; Tests `tests/test_body_question.py`. Volle Suite 1608, nur der bekannte alte Fehler `test_neuro_ledger`.
- Einschalten (Z2b-Text) in `config/settings.json`: `"body_question_b1": "<Text aus scripts/step2_z2b_seeds.py QUESTIONS['B1_DETAIL']>"`.

## Bestätigungslauf (`scripts/step2_z2c_switch.py`, vor dem Lauf gepusht, ein Seed, kein Gate)
Unterschied zu Z2b: der Schalter fragt auch in den vorbereiteten früheren Runden, nicht nur in der aktuellen.

| Lauf (Seed 14) | b1_only | b2_only | both_exact | B1-Optionszitate* | B2-Regelzitate* |
|---|---|---|---|---|---|
| C (Z2b, ohne Frage) | .275 | .242 | .375 | 18 | 20 |
| CQ (Z2b, Patch, beide) | .600 | .208 | .675 | 59 | 17 |
| **CL (Schalter, beide)** | **.575** | .200 | **.592** | 52 | 15 |
| **CB1 (Schalter, nur B1)** | **.575** | .258 | .450 | 50 | 14 |

\* Zeilen mit verifiziertem Zitat, Summe über alle Varianten.

- Der Live-Schalter reproduziert den Effekt weitgehend: b1_only +.30, both_exact +.22 gegenüber C; B1 zitiert Optionswerte fast so oft wie im Z2b-Patch.
- Nur-B1 bringt denselben B1-Gewinn; both_exact fällt aber auf .450 (ein Seed, 10 Episoden – innerhalb des Z2b-Rauschbands von ±.07 nicht sicher trennbar).
- **0 falsch festgelegt** in 140 Werkzeug-Zeilen. STEP2 bleibt UTILITY_FAIL; B2-Regelzitat bleibt der Engpass.

## Grenzen
- Die Frage ist STEP2-spezifisch (Optionen A/B, Budget/Frist/lokal). Für normalen Chat gibt es keine gemessene allgemeine Frage → Schalter bleibt aus.
- Ein Seed, Linux statt Redmi; Seed-Bug in `cognition.offer` (Körper immer Seed 13) bleibt offen, hier wie in Z2b im Skript überbrückt.
