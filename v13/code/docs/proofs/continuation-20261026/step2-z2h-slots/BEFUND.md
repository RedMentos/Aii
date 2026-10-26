# Befund WP-Z2h: vier statt zwei Zeiger-Plätze bringen nichts — B2 wählt nach Position (2026-10-26)

Vorregistrierung `PREREG.md` (Commit `83c23664`, vor Inferenz gepusht). Linux-Cloud, 4 CPUs, kein Redmi. 6 Läufe × 70 Zeilen (P2/P4 × Seeds 29–31),
alle RECORDED, kein Abbruch. `b2_context_chars` = 1536, Zeiger an, Wächter an (Replay).

## Ergebnis laut Vorregistrierung: `Z2H_SLOTS_NO_GAIN`
| | P2 (2 Plätze) | P4 (4 Plätze) |
|---|---|---|
| Kickoff im Kontext | 100 % | 100 % |
| B2-Regelquote (alle aktuellen Regeln zitiert) | .233 | .275 — Differenz +.042 [−.083, +.158] |
| exakt bewacht in `both_exact` (3 Seeds) | 5 | 5 |
| alle Zeilen: falsch ohne → mit Wächter | 18 → **0** | 15 → **0** |
| alle Zeilen exakt (Wächter an) | 11/210 | 12/210 |
| gewählte Sätze je Angebot | 1,69 | 2,35 |
| überholte Werte in B2-Zitaten | 11 | 21 |
| Werkzeug-Nutzen `both_exact` / b1_only | .583 / .489 | .572 / .433 |
Je Typ (exakt mit Wächter): LONG 7 / 8, CONFIRM 4 / 4, **REVISED 0 / 0, TWICE 0 / 0**. Konsistenz und Struktur erfüllt, Plätze benutzt.

**Zweite Bestätigung des Wächters** auf wieder frischen Episoden: 33 falsche Festlegungen ohne, 0 mit, keine exakte verloren.

## Ursache, nachträglich gefunden (nicht vorregistriert, offen genannt) — `bench-results/.../pick_bias.txt`
B2 (Qwen3.5-0.8B) wählt die Sätze überwiegend **nach Position**: knapp die Hälfte aller gewählten Nummern sind 1–3 (das sind die Sätze der
*aktuellen* Aufgabe, die C3 ohnehin bekommt), in gut einem Drittel der Angebote schlicht „1, 2, …“. Bei REVISED/TWICE in P4: 88 gewählte Sätze aus
der aktuellen Aufgabe, 42 Datenblatt, 39 Kickoff, nur **9 aus der Änderungsnotiz**. Alle aktuellen Regeln zitiert: P2 0/15, P4 1/15 (`both_exact`).
Mehr Plätze füllt B2 mit weiteren vorderen Sätzen. Engpass ist also nicht die Anzahl der Plätze, sondern **welche Sätze zur Wahl stehen und in
welcher Reihenfolge**.

## Empfehlung
- `b2_quote_slots` bleibt Standard 2 (kein Gewinn, aber auch kein Schaden). Schalter bleiben live aus.
- Wächter: zweimal auf frischen Daten bestätigt — für jeden Lauf mit größerem B2-Budget Pflicht.
- Nächstes Paket **WP-Z2i**: Auswahlliste ohne die Sätze der aktuellen Aufgabe (C3 hat sie schon) und eine Variante mit jüngster früherer Quelle
  zuerst; vorregistriert, frische Episoden, Wächter an.

Daten: `code/bench-results/step2-z2h-slots-20261026/`; volle STEP2-Berichte im Projektordner `v13/bench-results/step2-z2h-slots-20261026/`.
