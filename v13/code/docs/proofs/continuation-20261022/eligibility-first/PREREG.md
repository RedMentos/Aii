# Vorregistrierung: Werkzeug-Entscheidung vorn + fester Regel-Leser (2026-10-22)

Vor dem frischen Lauf geschrieben und gepusht. Linux-Cloud, C3 LFM2.5-350M (Runner b10964), kein Redmi, kein Gate.

## Problem
Thread Q (`eligibility-whole-turn-q`, Saat 29): Das Rezept irrt nie (0/60 falsch), aber C3 behält im Antworttext oft die
eigene Entscheidung (richtig nur 32/60, sichtbar richtig 53/60 erst durch die nachträgliche Broker-Korrektur). Außerdem liest
C3 Regeln falsch (Entscheidung UNKNOWN in 18 Aufgaben, die eine Regel hatten; geänderte Regel exakt nur 5/15).

## Änderung (beide Schalter Standard aus)
1. `eligibility_reader=fixed`: Regeln liest `eligibility.read_fixed` (Regex, nicht generativ; Nutzerentscheidung 21.10.:
   Regeln nie von einem Sprachmodell). Aktuelle Nachricht schlägt frühere; zwei Werte in einem Text → kein Wert. Optionen
   ebenso, wenn die Formulierung abgedeckt ist (dann kein C3-Lese-Aufruf), sonst liest C3 nur die Optionen.
2. `tool_answer_first=true`: Der Entscheidungssatz des Rezepts ist der erste sichtbare Satz (`ToolStep.lead`), C3 erklärt
   danach. Bei UNKNOWN/NONE ist der feste Text die ganze Antwort (`lead_final`: fehlende Regel nennen und erfragen bzw.
   Optionen mit Grund), ohne C3-Fortsetzung. Runtime-Zeile als Kettenglied `integrated_candidates.tool_answer_first`.

## Entwicklung (Saat 7, 3 je Art, nur Verdrahtung)
- Iteration 1 (`dev-iterations/dev7-iter1.*`): C3 setzte nach „I cannot decide yet“ in 2/3 fehlenden-Regel-Aufgaben trotzdem
  eine Option fort → Fix 2b (UNKNOWN/NONE ohne Fortsetzung).
- Iteration 2 (`dev7.*`, Grundlage dieser Registrierung): richtig c3_alone 5, tool_model 6, tool_fixed 7,
  **tool_fixed_first 12/12**, falsch festgelegt 0.

## Messung
`scripts/eligibility_first.py`, Aufgaben-Generator und Bewertung von Q unverändert (`eligibility_live.gen`, `answer_action`).
Frische Saat **41**, 15 je Art (complete/missing/earlier/override), 4 Arme je Aufgabe, neue Sitzung je Arm.
Hashes von Skript, Laufzeit-Code und Aufgaben in `prereg.json`.

## Entscheidungsregeln (fest)
- **FIRST_SUPPORTED**, wenn tool_fixed_first gegen tool_model im Antworttext: (a) Netto-Gewinne ≥ +10 und Vorzeichentest
  p < .05, (b) falsch festgelegt nicht höher, (c) Rezept nie falsch, (d) keine Art verliert netto mehr als 2.
- **FIXED_READER_SUPPORTED**, wenn Entscheidung richtig (tool_fixed) ≥ tool_model + 5 und Rezept nie falsch.
- Nur berichtet: c3_alone, sichtbar richtig mit Korrektur, je Art, Modell-Aufrufe, Zugzeit.

## Grenzen
Generierte englische Aufgaben genau in der Wortform, die der feste Leser abdeckt (das ist sein Vorteil und seine Grenze:
andere Wortformen → UNKNOWN oder C3-Optionslesen). Altersrecht nur für die Messung ersetzt. Kein Handy, nicht STEP2.
Bei FIRST_SUPPORTED schlage ich vor, beide Schalter im Handy-Paket einzuschalten (Nutzer hat am 22.10. „Ja, beide an im
Handy-Paket“ für das Werkzeug gewählt).
