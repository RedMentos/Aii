# R4 Teil 3: C3-Token-Unsicherheit als Weck-Signal (2026-10-12, Thread K)

**Verdikt: SIGNAL_SUPPORTED, POLICY_NOT_SUPPORTED.** Vorregistrierung `preregistration.json` (sha256 `856c69a2…1240`, Commit `4802a23`, nach Seed 7, vor Seed 11), Bericht `report.json`.

**Aufbau.** Arm `c_native_only` aus Thread Gs R4 (`scripts/r4_wake_bench.py`) erneut, gleicher BENCH_CFG, echte C3 LFM2.5-350M (llama.cpp b10964, Cloud-CPU), Aufgaben `utility_bench2.tasks(7)` und `(11)`. Einziger Eingriff: Mess-Hook im Skript fügt `n_probs=1` an die gestreamte C3-Antwort und liest `completion_probabilities` mit; **Antworten bytegleich zu G (60/60 je Seed)**. Sechs feste Merkmale. Auswahl nur auf Seed 7: bestes Merkmal `digit_min_logprob` (kleinste Token-Wahrscheinlichkeit unter Tokens mit Ziffer, Train-AUROC .93), Schwelle für die Politik „bei Unsicherheit beide Körper wecken“ (Ergebnis aus Gs aufgezeichnetem `always_ab`-Arm).

**Frische Aufgaben (Seed 11).**

| | Wert |
|---|---|
| AUROC „C3 allein liegt falsch“ (`digit_min_logprob`) | **0,84** (95-%-Untergrenze 0,73) |
| andere Merkmale (mean / p10 / Anteil p<.5 / min / Länge) | 0,81 / 0,80 / 0,80 / 0,70 / 0,66 |
| Politik bestanden | 42/60 (= C3 allein 42; Heuristik 33; immer A+B 38) |
| geweckt | 2/60 Turns, 6,7 s/Turn statt 23 s (Heuristik) |
| rettbare Aufgaben (C3 falsch, A+B richtig) | 3, davon 0 geweckt |

**Lesart.** C3 „weiß“, wann seine Zahlen-Antwort wackelt: die Unsicherheit der Ziffern-Tokens trennt richtige und falsche Antworten gut und überträgt sich auf frische Aufgaben. Als Weck-Regel bringt das trotzdem nichts, weil die Körper die Fehler von C3 kaum beheben (nur 3 von 18 C3-Fehlern rettet „immer A+B“, und gerade die sind nicht unter den unsichersten). Engpass ist also nicht das Erkennen, sondern was danach passiert.

**Folge (nicht umgesetzt, Vorschlag).** Das Signal eher für (a) ehrliche Unsicherheitsangabe/Rückfrage in der Antwort oder (b) Nachrechnen über das deterministische Werkzeug `eligibility`/Rechnen (WP-W2c) nutzen statt Körper zu wecken; beides braucht eigene Vorregistrierung. Keine Runtime-Änderung; Mess-Hook bleibt im Skript.

**Grenzen.** Generierte englische Aufgaben, Regex-Prüfung, ein frischer Seed, Cloud-CPU; Politik-Ergebnis kontrafaktisch aus Gs aufgezeichneten Armen (A+B ist nicht deterministisch). Kein Redmi.

Reproduktion: `scripts/r4_c3_uncertainty_wake.py capture|prereg|evaluate` (Docstring), Tests `tests/test_r4_c3_uncertainty_wake.py` (4).
