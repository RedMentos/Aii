# §99-Ablation: Kontrafaktische Konfidenz des Weltmodells (WP-T8 §7.2.2) — **PARTIAL** (Thread L, 2026-10-12)

Skript `code/scripts/ablation_world_model_confidence.py`, Vorregistrierung `preregistration.json` (Commit `0b1f20c`, vor dem Lauf gepusht), Rohdaten `report.json`.
Echtes `world_model.fit` (Bootstrap-Ridge-Ensemble) und `counterfactual`; nur `transitions` bekommt synthetische eigene Übergänge. Verborgene Welt mit quadratischem Term (lineares Extrapolieren liegt weit weg von den Daten falsch). Sammelpolitik schief: simple nur kurz, detail nur lang, gist überall, both selten. 300 Übergänge, 400 zufällige Abfragen über den ganzen Raum, 5 Saaten.
Primärmaß: Spearman-Korrelation zwischen Konfidenz und negativem Fehler (höher = Konfidenz ordnet Fehler besser).

| Konfidenz | Spearman | echte Konfidenz gewinnt |
|---|---|---|
| echt (Abdeckung × OOD × Ensemble-Streuung) | .354 ± .134 | — |
| nur Stichprobenzahl | .355 ± .145 | 2/5 |
| nur Ensemble-Streuung | **.367** ± .074 | 2/5 |
| zufällig | −.029 | 5/5 |

- Die Konfidenz ordnet Fehler klar besser als Zufall. Das Label SIMULATION_SUPPORTED hat in allen 5 Saaten kleineren Fehler als SIMULATION_UNCERTAIN (z. B. .43 vs .61).
- Sie ist aber nicht besser als jeder ihrer Einzelteile. Die Kombination fügt nichts hinzu; die Streuung allein ist sogar etwas stabiler → PARTIAL.
- Vermutung (nicht getestet): Der OOD-Term in Einheiten des mittleren Nachbarabstands schwankt mit der Datendichte stark und verrauscht das Produkt.
- Grenze: synthetische eigene Übergänge, schiefe Sammelpolitik, BOOT-Knöpfe (COVER_N, SPREAD_REF, OOD_SUPPORT); keine Kausalaussage.
