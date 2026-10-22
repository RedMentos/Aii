# WP-AGE0c Befund: späte Selbstkorrektur schlägt fast immer falsch an — `AGE0C_STAY_SHADOW`

Stand 2026-10-22. Vorregistrierung `PREREG.md` (Commit 73ef6f4, vor der Auswertung). Skript `scripts/age0c_false_alarm.py`,
Ergebnis `report.json`. Keine Modellläufe: vorhandene echte B1/B2-Angebote (LFM2.5-1.2B / Qwen3.5-0.8B) aus STEP2 und
Kalibrierung. Der echte Code (`late_offer`, Modus shadow) stimmt in allen 1137 Paaren mit dem Nachbau V0 überein.

## Zahlen (Alarm auf einer richtigen Antwort = Fehlalarm)

| Arm | Paare | V0 heute | V1 ohne needs_reentry | V2 + Echo-Filter |
|---|---|---|---|---|
| A-richtig (Lösung als JSON) | 263 | **100 %** | 28,9 % | 2,3 % |
| B-knapp (nur Lösung) | 237 | **40,9 %** | 29,1 % | 3,8 % |
| B-mit-Echo (Frage + Lösung) | 237 | **19,4 %** | 3,8 % | 3,8 % |
| A-echt: begründete Alarme | 400 / 67 / 5 Alarme | **0 %** | 0 % | 0 % |
| Trennschärfe falsch − richtig (gepaart) | 400 | **0 pp** | −5 pp | −0,25 pp |

Kriterien (K1 Fehlalarm ≤ 10 % / obere Grenze ≤ 15 %, K2 ≥ 50 % begründet, K3 ≥ 20 pp):
V0 K1 ✗ K2 ✗ K3 ✗ · V1 ✗ ✗ ✗ · V2 K1 ✓, K2 ✗, K3 ✗. **Keine Variante ist lieferbar, auch kein Kandidat.**

## Warum
1. **`needs_reentry` sagt nichts über die Antwort.** In allen 400 STEP2-Angeboten steht es auf `true` (B1 und B2), bei
   richtiger wie falscher Antwort. Der Körper sieht die Antwort nie; das Feld kann sie also gar nicht bewerten.
2. **Die „fehlenden Zahlen“ sind fast immer Echos der Frage.** Beispiel: B2 fasst „3 + 7“ zusammen, die richtige Antwort
   „10“ enthält weder 3 noch 7 → Alarm. Im STEP2-Fall nennt B2 das Budget „100 euros“, das in der richtigen JSON-Antwort
   nicht vorkommt.
3. **Der Echo-Filter (V2) macht den Erkenner still, nicht klug.** Er senkt die Fehlalarme unter 4 %, findet aber in 400
   falschen echten C3-Antworten keinen einzigen begründeten Fehler und schlägt bei richtiger und falscher Antwort gleich
   oft an.

## Folge
- `:self correction` bleibt **shadow**. `deliver` wird **nicht** empfohlen. Nichts wurde umgestellt.
- Der Fehler liegt nicht an Schwellen, sondern am Aufbau: eine späte Korrektur braucht eine Prüfung, **die die Antwort
  sieht** (z. B. Nachrechnen der Antwortzahlen mit dem Rechenwerkzeug, oder ein Körper, der Antwort + Quelle bekommt und
  einen konkreten Widerspruch mit Zitat nennen muss). Das ist ein neues Paket (WP-AGE0d), wieder mit Vorregistrierung und
  frischen Daten.

## Grenzen
Enge englische Aufgaben (Budget-Rechnung, kleine Rätsel), kein freier Chat; Angebote kamen vor der Antwort (live: gleiche
Eingabe nach der Antwort, ggf. mit Peer-Nachricht). Echte C3-Antworten waren alle falsch, daher misst A-echt nur die
Begründung. Nicht auf dem Redmi gemessen (nicht nötig: keine Modellrechnung, reine Wiedergabe).
