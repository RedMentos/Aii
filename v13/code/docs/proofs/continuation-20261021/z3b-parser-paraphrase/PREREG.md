# WP-Z3b Fester Parser vs. C3 als Regel-Leser — Vorregistrierung (2026-10-21, vor jedem Modelllauf)

Registrierung `registration.json`, SHA256 (kanonisch) `10cd00f1a591b6e956c25d1493517d0925fc120f5b032b6ca30c98ec979c49d9`.
Kohorte `cohort.json` (78 Fixtures, sha256 kanonisch `fef50135…`, aus dem Skript reproduzierbar).
Skript `z3b_parser_vs_reader.py`, Tests `test_z3b_parser_vs_reader.py` (9, nur Software). Diagnostik, **kein Gate**:
STEP2 `UTILITY_FAIL` bleibt, keine Autorität, nichts wird eingeschaltet.

## Frage
Z3 (`NO_CONSUMER_PATH`): C3 liest Budget, Frist und Optionswerte fehlerfrei, gibt aber `local_only` immer `true` zurück;
ein fester Parser liest die kanonische Wortform zu 100 %. Zwei Fragen:
1. (sekundär) Liest ein fester Parser die Ja/Nein-Regel `local_only` und C3 nur Zahlen/Optionen, trägt das dann auf der
   kanonischen Kohorte? (Z3-Nachanalyse sagte 117/117, war aber nicht registriert.)
2. (primär) Kann C3 als Leser **mehr als ein fester Parser**? Dazu dieselben 39 Fixtures mit **umformulierten Regeln**
   (gleiche Werte, gleiche Orakel), in Formen, für die der Parser nie geschrieben wurde, inklusive verneinter Ja/Nein-Regeln
   („Non-local options are not permitted.“ = true, „Remote options are allowed as well.“ = false).

## Aufbau
- Kohorte `canonical`: die 39 Z3-Fixtures byte-gleich. Kohorte `paraphrase`: jede private Regel-Aussage mit einer von
  4 Vorlagen je Regel/Polarität umformuliert (Seed 20261021, Vorlagen in der Registrierung). Software-Test: der Parser liest
  in keiner Paraphrase einen Wert; jede Zahl bleibt erhalten; Orakel unverändert.
- Lieferung wie Z3: aktuelle Quelle + beide privaten Quellen wörtlich (Store-validiert). Nur C3 LFM2.5-350M `3d10b6ab…`,
  Runner b10964 `79e31218…`, Linux-Cloud-CPU 4 Kerne, kein Redmi. Kalte Aufrufe, Seeds 13/14/15, Temperatur 0.1.
- Zwei Aufrufgruppen je Fixture und Seed (468 Aufrufe): `c3_extract` (Z3-Extraktion, Prompt und Schema byte-gleich) und
  `c3_rules` (neuer fokussierter Regel-Leser: nur budget/deadline/local_only, wortlaut-offene Anweisung, Widerspruch → null).
- Arme (deterministische Nachverarbeitung; ein Aufruf speist mehrere Arme, also kein Stichproben-Störfaktor):
  - `parser_only` — fester verankerter Parser, kein Modell (Basislinie)
  - `x_anchored_strict` — Z3 `c3_extract_tool_strict` wiederholt (verankerter Wächter ist selbst ein Parser)
  - `x_parser_bool` — C3-Zahlen/Optionen, `local_only` vom Parser, Z3-strict-Wächter (**Frage 1**)
  - `x_grounded` / `r_grounded` — C3-Werte mit nur wortlaut-unabhängigen Wächtern: Zahl muss in einem Zitat stehen;
    jede Zahl in den Zitaten muss einer angenommenen Regel zugeordnet sein (sonst UNKNOWN, fängt z. B. ein zweites Budget);
    Optionen im eigenen Satz. `local_only` ist ohne Parser **nicht prüfbar** und wird übernommen.
  - `x_hybrid` / `r_hybrid` — Parser zuerst; nur wo er nichts liest, der C3-Wert durch dieselben Wächter.
- Vorab erwartet: `parser_only` auf Paraphrasen = nur die 18 Kontrollzeilen exakt (0.154), 0 falsch. `x_anchored_strict`
  und `x_parser_bool` auf Paraphrasen ebenso UNKNOWN. `x_grounded` kanonisch mit vielen falschen Festlegungen, weil C3
  `local_only` laut Z3 immer `true` liest und hier kein Parser schützt.

## Metriken (vorab, wie Z3)
Entscheidung exakt (alle Felder außer `project`), falsche Festlegung (A/B/NONE ≠ Orakel), Aktion richtig, UNKNOWN-Kontrollen,
Lese-Treffer je Regel, je Seed; fehlgeschlagene Aufrufe zählen als falsch, nie verworfen.

## Entscheidungsregel (Schwellen vorab: ≥ 80 % exakt, ≤ 5 % falsche Wahl)
„trägt“ = Entscheidung-exakt ≥ 0.80 und falsche Festlegung ≤ 0.05, gepoolt 3 Seeds × 39 Fixtures einer Kohorte.
„Gewinn“ = gepaarter Bootstrap (über Fixtures) Arm − `parser_only` auf Paraphrasen, untere 95-%-KI-Grenze > 0.
1. Ein C3-Arm trägt auf Paraphrasen **und** kanonisch → `C3_READER_BEATS_PARSER`.
2. Sonst: ein C3-Arm hat Gewinn **und** ≤ 0.05 falsch auf beiden Kohorten → `C3_READER_PARTIAL_GAIN`.
3. Sonst → `PARSER_SUFFICIENT_NO_C3_GAIN`.
Sekundär: `x_parser_bool` trägt kanonisch → `BOOL_PARSER_FIX_CONFIRMED`, sonst `…_NOT_CONFIRMED`.
Kein Nachlauf mit geänderten Prompts, Vorlagen oder Wächtern unter dieser Registrierung.

## Grenzen
Vorlagen sind von mir geschrieben (16 Formen, eine Aufgabenart); ein Parser ließe sich auf genau diese Formen erweitern —
die Frage ist, ob C3 *ohne* solche Erweiterung liest. Die Optionssätze bleiben kanonisch. Zitat-Wächter decken nur Zitate ab
(die aktuelle Quelle nennt in dieser Kohorte keine Regeln). Cloud-CPU statt Handy; Seeds bei Temperatur 0.1 kaum unabhängig.
