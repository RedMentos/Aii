# Action-JEPA: echtes NumPy-Training auf 1875 nativen Zeilen, Seeds 13/21/34

Stand 2026-10-12, Thread „Nächste offene Pakete F“ (Claude). Linux-Cloud, kein Redmi.

**Ergebnis: alle drei Seeds `candidate_gate_pass=false`.** Analytischer Gradient, Endlichkeit,
Determinismus, Reload, Nicht-Kollaps bestehen. `predictive_gain_over_controls` und
`fixed_reference_retention` scheitern bei 13, 21 und 34.

| Seed | Test-MSE Kandidat | Copy | Mittelwert-Delta | Shuffled | Retention vorher → nachher |
|---|---|---|---|---|---|
| 13 | .310 | .394 | .180 | .505 | .432 → .281 |
| 21 | .311 | .360 | .194 | .526 | .340 → .304 |
| 34 | .284 | .277 | .176 | .475 | .266 → .264 |

Der affine Prädiktor lernt (Trainingsverlust .30–.40 → .10–.12) und schlägt meist Copy, ist aber
auf jeder Partition etwa 1,7× schlechter als die Mittelwert-Delta-Kontrolle je Aktion. Einzig
`translate_de` liegt etwa gleichauf (Test .29–.36 gegen .31–.34). Die Retention-Prüfung ist pro
Aktion streng (Delta 0): `negate`/`question`/`summarize` werden schlechter als der Startzustand, weil der
Startzustand dort fast Copy ist und Copy für diese Aktionen nahe am Ziel liegt. Das bestätigt
den Befund aus WP-T17 (synthetisch) jetzt auf echten Qwen3.5-0.8B-Taps.

## Bindung und Abweichung

- Vorregistrierung unverändert: `../../continuation-20261011/action-jepa-bounded-recovery/training-preregistration.json`
  (Seeds 13/21/34, 240 Schritte, dim 16, lr .02, max_update_norm .05, EMA .99, Retention-Delta 0).
  Alle sechs vorregistrierten Quell-Hashes stimmen.
- Taps: Nacht-Erfassung `09fde379…`, bytegleich aus `action-jepa-prefix736.closed.zip` +
  `action-native1875-recovered-20261012/parts` wiederhergestellt (`scripts/action_jepa_delta_storage.py restore`,
  numpy 2.3.5). Die ursprünglich gebundenen Taps `533ff0be…` sind verloren.
- Abweichung 1: Der unveränderte Exporter verlangt GGUF/Runner/Bibliotheken als Dateien; die fehlen
  hier. Neues Skript `scripts/export_action_jepa_recovered_dataset.py` bindet sie über die
  Registrierung `99912f23…`, die in allen 118 Rohbatches steckt, prüft jeden Rohbatch gegen die Floats
  und verlangt, dass alle 1492 Zeilen und Quelltext-Bindungen identisch zum vorregistrierten Datensatz
  `be96e671…` sind. Datensatz neu: `56146f32…`.
- Abweichung 2: Python 3.13.16 statt 3.12.14 (numpy 2.3.5, BLAS 1 Thread wie vorgegeben).
- `training-input-binding.json` wurde vor dem ersten Seed auf GitHub gepusht (Commit `fbd3bb8`).

## Dateien

- `report.json`: Kennzahlen je Seed/Partition/Aktion, Gates.
- `parts/`: geschlossenes ZIP (`67f1c9d8…`) mit Datensatz, Checkpoints, rohen `metrics.json` und
  externen `predict`-Aufrufen für alle vier Aktionen auf den 143 Test-Kontexten.
  Wiederherstellen: `python3 scripts/sealed_storage_parts.py restore --manifest parts/manifest.json --out X.zip`.

Keine Empfänger-, Lern- oder Runtime-Autorität. Kein semantischer Qualitätsnachweis.

## Was das Ergebnis ändern würde

Ein Kandidat müsste die Mittelwert-Delta-Kontrolle je Aktion um >2 % schlagen. Naheliegend:
Mittelwert-Delta als Startwert des Bias (Kandidat lernt nur den Rest), oder mehr Schritte, nur auf der
Kalibrier-Partition gewählt. Beides wäre eine neue, getrennt vorzuregistrierende Runde; die
historischen Test-Themen sind bereits exponiert.
