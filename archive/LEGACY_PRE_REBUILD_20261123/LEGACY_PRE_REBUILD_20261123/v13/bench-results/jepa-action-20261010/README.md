# WP-T17: JEPA-Prädiktor für Handlungsfolgen (2026-10-10)

Script: `code/scripts/jepa_action_bench.py`, Tests `code/tests/test_jepa_action.py`.
Körper B2 = Qwen3.5-0.8B Q4_0, mean-pooled Taps (1024 dim). Sätze: `../jepa-ablation-20261010/sentences.json` (376, 16 Themen).
Handlungen (Ergebnis von C3 LFM2.5-350M geschrieben, `actions.json`, Erzeuger `gen_actions.py`): translate_de, question, negate, summarize.
Train 10 Themen, Test 6 andere Themen. 3 Seeds (13, 21, 34: Themen-Split + Projektion), Mittelwert ± Std.

| Arm | Handlung passiert? (AUROC) | Ergebnis zum Input? (AUROC) | inverses Modell (Zufall 0,25) | Vorwärts Top-1 |
|---|---|---|---|---|
| ohne Prädiktor, 16 dim | 0,50 | 0,80 | 0,25 | 0,46 |
| Mittelwert-Delta je Handlung, 16 dim | 0,78 | 0,92 | 0,88 | 0,54 |
| JEPA geteilt, BOOT (240 Schritte) | 0,66 | 0,90 | 0,84 | 0,51 |
| JEPA geteilt, lang EMA | 0,81 | 0,81 | 0,57 | 0,15 |
| JEPA geteilt, SIGReg | 0,69 ± 0,11 | 0,94 | 0,70 ± 0,18 | 0,56 |
| JEPA je Handlung getrennt (Laufzeit-Optimierer unverändert) | 0,62 | 0,83 | 0,35 | 0,21 |
| ohne Prädiktor, 128 dim | 0,50 | 0,79 | 0,25 | 0,59 |
| Mittelwert-Delta, 128 dim | 0,81 | 0,96 | **0,95** | 0,76 |
| JEPA geteilt SIGReg, 128 dim | 0,78 | **0,98** | 0,90 | 0,77 |
| Mittelwert-Delta, voller Raum | 0,80 | 0,97 | 0,94 | **0,82** |
| Ridge je Handlung, voller Raum | **0,88** | 0,90 | 0,83 | 0,51 |
| überwacht (Handlungs-Labels) | – | – | 0,98 | – |

Befund: Der aktionsbedingte Prädiktor lernt echte Handlungsfolgen (inverses Modell 0,84–0,90 statt 0,25 ohne Prädiktor),
schlägt aber die triviale Kontrolle „ein Mittelwert-Delta je Handlung“ in derselben Projektion nicht (einzige Ausnahme:
Inhalts-Prüfung 128 dim 0,98 vs. 0,96). Die Laufzeit-Form (linear, ohne Bias) muss einen konstanten Handlungs-Versatz über
die Projektion nachbilden; langes EMA-Training kollabiert dabei (Vorwärts 0,15). §99 „JEPA hilft“ für Handlungsfolgen:
**nicht belegt** (Prädiktor nötig gegenüber nichts, aber nicht besser als 4 Mittelwerte).

Grenzen: Handlungen sind Text-Umformungen, keine Werkzeug- oder Weltwirkungen; Ergebnisse von C3 geschrieben; letzte Schicht
mean-pooled; 3 Seeds.
