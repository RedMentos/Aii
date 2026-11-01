# Action-JEPA Runde 6: geändertes Objective (Mittelwert-Delta + Ridge-Rest)

Vorregistriert in `preregistration.json` (GitHub `9214a4c`, vor jedem Lauf). Skript `code/scripts/action_jepa_round6_ridge.py`, Tests `code/tests/test_action_jepa_round6_ridge.py` (5).

Objective: Vorhersage = `x@p + mean_delta[a] + (f - mu_a) @ W_a`. Mittelwert-Delta ist feste Basis, `W_a` ist die Ridge-Lösung auf Train (geschlossene Form), λ pro Handlung aus einem festen Raster inkl. λ=∞ (= reine Mittelwert-Delta-Kontrolle), gewählt nur auf Kalibrierung. Kein EMA-Ziel, keine Varianz-Untergrenze. Arme `full` (1024-d Tap) und `proj` (16-d Projektion). Bewertung, Kontrollen und Gates wie `action_jepa_objective.py`; das Gradienten-Gate ist durch eine Prüfung der Normalgleichungen ersetzt. `noncollapse` kann hier konstruktionsbedingt nicht scheitern.

## Ergebnis (54 Läufe, Seeds 13/21/34)

| Daten | Läufe | PASS |
|---|---|---|
| Runde 5 Werkzeug-Welt (`calc`), 4 Taps × 2 Arme | 24 | **24** |
| Runde 4 Text-Handlungen, Mittelschicht-Taps | 24 | 12 |
| Runde 3 Text-Handlungen, gemittelte End-Embeddings | 6 | 2 |

- Werkzeug-Welt: gelernter Rest auf Test 3–20× unter Mittelwert-Delta (Verhältnis .05–.45), Retention überall besser als die Kontrolle.
- Text: Test meist 5–40 % unter Mittelwert-Delta (bestes: `question` auf `l_out-23` last, .52–.70); Fehlschläge fast nur `fixed_reference_retention` (Delta 0: `negate` oder `question` auf Retention 1–6 % schlechter), vier knappe Verfehlungen des .98-Gates.
- Schluss: Das Objective der Runden 1–5 war das Hindernis, nicht die Taps.

## Grenzen

Die Test-Partitionen der Runden 3–5 waren schon gelesen. Laut Vorregistrierung ist das daher nur ein Hinweis; vor jeder §99-Aussage braucht es eine frische Erfassung (Runde 7). Keine Laufzeit-, Empfänger- oder Lernautorität, nicht auf dem Redmi gemessen, `canonical_architecture_complete=false`.

Rohdaten (alle `metrics.json` + Checkpoints): `results-parts/` (ZIP `93a53501…`, Wiederherstellung mit `scripts/sealed_storage_parts.py restore`).
