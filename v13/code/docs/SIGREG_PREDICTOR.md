# WP-S4: LeJEPA SIGReg im t+2-Predictor (2026-10-09)

Datei: `v13/predictor_worker.py`, Tests: `tests/test_predictor_sigreg.py`.

## Schalter (Config, optional)

| Key | Werte | Default |
|---|---|---|
| `predictor_regularizer` | `ema` (bisheriges Verhalten: EMA-Target + Varianz-Floor), `sigreg` (Online-Target mit Stop-Grad, SIGReg statt Varianz-Floor), `both` (EMA-Target + SIGReg) | `ema` |
| `sigreg_weight` | Gewicht des SIGReg-Terms | `1.0` |
| `sigreg_projections` | Zufallsrichtungen pro Schritt (pro Schritt neu, deterministisch aus `seed`) | `32` |

Ohne neue Keys ist das Verhalten byte-identisch zum alten Pfad (auch `world_worker.py` nutzt weiter den Default).
Die Keys sind keine KNOBS in `config.py`, weil das dort nur numerische Knöpfe sind; sie werden mit `cfg.get` gelesen.

## SIGReg

Sliced Epps-Pulley-Test (LeJEPA, arXiv 2511.08544): Projektion der 16-dim Einbettung auf Zufallsrichtungen,
Abstand der empirischen charakteristischen Funktion zu der von N(0,1), Trapez-Quadratur auf t ∈ [0,3] mit
Gewicht exp(-t²/2). Analytischer Gradient, Finite-Differenzen-Check < 1e-5 (läuft im Job mit).

## Kollaps-Telemetrie

Jedes Update loggt alle 32 Schritte in `history.collapse_telemetry`: effektiver Rang, Participation-Rank,
Isotropie (1 = gleichmäßiges Spektrum, 1/d = eine Richtung), mittlere Std, plus Loss-Teile.
`before`/`after` enthalten `context_embedding` und `target_embedding` mit denselben Größen.
`metrics.regularizer` nennt den Modus.

## Ablation (synthetisch, 120 Paare, 32→8 dim, 240 Schritte, `ablation()`)

| Start | Modus | Std | Isotropie | Rang | Pred-MSE | Copy-MSE |
|---|---|---|---|---|---|---|
| gesund | ema | 1.01 | 0.44 | 8 | 0.055 | 0.075 |
| gesund | sigreg | 0.70 | 0.48 | 8 | 0.037 | 0.042 |
| gesund | both | 0.74 | 0.52 | 8 | 0.051 | 0.072 |
| geschrumpft ×0.02 | ema | **0.06** | 0.31 | 8 | 0.0004 | 0.0001 |
| geschrumpft ×0.02 | sigreg | 0.66 | 0.49 | 6 | 0.020 | 0.022 |
| geschrumpft ×0.02 | both | 0.56 | 0.32 | 4 | 0.014 | 0.011 |

Lesart: Aus einem geschrumpften Projektor holt EMA + Varianz-Floor die Skala nicht zurück (winzige MSE ist
das Kollaps-Symptom, nicht Qualität). SIGReg stellt Skala und Isotropie wieder her. Bei gesundem Start
ist kein Modus kollabiert. Das ist ein Fixture-Ergebnis; auf echten nativen Taps (Redmi/Cloud-Bench) noch
nicht gemessen. Default bleibt `ema`, bis eine Messung auf echten Taps vorliegt.

## Messung auf echten nativen Taps (2026-10-12, Thread K)

Vorregistrierte Ablation mit dem unveränderten Worker auf echten B1-Token-Zuständen, 120 Läufe: **Default bleibt `ema`**.
Beim Laufzeitbudget repariert kein Modus einen geschrumpften Checkpoint; beim Knob-Maximum-Budget überanpasst EMA,
SIGReg bleibt stabil (Hinweis für spätere Budget-Erhöhung). Befund und Tabelle:
`docs/proofs/continuation-20261012/sigreg-real-taps/BEFUND.md`.
