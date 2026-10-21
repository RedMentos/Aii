# WP-Z3c Erweiterbarer Regel-Parser — Befund (2026-10-21)

**Vorregistriertes Urteil: `PARSER_V2_CARRIES_AUTHOR_ONLY`; sekundär `C3_TRAINING_NOT_NOW`.**
Kein Gate, keine Autorität; STEP2 `UTILITY_FAIL` unverändert. Reihenfolge laut Git: Vorregistrierung + versiegelter
Autor-Holdout `62c5c7f` → Parser eingefroren `dac892a` (`freeze.json`) → Modell-Holdout Runde 1 + Audit `cc34bda` →
Nachtrag A1 `92d87ce` → Runde 2 + Audit `40e0618` → C3-Probe und Lauf. Report `run/report.json`, Zeilen `run/rows.json`,
Kohorte `run/cohort.json`. Linux-Cloud-CPU, kein Redmi; der Parser selbst braucht kein Modell und läuft in Millisekunden.

## Ergebnis (je Kohorte, eine Zeile je Aufgabe, Parser deterministisch)

| Kohorte | n | Parser v1 (fest) exakt | Parser v2 exakt | v2 falsche Wahl | trägt (≥ 0.80 / ≤ 0.05) |
|---|---:|---:|---:|---:|---|
| dev kanonisch (Regression) | 39 | 1.000 | **1.000** | 0 | ja |
| dev Z3b-Paraphrasen | 39 | 0.154 | **1.000** | 0 | ja (Entwicklungsdaten) |
| **Autor-Holdout** (frisch, versiegelt) | 57 | 0.316 | **0.912** [0.81, 0.96] | **1** (1.8 %) | **ja** |
| **Modell-Holdout** Runde 2 (B1) | 22 | 0.273 | 0.318 | 0 | nein, und unterbesetzt (< 30) |
| Modell-Holdout Runde 1 (B1) | 11 | 0.273 | 0.273 | 0 | nein, unterbesetzt |

Autor-Holdout im Einzelnen: 26/30 normale Aufgaben, 3/3 fehlende Regel, 3/3 Widerspruch, 3/3 exakte Kontrolle,
6/6 „Köder zusätzlich“ (z. B. „Last year the budget was 64 euros.“ neben der echten Regel), 11/12 „Köder statt Regel“.
Lese-Treffer v2: Budget 0.89, Frist 1.00, Lokal 1.00 (alle 16 Ja/Nein-Formen inkl. Verneinungen wie
„We do not accept non-local options.“, „Options that are not local cannot be chosen.“, „Locality is not a requirement.“).

## Was das heißt
1. **Auf frischen Formen, die der Autor schrieb, trägt der Parser:** 0.91 exakt statt 0.32. Alle vier Fehlschläge sind
   dieselbe Redewendung „Funding tops out at N euros.“ — bewusst nicht ins Lexikon aufgenommen, weil sie nur im Holdout
   vorkam. Der Parser sagt dort `UNREADABLE` → UNKNOWN, keine falsche Wahl.
2. **Eine falsche Festlegung:** „Nobody has decided whether the budget should be 102 euros.“ wurde als Budget 102
   gelesen (Köder-Erkennung kennt „not decided“, aber nicht „nobody has decided“). 1/57 liegt unter der 5-%-Schwelle,
   zeigt aber genau das Restrisiko: ein Köder-Satz, der wie eine Regel aussieht, ist der einzige Weg zu einer falschen Wahl.
3. **Auf Sätzen eines Modells trägt er nicht.** B1 hat in zwei Runden die Regeln umformuliert; nur 11 bzw. 22 von 39
   Aufgaben blieben bedeutungsgleich (B1 macht aus „nur lokal“ oft „lokale Vorschriften“ oder „die Regel gilt überall“),
   also unterbesetzt. Dort liest v2 Budget 0.86 und Frist 1.00, aber Lokal nur 0.18: B1 schreibt „things available
   nearby“, „within the area you're in“, „content from anywhere“, „The local-only requirement is true.“ — Wörter, die
   das Lexikon nicht kennt. In allen diesen Fällen sagt v2 UNKNOWN, **0 falsche Wahl auf beiden Modell-Runden**.
   Satz-Ebene (deskriptiv, nicht registriert, `run/sentence_level_descriptive.json`): von den bedeutungsgleichen
   B1-Sätzen liest v2 47/57 Budget-, 34/36 Frist- und 1/9 Lokal-Sätze richtig, **0 falsch**, der Rest wird verweigert.
4. **C3-Lese-Training lohnt jetzt nicht** (`C3_TRAINING_NOT_NOW`, Probe `run/probe/`): C3 sollte 20 einzelne Sätze
   (16 Lokal-Regeln, 4 Köder) × 3 Seeds als true/false/null lesen. Antworten: 57× `true`, 3× `false`, 0× `null`.
   0.56 „richtig“ ist nur die Hälfte wahrer Sätze plus Zufall, und kein einziger Köder wurde als „nicht entschieden“
   erkannt. Es gibt kein Signal, das ein kleines Training verstärken könnte; der Parser liest dieselben 16 Sätze 16/16.

## Entscheidung
- Parser v2 ersetzt v1 als Regel-Leser für den Eligibility-Pfad **nur im SHADOW-Sinn**: er ist auf kanonischen und
  Autor-Formen sicher besser, auf fremden Formulierungen aber noch zu lückenhaft (Lokal-Wortschatz). Die Sicherheit
  hält überall (v2 verweigert statt zu raten), bis auf Köder-Sätze, die wie Regeln klingen.
- Erweitern geht nur über `parser_v2.extend()` mit Beleg je Eintrag; Holdout-Sätze sind als Beleg gesperrt (der
  Validator lehnt sie ab). Die hier gefundenen Lücken (`tops out`, `nobody has decided`, `nearby`/`area`/`anywhere`,
  „requirement is true“) sind damit Entwicklungsdaten für ein **neues Paket mit neuem Holdout**, nicht Nachbesserung hier.
- Für einen echten fremden Holdout taugt B1 als Umformulierer nur halb (die Hälfte der Lokal-Sätze verliert die
  Bedeutung). Besser: Sätze, die der Nutzer selbst schreibt, oder ein stärkeres Modell nur in der Cloud als Generator.

## Grenzen
- Der Autor-Holdout wurde vom Parser-Autor geschrieben und vor dem Parser gelesen; der Hash beweist nur, dass er danach
  nicht geändert wurde. Einige allgemeine Lexikon-Einträge (z. B. „excluded“, „optional“, „on-site“) kommen auch dort
  vor. Deshalb gilt das Urteil ausdrücklich nur „AUTHOR_ONLY“.
- Modell-Holdout unterbesetzt (22 < 30), Bedeutungs-Audit von mir (vor dem Lauf, Labels in den Audit-Dateien).
- Eine Aufgabenart (Budget/Frist/Lokal), Englisch, Optionssätze kanonisch, Cloud statt Handy.
