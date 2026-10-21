# WP-Z3b Fester Parser vs. C3 als Regel-Leser — Befund (2026-10-21)

**Status `RECORDED`, 1638/1638 Zeilen (78 Fixtures × 3 Seeds × 7 Arme), 468 native C3-Aufrufe, 0 Fehler, Bindungen
unverändert. Vorregistriertes Urteil: `PARSER_SUFFICIENT_NO_C3_GAIN`; sekundär `BOOL_PARSER_FIX_CONFIRMED`.**
Kein Gate, keine Autorität; STEP2 `UTILITY_FAIL` unverändert. Registrierung `10cd00f1…` (Commit vor dem Lauf),
Report `run/report.json`, Zeilen `run/rows.json.gz` (entpackt sha256 `d718e06c…` = `rows_sha256`). Linux-Cloud-CPU,
4 Kerne, kein Redmi, C3 byte-gleich zu Z3.

## Ergebnis (gepoolt je Kohorte, n = 117 je Arm)

| Arm | kanonisch exakt | kanonisch falsch | Paraphrase exakt | Paraphrase falsch | Δ zu Parser (Paraphrase, 95-%-KI) |
|---|---:|---:|---:|---:|---|
| parser_only (kein Modell) | **1.000** | 0.000 | 0.154 | 0.000 | — |
| x_parser_bool (C3-Zahlen, Parser-Bool) | **1.000** | 0.000 | 0.154 | 0.000 | 0.00 [0.00, 0.00] |
| x_anchored_strict (= Z3 strict) | 0.538 | 0.000 | 0.154 | 0.000 | 0.00 [0.00, 0.00] |
| x_grounded (C3 liest alles) | 0.744 | **0.256** | 0.410 | **0.077** | +0.26 [0.10, 0.41] |
| x_hybrid (Parser zuerst, sonst C3) | 0.923 | **0.077** | 0.410 | **0.077** | +0.26 [0.10, 0.41] |
| r_grounded (fokussierter Regel-Leser) | 0.598 | 0.043 | 0.154 | 0.000 | 0.00 [0.00, 0.00] |
| r_hybrid | 0.923 | **0.077** | 0.154 | 0.000 | 0.00 [0.00, 0.00] |

0.154 = nur die 18 UNKNOWN-Kontrollzeilen (fehlende/widersprüchliche Regel) richtig, alle entscheidbaren Aufgaben UNKNOWN.
Seeds 13/14/15 praktisch gleich (Temperatur 0.1). Kein C3-Arm trägt auf Paraphrasen (≥ 0.80 exakt). Die einzigen Arme mit
Gewinn gegenüber dem Parser (x_grounded/x_hybrid, +26 Punkte, KI > 0) legen sich in 7.7 % der Paraphrase-Zeilen falsch fest
(> 5 %) → kein `PARTIAL_GAIN`. Das Urteil gilt so, wie registriert.

## Was das heißt
1. **Frage 1 bestätigt (jetzt registriert):** Liest der feste Parser die Ja/Nein-Regel `local_only` und C3 nur Zahlen und
   Optionen, sind kanonisch 117/117 exakt, 0 falsch. Die Z3-Nachanalyse hält.
2. **C3 liest `local_only` überhaupt nicht.** Im Extraktionsaufruf kommt in 234/234 Zeilen (beide Kohorten) `true` zurück,
   egal ob dort „Local-only requirement: false“, „Remote options are allowed as well.“ oder gar nichts steht. Das ist eine
   Konstante, kein Lesefehler bei Verneinung. Auch der fokussierte Leser mit ausdrücklicher Erklärung von true/false liefert
   auf Paraphrasen 117/117 `true`.
3. **Zahlen auf neuen Formulierungen nur teilweise:** Budget 72 %, Frist 45 % richtig gelesen (kanonisch 92 %/100 %).
   Die wortlaut-unabhängigen Wächter (Zahl muss im Zitat stehen, jede Zitat-Zahl muss zugeordnet sein) verwerfen die
   meisten Fehlgriffe und fangen alle drei Widerspruchs-Kontrollen ohne Parser.
4. **Die falschen Festlegungen kommen alle von der Bool-Konstante:** auf Paraphrasen 2 Aufgaben mit erlaubten
   Nicht-lokal-Optionen und 1 Kontrolle mit fehlender Lokal-Regel (C3 erfindet `true`), je Seed. Ohne Parser gibt es für
   `local_only` keinen Wächter.
5. **Der fokussierte Regel-Leser ist schlechter als die Extraktion:** kanonisch liest er `local_only` zwar in 62 % richtig
   (einziger Arm mit `false`-Antworten, 35/117), das Budget aber nur zu 59 %, und erfindet bei fehlender Regel `local_only`; auf Paraphrasen gibt er meist `null` oder falsche Zahlen zurück (Wächter → UNKNOWN).
6. **Hybrid kanonisch 0.077 falsch:** wo der Parser `local_only` nicht findet (fehlende Regel), springt C3 mit seinem
   erfundenen `true` ein. Ein C3-Fallback für Ja/Nein-Regeln ist damit gefährlicher als UNKNOWN.

## Entscheidung (§29 Nr. 6, §31 R9 / §24.34)
- Für Entscheidungsregeln gilt: **Parser liest Regeln, C3 höchstens Zahlen in Optionssätzen.** C3 als Leser bringt auf
  umformulierten Regeln keinen sicheren Gewinn; der einzige Gewinn (+26 Punkte) kostet 7.7 % falsche Festlegungen.
- `local_only` (und jede Ja/Nein-Regel) **nie** vom C3-350M lesen lassen, auch nicht als Rückfall. Für den Live-Pfad
  (eligibility-v2, Branch dq33gk) heißt das: Bool-Regel deterministisch lesen, Rest wie Z3 strict.
- Nicht widerlegt: dass ein anderes Modell oder ein trainierter Leser Paraphrasen lesen kann. Weitere Wortformen
  brauchen dann einen erweiterbaren Parser (gelernte Muster mit Beleg) oder ein eigenes Lese-Training, beides neue Pakete.

## Grenzen
16 selbst geschriebene Vorlagen, eine Aufgabenart, Optionssätze kanonisch; Cloud-CPU statt Handy; Seeds bei Temperatur
0.1 kaum unabhängig. Kein Nachlauf unter dieser Registrierung.
