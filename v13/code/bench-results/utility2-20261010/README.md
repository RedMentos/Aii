# Nutzen-Messung Runde 2 (WP-T3b, 2026-10-10, Pakete A)

Skript `code/scripts/utility_bench2.py`, Rohdaten `utility2.json` (mit `verdict`).

Aufbau:
- Echte Modelle C3, B1 und B2.
- Bench-Modus: Temperatur 0, C3 gierig (`legacy`), Frist 600 s, Observer-Budget 180 s.
- 60 generierte englische Aufgaben, 4 Arten × 15:
  - `summary`: falsche Summenzeile
  - `long`: Zahl im langen Text versteckt
  - `notes`: zwei widersprüchliche Notizen, die neuere gilt
  - `compare`: Maximum und Differenz
- Gepaart je Aufgabe, mit exaktem Vorzeichentest.

| Arm | bestanden | nur Arm | nur Baseline | p | identische Antwort | Angebote/Turn |
|---|---|---|---|---|---|---|
| baseline | 0,57 | – | – | – | – | 1,17 |
| baseline (Wiederholung) | 0,60 | 5 | 3 | 0,73 | 33/60 | 1,17 |
| effort_low (fest) | **0,70** | 14 | 6 | 0,12 | 6/60 | 2,0 |
| no_inquisition | 0,58 | 4 | 3 | 1,0 | 33/60 | 1,17 |
| no_coalition | 0,60 | 4 | 2 | 0,69 | 32/60 | 1,17 |

Nach Art (baseline → effort_low):
- summary 0,53 → 0,47
- long 1,0 → 1,0
- notes 0,60 → **0,93**
- compare 0,13 → **0,40**

## Befunde
1. **Der Bench-Modus ist nicht deterministisch.** Im Vorlauf waren 4/4 Antworten gleich. Über 60 Aufgaben weicht dieselbe Konfiguration aber in 27 Antworten ab und kippt 8 Bewertungen. Diese 8 sind das Rauschband.
   - Fristschnitte sind ausgeschlossen. Vermutete Ursachen: Prompt-Cache-Wiederverwendung im llama-server-Slot und der Hintergrund-Observer zwischen den Turns. Nicht geprüft.
2. **Koalition und Inquisition:** kein messbarer Nutzen, beide liegen im Rauschband (G-FOCAL-CAPACITY-003 bleibt EVIDENCE_NOT_PASSING).
3. **Feste niedrige Effort-Stufe ist besser als die adaptive (+8 netto, p = 0,12, nicht signifikant).**
   - Sie weckt pro Turn beide Körper (2,0 statt 1,17 Angebote). Die adaptive Politik weckt meist nur B2.
   - Vorteil bei Widerspruch und Vergleich (notes, compare), kleiner Nachteil bei summary, etwa 5 s mehr pro Turn.
   - Hinweis: Die adaptive Effort-Politik ruft bei Detail-Aufgaben zu selten B1. Das ist ein Kandidat für die Effort-Einmessung (Daten liegen in `utility2.json`).
4. compare ist für alle schwach (0,13–0,40). Die Rechnung „größter minus kleinster Wert“ gelingt C3 selten.

## Grenzen
- Gierige Bench-Dekodierung statt des ausgelieferten anti_echo.
- Generierte Aufgaben, Regex-Prüfung nur der Endantwort, eine Saat.
