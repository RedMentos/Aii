# Befund: Werkzeug-Entscheidung vorn + fester Regel-Leser (2026-10-22)

Vorregistriert in `6d278e5` (vor dem Lauf gepusht), frische Saat 41, 60 Aufgaben, 4 Arme, C3 LFM2.5-350M, Linux-Cloud.
Daten `fresh41.json`/`.log`, Auswertung `report.json` (Hashes von Prereg, Skript und Code geprüft).

## Urteile
- **FIRST_SUPPORTED** (alle vier Kriterien): Antworttext richtig **59/60** (tool_model 23, c3_alone 18), Netto +36 gegen
  tool_model (36:0, p < .0001), falsch festgelegt **0** (tool_model 30, c3_alone 37), Rezept nie falsch, keine Art verliert.
- **FIXED_READER_SUPPORTED**: Entscheidung des Rezepts richtig **60/60** mit festem Leser gegen 42/60 mit C3-Leser,
  0 falsch. Geänderte Regeln: 15/15 statt 4/15.

| Art (je 15) | c3_alone | tool_model | tool_fixed | tool_fixed_first |
|---|---|---|---|---|
| complete | 8 | 11 | 13 | 15 |
| missing (richtig = „kann nicht entscheiden“) | 0 | 1 | 0 | 15 |
| earlier | 7 | 8 | 10 | 15 |
| override | 3 | 3 | 6 | 14 |
| sichtbar richtig mit Korrektur | – | 48 | 60 | 60 |
| Median Zugzeit (s) | 2,0 | 3,0 | 2,0 | 1,6 |

## Was das heißt
- Der feste Leser allein hebt die Entscheidung auf 60/60, aber C3 schreibt trotzdem oft seine eigene Wahl (29/60): das
  Lesen war ein Engpass, das Übernehmen der zweite.
- Erst „Entscheidung vorn“ bringt den Antworttext selbst auf 59/60; die nachträgliche Korrektur wird überflüssig.
- Ein Rest: `override06` — nach „Choose Option A.“ schreibt C3 „Choose Option B.“ (Parser: keine eindeutige Wahl, nicht
  falsch gezählt; der Broker meldet den Widerspruch und hängt die Korrektur an). Bei UNKNOWN/NONE gibt es keine
  C3-Fortsetzung mehr, dort ist dieser Fehler ausgeschlossen.
- Kein C3-Lese-Aufruf mehr in dieser Wortform: Zug schneller (1,6 s statt 3,0 s).

## Grenzen
Generierte englische Aufgaben in genau der Wortform, die der feste Leser abdeckt. Andere Formulierungen ergeben UNKNOWN
(Regeln) oder C3 liest nur die Optionen. Altersrecht nur für die Messung ersetzt. Kein Handy-Wert, nicht STEP2.
`model_generated` steht bei festen Ganz-Antworten (UNKNOWN/NONE) noch auf true; Kennzeichen ist `tool_answer_first='FINAL'`.

## Folge
Laut Nutzerentscheidung 22.10. („Ja, beide an im Handy-Paket“) und 21.10. (Regeln nie von einem Sprachmodell): Standard
jetzt `eligibility_reader=fixed`, `tool_answer_first=true` (alte Werte in `LEGACY_PRE_20261022`). Das Werkzeug selbst bleibt
aus, bis der Nutzer `:growth enable eligibility` gibt; Age 0 = SHADOW. Nächster Schritt: Handy-Paket (WP-Z7) mit beidem,
und Wortformen außerhalb der Vorlage über den Regel-Leser-Strang (WP-Z3c/UR).
