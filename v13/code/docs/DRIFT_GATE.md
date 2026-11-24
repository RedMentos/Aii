# WP-S5 Drift-Gate und Self-Distillation

Code `v13/drift.py`, Probe-Menge `specs/drift-probes.json`, Tests `tests/test_drift.py`, Befehl `:drift`.

## Was es tut

- **Eingefrorene Probe-Mengen.**
  - Sprache: 30 allgemeine Prompts (24 EN, 6 DE), ohne Nutzerdaten, nie im Training.
  - Entscheidungen: route/wake/halt mit den ältesten menschlichen Labels, höchstens 64.
  - Beim ersten Gebrauch wird der SHA-256 festgehalten. Eine geänderte Datei oder neue Labels gelten erst nach `:drift refreeze <Set> <Grund>`. Die Historie bleibt erhalten.
- **Messung nach jedem Adapter-Update** (RL's Razor: Vergessen folgt dem Abstand zur Basis).
  - `measure_lm(component, evaluator)`: mittlere KL(Basis ‖ Kandidat) auf den Sprach-Probes. Der Evaluator braucht nur `kl(prompts) -> float`, `lora_trainer.LlamaCppEvaluator` passt.
  - `measure_decisions(component, base_fn, cand_fn)`: Anteil gekippter geschützter Entscheidungen.
  - Jede Messung landet in Telemetrie `drift_gate` und im Zustand `WP_S5_DRIFT`.
- **Freigabe-Kriterium.**
  - `record(update_id, report)` schreibt `drift` ins Update-Manifest.
  - `guards.stability_envelope` (also `:approve`) lehnt mit `DRIFT_ABOVE_CAP` ab.
  - Die Grenzen kommen aus der aktuellen Konfiguration, nicht aus der Messung: `drift_kl_max` 0,05 (gleich AG6 `DRIFT_MAX`) und `drift_flip_max` 0,10.
  - Mit `drift_required=1` wird auch ein Update ohne Messung abgelehnt (`DRIFT_NOT_MEASURED`).
- **SDFT-Datensatz** (`:drift sdft`).
  - Grundlage sind menschliche Korrekturen (fact/style/preference, `learn`).
  - Der Lehrer-Prompt enthält Frage + Korrektur, der Schüler-Prompt nur die Frage.
  - `target` bleibt leer: Das Modell erzeugt die Lehrer-Antwort selbst (on-policy), kein SFT auf den Korrekturtext.
  - Jedes Element trägt `AG6_RETENTION_REQUIRED` (Gegenbefund arXiv 2607.01763).

## Übergabe / offen

- **LoRA: erledigt 2026-10-10 (Pakete D).** Der Live-Evaluator (`agi/trainers.py`) misst die eingefrorenen Probes auf dem Deploy-Pfad; `weights.gate` prüft `frozen_drift`, `weights.approve` ruft `drift.gate` (AG6-Batches haben keine `updates`-Zeile, daher kein `record()`). Echter Wert: KL .019. SDFT im Trainer: Code fertig 2026-10-10 (`weights.sdft_candidates`, `LoraTrainer.self_teach`), echte Läufe lernen die Korrekturen, Gate blockiert noch wegen einer kippenden Probe (siehe `bench-results/ag6-live-20261010/SWEEP.md`). Den SDFT-Datensatz im Trainer verwenden: Lehrer-Antwort mit Kontext generieren, Schüler ohne Kontext trainieren.
- **Shadow-Heads (`learning.py`):** Nach dem Training `measure_decisions` mit aktivem Head vs. Kandidat auf den eingefrorenen Events aufrufen. Dafür braucht es pro Komponente eine Funktion „Entscheidung für Event X“. Für output_adapter/world/predictor fehlt eine Entscheidungs-Probe; dort gilt KL bzw. die vorhandene Retention-Metrik.
- `drift_required` steht auf 0, bis alle Update-Pfade messen. Danach auf 1 stellen.
- Kein Redmi-Wert; die KL-Grenze ist ein BOOT-Wert.

## Data mix before every weight-training job (Pakete E, 2026-10-10)
`guards.mix_for_training(items)` runs in `agi/weights.WeightConsolidation.stage` and again in `train()` before `trainer.fit`. Origin per item: explicit `origin` field, else DREAM/HYPOTHESIS label → dream, model-written targets (`rated_answer`, sdft without origin, TTT `own_final_answer`) → self, else human. SDFT items carry `origin: human_replay` (content is the human correction), sleep TTT candidates `origin: self`. Quotas from `guards.DATA_MIX`; a failing batch is `DATA_MIX_FAIL` and can be re-staged.
