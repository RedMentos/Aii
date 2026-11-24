# Action-JEPA Runde 9: Text-Arm `l_out-11` letzter Token auf neuen Themen

Stand 2026-10-13, Thread „Nächste offene Pakete M“ (Claude), Linux-Cloud, nicht auf dem Redmi.
Vorregistriert in `preregistration.json` (GitHub `a6e755d`, vor Erzeugung und Erfassung). Kandidat `scripts/action_jepa_round6_ridge.py` unverändert (sha `acb8264e…`), gleiche Gates, Seeds 13/21/34 × `full`/`proj`, dim 16.

## Ergebnis: CONFIRMED, 6/6 Läufe bestehen alle Gates

Test: 184 frische Episoden aus 8 nie benutzten Themen (Runde 7: 72 aus 3). Quotient Test-MSE / beste Kontrolle (min aus Kopie, Mittelwert-Delta, gemischtes Ziel), über die 6 Läufe:

| Handlung | Spanne | 
|---|---|
| question | .71–.82 |
| negate | .72–.89 |
| summarize | .87–.97 |
| translate_de | .88–.94 |

Retention: in allen 24 Handlung×Lauf-Paaren besser als die Kontrolle (Delta −.006 bis −.100).

- Der Gewinn ist echt, aber klein: 3–29 % unter der besten Kontrolle (Werkzeug-Welt: 76–95 %). `summarize` liegt in einem Lauf bei .97, nah am .98-Gate.
- Ablauf: C3 (LFM2.5-350M, Temperatur 0) schrieb Sätze und die vier Handlungen. Alle 2795 Zeilen (1875 alt + 920 neu) wurden einmal mit B2 mean-final (für den Runde-3-Export) und einmal mit einem einzigen Tap-Build erfasst: `native_layer_taps.cpp` gegen das gepinnte b10964-Release, sha `4a6a311f…`, wie der Gerätepfad, nur Schicht 11. Gesamtlauf ca. 28 min.

## Abweichungen (vorregistrierte Reserve-Regel, kein Neulauf)

- restaurants, mountain hiking, shopping malls und Reserve lighthouses lieferten < 16 verwertbare Sätze. Genutzt wurden die Reserven fire stations, playgrounds, deserts. zoos und deserts haben 20 statt 24 Sätze. 0 Episoden wegen geteiltem Text ausgeschlossen.
- Train/Kalibrierung/Retention sind wie in Runde 7 die Plan-v2-Episoden; neu ist nur der Test.

## Grenzen

Belegt ist nur: eine feste Mittelwert-Delta-Basis plus ein gelernter Ridge-Rest auf eingefrorenen `l_out-11`-Letzt-Token-Taps sagt C3-Text-Handlungsfolgen auf ungesehenen Themen besser voraus als die Kontrollen. Keine Aussage über semantische Qualität, keine Laufzeit-, Empfänger- oder Lernautorität, nicht in der Laufzeit (die SHADOW-Werkzeug-Vorhersage deckt weiter nur `calc` und Notizen ab), `canonical_architecture_complete=false`.

Dateien: `report.json` (alle Läufe, Gates, Quotienten), `generation-report.json`, `fresh-sentences.json`, `layer-capture-report.json`, `text-export-receipt.json`. Rohdaten `raw-parts/` (ZIP `ab7ba4b9…`: Erzeugungs-Rohlog, alle Erfassungs-Batches, Taps, Schrittprotokolle), Ergebnisse `results-parts/` (ZIP `7b8098d8…`: 6 `metrics.json` + Checkpoints, Bericht). Wiederherstellen mit `scripts/sealed_storage_parts.py restore --manifest … --out …`. Neu ausführen: `scripts/action_jepa_round9_text.py run` (Befehl in `report.json`/Schrittprotokollen).
