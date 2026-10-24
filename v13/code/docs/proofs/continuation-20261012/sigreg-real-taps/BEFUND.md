# WP-S4-Rest: SIGReg vs. EMA auf echten nativen Token-Zuständen (2026-10-12, Thread K)

**Verdikt: DEFAULT_STAYS_EMA** (vorab festgelegte Regel, keine Code-Änderung). Preregistrierung `preregistration.json` (sha256 `3be1a653…e8c6`, Commit `f07837a` vor dem ersten Testlauf), Ergebnisse `results.json` (sha256 `e1a2740b…36bf`), 120/120 Läufe.

**Aufbau.** Unveränderter Runtime-Worker `v13.predictor_worker.train` (eigene Gates: noncollapse, predictive gain vs. Kopie und Shuffle, Retention, Gradient-Check, Determinismus, Reload). Daten: echte B1-LFM2.5-1.2B-Token-Endzustände (llama.cpp b10964, `/embeddings` pooling none) aus `bench-results/b3-l1-v3-20261012/states.npz` (sha256 `df80c17b…87d2`, Thread J, 600 synthetische Übergabe-Notizen). Paarregel wie `learning.py` (Token i → i+2, i=3,6,9…, Gruppe = Notiz). Notizen 0–79 nur für den Probelauf, Testnotizen disjunkt: R16 (16 Notizen ≈ 390 Trainingspaare, Laufzeit-Größe) und R64 (64 Notizen ≈ 1560 Paare) × 5 Folds × gesunder/geschrumpfter (×0,02) Start × Budget `runtime` (Config-Defaults: lr .002, Norm .02, 240 Schritte) und `stress` (Knob-Maxima: lr .05, Norm .2, 1000 Schritte). Zusatzmaß: Top-1-Treffer der Vorhersage unter allen Held-out-Zukünften (skalenfrei, modusübergreifend vergleichbar).

| Budget / Start | Modus | commit_eligible | Vorhersage/Kopie (Median) | Top-1 (Kopie) | Retention | noncollapse |
|---|---|---|---|---|---|---|
| runtime / gesund | ema | 5/10 | **0.883** | .037 (.020) | 10/10 | 7/10 |
| runtime / gesund | sigreg | 0/10 | 0.983 | .038 (.037) | 10/10 | 8/10 |
| runtime / gesund | both | **7/10** | 0.908 | .039 (.026) | 10/10 | 10/10 |
| runtime / geschrumpft | alle | 0/10 | 1.00–1.13 | ≈ Kopie | – | **0/10** |
| stress / gesund | ema | 1/10 | **1.556** (schlechter als Kopie) | .226 (.254) | 3/10 | 10/10 |
| stress / gesund | sigreg | **5/10** | 0.957 | .289 (.288) | **10/10** | 10/10 |
| stress / gesund | both | 0/10 | 0.965 | .271 (.240) | 0/10 | 10/10 |
| stress / geschrumpft | ema / sigreg / both | 0/10 | 3.87 / 0.95 / 0.84 | .11 / .11 / .19 | 0/10 | 10/10 |

**Lesart.**
1. Mit dem echten Laufzeitbudget bewegt sich der Projektor kaum; EMA hat die beste Vorhersage/Kopie-Quote, `both` besteht die Worker-Gates öfter (7 vs. 5/10), ist aber in Quote schlechter → Regel nicht erfüllt, `ema` bleibt.
2. **Ein geschrumpfter (kollabierter) Checkpoint wird beim Laufzeitbudget von keinem Modus repariert** (0/10 noncollapse). Der Synthetik-Befund „SIGReg rettet Kollaps“ (`SIGREG_PREDICTOR.md`) gilt nur mit großem Budget.
3. Beim Stress-Budget überanpasst EMA (Vorhersage 1,56× schlechter als Kopie, Retention 3/10); SIGReg bleibt stabil (Retention 10/10, Quote < 1). Kollaps-Erholung schaffen bei großem Budget alle drei Modi (auch EMA mit Varianzboden) → Klausel (2) scheitert, nur Hinweis: **falls das Budget je erhöht wird, ist `sigreg` der sicherere Modus.**
4. Absolut ist der Nutzen klein: auch der beste Arm sagt Token t+2 höchstens ~12 % besser als die Kopie voraus; Top-1 liegt nahe an der Kopie. Kein Beleg für semantischen Vorhersagewert.

**Grenzen.** Nur B1 (2048 dim); B2-Qwen-Token-Zustände (1024 dim) nicht im Datensatz. Daten stammen aus `/embeddings` statt dem Runtime-Tap-Pfad (gleiche Endzustände, nicht bytegleich geprüft). Synthetische Notizen, Linux x86_64, kein Redmi.

Reproduktion: `cd code && python3 scripts/sigreg_real_taps.py run` (prüft Daten-/Code-Hashes gegen die Preregistrierung, setzt fort). Tests `tests/test_sigreg_real_taps.py` (7).
