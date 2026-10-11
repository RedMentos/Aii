# §99 Pflicht-Ablationen ohne Modell (WP-AB, 2026-10-10)

Code `code/v13/ablation99.py`, Lauf `code/scripts/ablation99_bench.py`, Tests `code/tests/test_ablation99.py`, Rohdaten `ablation99.json`.
Die echten Module laufen auf einem synthetischen, offenen Strom: Neuromod-Gate, FastForward-Lebenszyklus und AgeControl-Plastizität. Kontrollen und V13 sehen pro Saat genau denselben Strom. Lerner sind lineare NLMS-Prädiktoren (Dim 4), einer pro Pfad. 5 Saaten. „x/5“ heißt: In x von 5 Saaten war V13 besser.

**Grenze:** Gezeigt wird nur, dass der Code tut, was sein Design verspricht, und wo eine Kontrolle gleich gut oder besser ist. Über Lernqualität mit echten Modellen sagt das nichts.

## Strom (Eligibility + Modulatoren)
600 Ereignisse, 5 Pfade:
- **route:** echte Ergebnisse, Ziel springt bei der Hälfte.
- **memory_retrieval:** menschliche Korrekturen.
- **world_predictor:** 75 % Traum-Labels mit Bias, 25 % echte Ergebnisse.
- **c5_action_selection:** 20 % „erfolgreiche“, aber unsichere Aktionen mit Sicherheits-Veto.
- **output_adapter:** nur in den ersten 20 % aktiv, danach nur Eigen-Labels mit Bias.

Fehler = ‖θ−w‖²/‖w‖². Ein Wert von 0 bedeutet gelernt, 1 heißt „nie gelernt“, über 1 heißt „Falsches gelernt“.

| Arm | Mittel Endfehler | route nach Drift | world_predictor | c5 | output_adapter | Budget |
|---|---|---|---|---|---|---|
| **V13 Gate + Datenmix (volle Komposition)** | **0,17** | 0,98 | **0,08** | 0,002 | **0,74** | 0,52 |
| V13 Gate allein | 0,65 | 0,98 | 1,33 | 0,002 | 1,94 | 0,61 |
| gradient only (Faktor 1) | 0,77 | **0,85** | 1,77 | 0,020 | 2,05 | 1,00 |
| gradient only, gleiches Budget | 0,75 | 1,25 | 1,66 | 0,020 | 2,05 | 0,61 |
| random mask, gleiches Budget | 0,77 | 1,23 | 1,75 | 0,033 | 2,05 | 0,62 |
| recency only | 0,65 | 0,88 | 1,32 | 0,002 | 1,93 | 0,68 |
| scalar reward | 0,74 | 0,95 | 1,77 | 0,002 | 1,93 | 0,70 |
| human-only | 0,70 | 1,73 | 1,49 | 0,068 | 1,93 | 0,36 |
| outcome-only | 0,66 | 0,95 | 1,33 | 0,002 | 1,96 | 0,50 |

## Befunde
1. **Eligibility helps: nur gegen gradient only und random mask belegt (je 5/5), nicht gegen recency only.**
   - Gegen recency only gewinnt V13 nur 1/5, Endfehler 0,654 gegen 0,651.
   - Die zweite Zeitskala der Spur bringt hier nichts Messbares.
   - Der Gewinn gegen die Kontrollen kommt aus Veto und Modulator, nicht aus der Spur.
   - Nach dem Drift lernt V13 langsamer um als gradient only (0/5) und als recency only (0/5).
2. **Typed modulators help: belegt gegen scalar reward (5/5) und human-only (5/5), knapp gegen outcome-only (4/5).**
   - Gegen scalar reward liegt der Gewinn ganz bei den Traum-Labels: 1,33 gegen 1,77, weil die Quelle „dream“ das Gewicht 0 hat.
   - Human-only lässt ergebnisgetriebene Pfade verhungern (route 0,020 gegen 0,002).
   - Das Veto ist in allen drei Kontrollen aktiv. Es ist eine harte Regel und wird hier nicht ablatiert.
3. **Wichtigster Befund: Das Gate allein schützt nicht vor Traum- und Eigen-Labels.**
   - Das Gate wirkt pro Pfad und nicht pro Beispiel. Ein Pfad mit guter Ergebnis-Historie lernt daher auch seine Traum-Beispiele mit hohem Faktor.
   - In allen Gate-Armen lernen world_predictor und output_adapter Falsches (Fehler über 1).
   - Erst die vorhandenen v4-Datenmix-Quoten (`guards.enforce_data_mix`: Traum höchstens 5 %, Eigenes höchstens 10 %) holen das auf 0,08 / 0,74. Mit ihnen gewinnt V13 gegen jede Kontrolle 5/5.
   - Folge: Traum- und Eigen-Daten müssen vor jedem Trainingsjob durch `enforce_data_mix` beziehungsweise `weights.DENY_SOURCE`. Das Gate ersetzt diese Filter nicht.
   - `FLOOR` = 0,25 garantiert solchen Daten außerdem ein Viertel Budget.
4. **Proceduralization helps: belegt.**

   | Arm | Kosten/Turn | Fehler | Fehler nach Drift | Fehler bei salienten Turns | Schnellpfad |
   |---|---|---|---|---|---|
   | V13 | 1,43 | 0,7 % | 0,7 % | 2,3 % | 78 % |
   | volle Deliberation | 3,00 | 2,3 % | 2,4 % | 2,3 % | 0 % |
   | statische Abkürzung | 1,07 | 24,6 % | 39,4 % | 96,8 % | 97 % |

   - Gegen volle Deliberation spart V13 52 % Kosten und macht weniger Fehler, weil die kompilierte Regel keine Ausrutscher der Deliberation hat.
   - Die statische Abkürzung scheitert am Drift und an salienten Turns. V13 öffnet bei Fehlern wieder und lässt saliente Turns aus.
5. **Age helps stability: nicht belegt.**
   - In der verrauschten Phase ist Age schlechter als fixed conservative (0,18 gegen 0,09, 0/5) und nur knapp besser als permissive (0,22, 5/5).
   - Beim Lernen und nach dem Zielwechsel ist Age so schnell wie permissive. Das ist der gewollte Teil.
   - Ursache 1: Rauschen senkt die gemessene Kompetenz. Das führt zur Herabstufung, und eine niedrigere Stufe bedeutet höhere Plastizität. Diese Rückkopplung geht für Label-Rauschen in die falsche Richtung.
   - Ursache 2: Fehlschläge durch Rauschen öffnen über `repeated_errors` zusätzlich. Ohne Wiederöffnen (Arm `age_no_reopen`) liegt der Fehler bei 0,16 statt 0,18, das Grundproblem bleibt.
   - Höchste erreichte Stufe: 3 (mit Bau-Decke 5; die ausgelieferte Decke ist 0).

## Nachtrag: Age-Korrektur hinter Flag (`age_plasticity_policy`)
Umgesetzt in `code/v13/age.py`. Standard bleibt `boot`, also das Kanon-Verhalten. `stable_reopen` braucht deine Freigabe. Es ändert zwei Dinge:
- Nach einer Herabstufung gilt die Plastizität der höchsten zuvor erreichten Stufe weiter, mindestens 4 Nachweise lang.
- Freigegeben wird diese Sperre erst durch anhaltende Fehler (2 Fehlschläge in Folge). Ein einzelner Fehlschlag öffnet nicht mehr.

| Arm | Lernen | verrauscht | Zielwechsel |
|---|---|---|---|
| age (boot) | 0,024 | 0,182 | **0,025** |
| **age stable_reopen** | 0,024 | **0,138** (5/5 besser als boot) | 0,033 (5/5 schlechter als boot) |
| fixed conservative | 0,051 | 0,092 | 0,045 |
| fixed permissive | 0,025 | 0,221 | 0,023 |

**Ergebnis:**
- Unter Rauschen hilft es: 24 % weniger Fehler.
- Dafür passt sich das System nach einem echten Zielwechsel langsamer an. Es bleibt aber schneller als conservative.
- Gegen conservative in der verrauschten Phase ist das Ziel weiterhin nicht erreicht (0/5).
- Der Grund liegt tiefer: Age-Signale (Kompetenz aus dem eigenen Fehler) unterscheiden Label-Rauschen nicht von einer Verschiebung. Dafür bräuchte es eine Rausch-Schätzung, etwa Uneinigkeit bei wiederholten Eingaben.
- **Empfehlung:** `stable_reopen` erst nach einer Redmi- oder Echt-Lauf-Prüfung einschalten.

## Vorschläge (nicht umgesetzt, Kanon-Fragen)
- **Age:** als `stable_reopen` umgesetzt (siehe Nachtrag); offen ist eine Rausch-Schätzung.
- **Neuromod:** Den Gate-Faktor pro Beispiel mit dem Quellen-Gewicht multiplizieren, zusätzlich zum Datenmix.
- **Eligibility:** Zwei Zeitskalen erst behalten, wenn ein Strom mit verzögerter Belohnung einen Vorteil gegenüber recency only zeigt.
