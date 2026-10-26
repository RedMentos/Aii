# Befund WP-Z2l: Kombination ja, zweiter andersartiger Körper nein (2026-10-26)

Vorregistrierung `PREREG.md` (Commit `d09474ce`, vor Inferenz gepusht). Linux-Cloud, 4 CPUs, kein Redmi. 6 Läufe × 70 Zeilen (CS/DS × Seeds 41–43),
alle RECORDED, kein Abbruch. Kette: 1536 Zeichen + ganze frühere Quellen + Wächter + jüngster zitierter Regelwert.

## Ergebnis laut Vorregistrierung: `Z2L_COMBINATION_ONLY`
| Ketten-Nutzen (Cluster-Bootstrap, 10 Episoden) | Differenz [95 %-CI] |
|---|---|
| CS `both_exact` − bester Einzelkörper (b1_only) | **+.242 [+.150, +.325]** |
| CS `both_exact` − DS `both_exact` (zwei Körper vs. ein Körper/zwei Zustände) | +.036 [−.075, +.145] |
| CS `both_exact` − `same_policy_dual` | +.239 [+.144, +.328] |
| CS `both_exact` − DS `prompt_only_dual` | +.333 [+.228, +.433] |
| DS `both_exact` − sein bester Einzelkörper | +.208 [+.044, +.336] |

| | CS (zwei Körper) | DS (ein Körper, zwei Zustände) |
|---|---|---|
| Ketten-Nutzen `both_exact` / b1_only / b2_only | .739 / .497 / .125 | .703 / .494 / .131 |
| exakt `both_exact` (30 Zeilen) | 18 | 20 |
| davon REVISED / TWICE / LONG / CONFIRM | 3 / 4 / 6 / 5 | 4 / 6 / 5 / 5 |
| falsch festgelegt (Kette) | **0** | **0** |
| B2-Regelquote | .71 | **.95** |
Gültigkeit 100 %, Konsistenz und Struktur erfüllt.

## Was das heißt
- Die **Kombination** zweier Zustände mit getrennter Aufgabe (Details/Optionen vs. Regeln über die Zeit) schlägt jeden Einzelkörper deutlich, auch die
  Kontrollen mit gleicher Politik oder nur anderem Prompt. Das ist der erste klare STEP2-Kombinationsgewinn auf schweren, geänderten Regeln — mit 0
  falschen Entscheidungen.
- Ein **zweites, andersartiges Modell** (Qwen als B2) bringt dafür nichts messbar Zusätzliches: derselbe Körper (LFM2.5-1.2B) in zwei Zuständen wählt die
  Regel-Notizen sogar zuverlässiger (.95 vs .71). Für diese Aufgabe reicht ein Körper mit zwei Zuständen; das spart RAM und Ladezeit auf dem Handy.

## Grenzen
Werkzeug-Nutzen (Ketten-Neubewertung aufgezeichneter Extraktionen), nicht Endnutzer-Antwort; Linux-Cloud, kein Redmi; zehn Episoden eines Aufgabentyps
(Budget/Frist/Lokal). Der Kanon-STEP2-Gate wird hier nicht befördert. Schalter bleiben live Standard/aus.

## Empfehlung
Kandidat für das Handy: ein Körper, zwei Zustände, mit der Kette (Schalter `b2_context_chars` 1536, `b2_quote_select=pointer`, `b2_quote_slots` 4,
`b2_quote_choices=sources`, Werkzeug mit `history` + `rule_reader='newest_quoted'`). Vor dem Einschalten: Messung auf dem Redmi (Zeit, RAM) und
Entscheidung des Nutzers.

Daten: `code/bench-results/step2-z2l-chain-20261026/`; volle STEP2-Berichte im Projektordner `v13/bench-results/step2-z2l-chain-20261026/`.
