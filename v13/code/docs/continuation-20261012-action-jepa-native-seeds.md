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

## Runde 2 (gleicher Tag): Residuum über Mittelwert-Delta

- Neues `scripts/action_jepa_residual_candidate.py` (+2 Tests): Bias startet bei Mittelwert-Delta, Schrittzahl
  240/960 nur auf Kalibrierung gewählt, sonst identische Gates. Vorregistrierung vor dem Lauf gepusht.
- Ergebnis: **alle drei Seeds FAIL.** Gewählt jeweils 240 Schritte (960 überanpassen). Gesamt-MSE knapp unter
  Mittelwert-Delta; nur `translate_de` gewinnt klar (Kalibrierung/Test 12–20 %), `negate`/`question` verlieren.
  Belege `docs/proofs/continuation-20261012/action-jepa-residual-round2/README.md`.
- Nächster sinnvoller Schritt (nicht begonnen): frische Testthemen erfassen (neue native Capture, schwerer Job,
  seriell) oder nichtlinearer Kopf; beides braucht neue Vorregistrierung.

## Runde 3 (gleicher Tag): frische Testthemen, native Neuerfassung

- `scripts/action_jepa_round3.py` (generate/capture/export) + 4 Tests. Vorregistriert vor Erzeugung (`d58cf97`).
- 5 frische Themen (2 vorregistrierte lieferten keine Sätze, eine Reserve genutzt), 2475 Zeilen in einer Laufzeit erfasst.
- Ergebnis: **kein Seed/Arm besteht.** Arm 2 ≈ Mittelwert-Delta, nur `translate_de` besser (6–23 %).
  Belege `docs/proofs/continuation-20261012/action-jepa-round3-fresh/README.md`.
- Damit ist die Action-JEPA-Linie für lineare Köpfe auf diesen Taps ausgeschöpft; nächster Schritt wäre ein anderer
  Tap (Mittelschicht, nicht gemittelt) oder echte Werkzeug-/Weltaktionen statt Text-Umformungen.

## Runde 4 (gleicher Tag): Mittelschicht-Taps

- `scripts/native_layer_taps.cpp` + `scripts/action_jepa_round4.py` + 2 Tests; vorregistriert (`19c37f5`).
- Ergebnis: **alle 24 Läufe FAIL.** Mittelschicht hilft `question`/`summarize`, letzte Schicht `translate_de`, `negate` nie.
  Belege `docs/proofs/continuation-20261012/action-jepa-round4-midlayer/README.md`.
- Bau des Werkzeugs: `pip download llama-cpp-python==0.3.36 --no-binary :all:`, im `vendor/llama.cpp` cmake-Target `llama`,
  dann `g++ -O2 -std=c++17 native_layer_taps.cpp -I…/include -I…/ggml/include -L…/build/bin -lllama -lggml -lggml-base`.

## Runde 5 (gleicher Tag): echte Werkzeug-Aktionen

- `scripts/action_jepa_round5_tools.py` (world/capture/export) + 2 Tests. v1 undurchführbar (Textkollisionen, 32/400), v2 vorregistriert.
- Ergebnis: **alle 24 Läufe FAIL.** Mittelwert-Delta sehr stark, gelernte Köpfe 2–128× schlechter; Training verschlechtert
  sogar den bei Mittelwert-Delta startenden Residuum-Arm. Belege `docs/proofs/continuation-20261012/action-jepa-round5-tools/README.md`.
- Schluss für die ganze Linie (Runden 1–5): mit dem bestehenden affinen Objective ist §99 „JEPA hilft“ für Handlungsfolgen nicht
  belegbar. Nächster sinnvoller Schritt wäre ein geändertes Objective (ohne Varianz-Untergrenze bzw. mit Mittelwert-Delta als fester
  Basis und regularisiertem Rest), getrennt vorregistriert.

## Runde 6: geändertes Objective (Mittelwert-Delta + Ridge-Rest)

Vorregistriert (`9214a4c`), 54 Läufe auf den Datensätzen der Runden 3–5: **38 PASS**. Werkzeug-Welt 24/24 (Rest 3–20× unter Mittelwert-Delta), Text-Handlungen 14/30 (Fehlschläge meist Retention mit Delta 0). Test-Partitionen waren exponiert, also nur Hinweis; nächster Schritt ist eine frische Erfassung (Runde 7) mit unverändertem Skript `scripts/action_jepa_round6_ridge.py`. Belege `docs/proofs/continuation-20261012/action-jepa-round6-ridge/`.

## Runde 7: frische Erfassung

Vorregistriert (`1914106`), Runde-6-Skript unverändert. Werkzeug-Welt mit nie benutzten Startwerten **24/24 PASS → CONFIRMED** (Median Test-MSE 0.21 × Mittelwert-Delta). Text mit neuen Themen 11/30 → NOT_CONFIRMED; nur `l_out-11` letzter Token stabil. Nur 3/8 Themen nutzbar (Reserve-Regel). Belege `docs/proofs/continuation-20261012/action-jepa-round7-fresh/`.
