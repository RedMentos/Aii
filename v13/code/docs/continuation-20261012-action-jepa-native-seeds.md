# Fortsetzung 2026-10-12: Action-JEPA NumPy-Seeds 13/21/34 (Claude, Thread F)

- Erledigt: vorregistriertes Training (`action-jepa-bounded-recovery/training-preregistration.json`) auf den
  1875 rekonstruierten nativen Taps `09fde379…`, Seeds 13/21/34, unveränderte Gates/Objective.
- Ergebnis: **alle drei Seeds Kandidaten-Gate FAIL.** Der affine Prädiktor lernt, ist aber auf allen
  Partitionen ~1,7× schlechter als die Mittelwert-Delta-Kontrolle und verletzt die Retention je Aktion.
  Belege und Tabelle: `docs/proofs/continuation-20261012/action-jepa-native-train-seeds/README.md`.
- Neu: `scripts/export_action_jepa_recovered_dataset.py` (Export aus wiederhergestellter Erfassung, bindet
  Native-Artefakte über die Registrierung, verlangt identische Zeilen zum vorregistrierten Datensatz),
  Tests `tests/test_action_jepa_recovered_export.py` (6). Keine Änderung an eingefrorenen `v13/*.py`.
- Reproduzieren: `action_jepa_delta_storage.py restore` (numpy 2.3.5; Registrierungspfade unter
  `/workspace/scratch/5a9214d3f329/v13-work/Aii/v13` müssen auf den v13-Ordner zeigen, z. B. Symlink),
  dann Export-Skript, dann `action_jepa_objective.py train` je Seed mit der Konfiguration der Vorregistrierung.
- Offen/nächster Schritt: neue, getrennt vorregistrierte Runde mit Mittelwert-Delta als Bias-Start oder
  kalibrierungsgewählter Schrittzahl. Keine Empfänger-/Lernautorität, kein Redmi-Nachweis.
  STEP2 UTILITY_FAIL und B3 L1 FAIL unverändert.
