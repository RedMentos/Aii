# WP-Z3c Erweiterbarer Regel-Parser — Vorregistrierung (2026-10-21, vor jedem Parser-Code und jedem Modelllauf)

Baut auf Z3b (`PARSER_SUFFICIENT_NO_C3_GAIN`, Draft-PR #12): der feste verankerte Parser liest die kanonische Wortform
117/117 exakt, fällt auf umformulierten Regeln aber auf 0.154 (nur die UNKNOWN-Kontrollen richtig). C3-350M liest
`local_only` gar nicht (konstant `true`). Diagnostik, **kein Gate**: STEP2 `UTILITY_FAIL` bleibt, nichts wird eingeschaltet.

## Frage
Trägt ein **erweiterbarer** deterministischer Regel-Parser (Lexikon als Daten mit Beleg je Eintrag, Verneinung,
Synonyme, „Regel erkannt, aber nicht lesbar“ → UNKNOWN) auf **frischen** umformulierten Aufgaben, die beim Schreiben des
Parsers nicht als Entwicklungsdaten dienten? Optional: lohnt ein kleines Lese-Training für C3?

## Daten (Reihenfolge ist Teil der Registrierung)
1. `dev` — Entwicklungsdaten: Z3b-Kohorte `canonical` (39) und `paraphrase` (39, 16 Vorlagen) byte-gleich.
   Der Parser darf daran (und an selbst ausgedachten Testsätzen) entwickelt werden.
2. `holdout_author` — **dieser Commit**, vor jeder Zeile Parser-Code: `holdout_author.json`
   (sha256 `f8136999ba7c6dc1e30920234b2594f9a502fba397edbb9d5b9b2e06e0f34ba4`). 32 neue Einzelformen (8 je
   Regel/Polarität, disjunkt zu Z3b), 4 Doppelformen (Frist + Lokal in einem Satz, Anteil 0.33), 12 Köder-Sätze
   (unentschieden / Vergangenheit / abgelehnter Vorschlag, mit Köder-Zahl). Kohorte (Seed 20261022):
   39 umformulierte Basis-Fixtures (gleiche Werte, gleiche Orakel) + 12 `decoy_missing` (eine Regel durch einen Köder
   ersetzt → Orakel UNKNOWN) + 6 `decoy_extra` (Köder zusätzlich zur echten Regel, Orakel unverändert) = 57.
   **Ehrliche Grenze:** derselbe Autor hat diese Formen gesehen, bevor er den Parser schreibt. Der Hash beweist nur,
   dass sie danach nicht geändert wurden. Deshalb zusätzlich:
3. `holdout_model` — erst **nach** dem Einfrieren des Parsers (Parser- und Lexikon-Hash in einem eigenen Commit):
   B1 (LFM2.5-1.2B, gepinnt wie Z3) formuliert jeden Regelsatz der 39 Basis-Fixtures um.
   Prompt: „Rewrite this project rule in different words. Keep the meaning and keep every number exactly. Answer with
   one sentence.“ JSON-Schema `{sentence: string}`, Temperatur 0.7, Seed 20261023 + Versuch, höchstens 3 Versuche je Satz.
   Automatischer Filter: genau die Zahlen des Originals, keine verankerte Kanon-Form, ein Satz, ≤ 30 Wörter.
   Danach Bedeutungs-Audit durch mich **vor** dem Parser-Lauf auf dieser Kohorte (`same` / `changed` / `unclear`,
   Datei committet vor dem Lauf). Fixtures mit `changed`/`unclear`/Filter-Fehlschlag werden ausgeschlossen und gezählt.
   Unter 30 verbleibenden Fixtures gilt die Kohorte als unterbesetzt (wird so berichtet, kein Urteil darauf).

## Arme
- `parser_v1` — Z3b-Parser (verankert), Basislinie.
- `parser_v2` — neuer erweiterbarer Parser, deterministisch, kein Modell. Entscheidung über denselben Rezept-Pfad
  (`eligibility-v2` Rezept, Optionen nur aus dem eigenen Satz, CONFLICT/fehlend → UNKNOWN).
- optional `c3_probe` (Satz-Ebene, kein Entscheidungsarm): C3 klassifiziert jeden Lokal-/Köder-Satz der
  `holdout_author`-Kohorte einzeln als `true`/`false`/`null` (Seeds 13/14/15, Temperatur 0.1).

## Metriken
Je Kohorte und Arm (Parser deterministisch, also n = Fixtures, keine Seeds): Entscheidung exakt (alle Felder außer
`project`), falsche Festlegung (A/B/NONE ≠ Orakel), UNKNOWN-Kontrollen richtig, Lese-Treffer je Regel, Wilson-95-%-KI.

## Entscheidungsregel (Schwellen vorab: ≥ 80 % exakt, ≤ 5 % falsche Wahl)
„trägt“ = Entscheidung-exakt ≥ 0.80 **und** falsche Festlegung ≤ 0.05 auf einer Kohorte.
Regression: `parser_v2` muss auf `dev/canonical` 39/39 exakt mit 0 falsch bleiben, sonst sofort `PARSER_V2_REGRESSION`.
1. Regression → `PARSER_V2_REGRESSION`.
2. Falsche Festlegung > 0.05 auf irgendeiner Kohorte → `PARSER_V2_UNSAFE`.
3. Trägt auf `holdout_author` **und** `holdout_model` (nicht unterbesetzt) → `PARSER_V2_CARRIES`.
4. Trägt nur auf `holdout_author` → `PARSER_V2_CARRIES_AUTHOR_ONLY`.
5. Sonst → `PARSER_V2_SAFE_NOT_SUFFICIENT`.
Sekundär C3-Training: `C3_TRAINING_WORTH_A_PACKAGE`, wenn `parser_v2` nicht `CARRIES` ist **und** `c3_probe` auf
Lokal-Sätzen über Zufall liegt (Anteil richtig ≥ 0.50 bei 3 Klassen) **und** bei Ködern ≥ 0.50 `null` sagt;
sonst `C3_TRAINING_NOT_NOW`. Läuft die Probe nicht, `C3_TRAINING_NOT_ASSESSED`.
Kein Nachlauf mit geändertem Parser oder Lexikon unter dieser Registrierung; Lexikon-Erweiterungen nach dem Lauf
sind neue Entwicklungsdaten und brauchen eine neue Holdout-Kohorte.

## Grenzen
Eine Aufgabenart (Budget/Frist/Lokal), Englisch, Optionssätze kanonisch. Autor-Holdout vom Parser-Autor geschrieben.
Modell-Holdout von einem 1.2B-Modell, Bedeutungs-Audit durch mich. Cloud-CPU statt Handy.
