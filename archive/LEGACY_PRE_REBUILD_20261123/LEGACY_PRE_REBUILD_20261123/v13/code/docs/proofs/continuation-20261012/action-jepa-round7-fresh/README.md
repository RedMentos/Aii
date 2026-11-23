# Action-JEPA Runde 7: frische Erfassung für das Runde-6-Objective

Vorregistriert in `preregistration.json` (GitHub `1914106`, vor Generierung, Welt und Erfassung). Kandidat `scripts/action_jepa_round6_ridge.py` unverändert (sha `acb8264e…`), gleiche Gates, Seeds 13/21/34, Arme `full`/`proj`.

## Ergebnis (54 Läufe)

| Familie | PASS | Urteil | Median Test-MSE / Mittelwert-Delta |
|---|---|---|---|
| Werkzeug-Welt (neue Startwerte, 1600 echte `calc`-Aufrufe) | **24/24** | **CONFIRMED** | 0.21 |
| Text-Handlungen (neue Themen) | 11/30 | NOT_CONFIRMED | 0.85 |

- Werkzeug: der gelernte Rest liegt pro Handlung bei 5–45 % des Mittelwert-Delta-Fehlers, Retention überall besser als die Kontrolle.
- Text: nur `l_out-11` letzter Token besteht stabil (6/6), dazu 3/6 `l_out-23` letzter Token (`full`) und 2/6 `l_out-11` Mittel; gemittelte End-Embeddings und `l_out-23` Mittel 0/6. Fehlschläge: Retention mit Delta 0 und das .98-Gate bei `negate`/`question`.

## Abweichungen

- Nur 3 von 8 Themen lieferten ≥ 16 Sätze von C3 (airports, swimming pools, post offices). Die vorregistrierte Reserve-Regel wurde angewandt; der Text-Test hat 72 statt 120 Episoden.
- Text-Train/Kalibrierung/Retention sind die plan-v2-Episoden der Runden 3/4 (Taps wertgleich neu erfasst); neu ist nur der Text-Test. Die Werkzeug-Welt ist komplett neu.

## Grenzen

Belegt ist nur: eine feste Mittelwert-Delta-Basis plus gelernter Ridge-Rest auf eingefrorenen nativen Taps sagt echte Werkzeug-Folgen besser voraus als alle Kontrollen. Keine Laufzeit-, Empfänger- oder Lernautorität, nicht auf dem Redmi gemessen, `canonical_architecture_complete=false`.

Rohdaten `raw-parts/` (ZIP `af3213c1…`: Generierung, Welt mit Transaktionen, alle Erfassungen), Ergebnisse `results-parts/` (ZIP `4e66fa56…`: 54 `metrics.json` + Checkpoints). Wiederherstellung mit `scripts/sealed_storage_parts.py restore`.
