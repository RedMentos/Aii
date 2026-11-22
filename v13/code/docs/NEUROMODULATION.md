# WP-N10 Neuromodulation und Eligibility (`v13/neuromod.py`)

Regel (§12.4, §35.1): `Δθ_i ∝ e_i × δ_i × M_i × P_i`. δ bleibt der Loss im jeweiligen Worker; N10 liefert e, M, P als **Gate-Faktor** für das nächste Shadow-Job-Budget.

- **e (Eligibility, §12.1, §62):** zwei Zeitskalen pro Pfad (fast 0,65 / slow 0,93 pro Erfahrungs-Event, slow_mix 0,25). Quelle: die `LearningTrace`-Pakete, die `learning.py` schon schreibt (Cursor über `packets.rowid`, restart-fest, nichts doppelt). Detail-Spuren nur selektiv (normal 10 %, Fehler 80 %, menschliches Feedback 100 %, deterministisch per Hash).
- **M (Modulator-Bus, §12.3, §35.2, §63, §101.1):** typisierte Kanäle in `ModulatorPacket.channels`; alte 5-Feld-Pakete (World, Predictor) werden gemappt. Epistemisch und instrumentell getrennt (§12.5), Gewichte je Lernart (§35.3: knowledge/control/language/skill/world/perception), Quellen-Glaubwürdigkeit nach §63 (Traum = 0). Pakete ohne Pfad gehen per Credit-Map an die im selben Event eligiblen Pfade (§12.2). Menschliche/Operator-Labels zählen selbst als `human_correction`.
- **Sicherheit:** `safety_veto`/`rule_violation`/`irreversible` = Veto-Level, zerfällt langsam; ≥ 0,5 sperrt den Pfad (`plasticity.budget` und `training_config` werfen). `:neuromod clear-veto <Pfad>` hebt es auf.
- **P (Metaplastizität, §16.1, §95.3):** F7-Gain aus `plasticity.py` × `age.plasticity()`; Retention-Fehler (F7 `PlasticityState` oder `retention<0`) öffnen über `repeated_errors` wieder.
- **Faktor:** `P_age × (0,25 + 0,75 × e × M)`, Veto → 0. Steht in `training_policy.neuromodulation`; `plasticity.observe` prüft `effective = base × gain × factor`. Offline-Import (`import_causal_output`) wird nicht nachträglich skaliert, nur Veto greift.
- **Consolidation Tag (§16.3):** ≥ 3 verschiedene FINAL-bestätigende Events (Evidenz/Korrektur/Retention/Erfolg; Überraschung allein nie) + gemessene Stabilität (F7 `consolidation_ready` oder bestandenes Retention-Gate). Retention-Fehler oder Veto löschen den Tag. Gibt keine Konsolidierungs- oder Commit-Autorität.
- **Sleep C:** schnelle Spuren enden, langsame/Modulatoren zerfallen um 10 Events, Tags neu geprüft, tote Pfade entfernt (`rep['neuromodulation']`).
- **AG6 (`agi/weights.py`):** Stage schreibt Spur auf Pfad `weights`, Veto → `SKIPPED_MODULATOR_VETO`, Retention-Gate → `retention ±1`, Nutzerfreigabe → `human_correction`.
- Tests: `tests/test_neuromod.py` (17). Alle Zahlen BOOT-Prioren, nicht gemessen.

Offen: Spuren für Pfade ohne Lernjob (Callosum, Workspace, C_focal, Context Policy, Fast Forward) entstehen erst, wenn WP-N1/N7/F diese Pfade bauen (`Neuromod.touch`). Gelernter Metaplastizitäts-Kopf statt fester Formel; Messung der Wirkung auf echten Trainingsläufen (Cloud-Prüfstand).

## WP-T12 (Pakete E, 2026-10-10): local error δ and metaplasticity head
- **Mapped local error (§12.2).** Typed error channels (`world_prediction_error`, `action_error`, `reward_error`, `calibration_error`, `cost_error`) feed a per-path `error_level`, through the existing credit map: an explicit path, else the paths eligible in that event. A `task_success` outcome gives a signed reward-prediction error δ = r − r̂ against the path's expected outcome r̂ (rate .1). It is stored per sample as `gate()['delta']`.
- **`local_update(component, delta=None)` (§12.4).** Returns the signed scale e × δ × M × P. A negative value means "do not imitate this sample". Measured in `bench-results/delayed-reward-20261010/`: per-sample δ separates confirmed from unconfirmed samples 12.8× (gate alone 1.1×) and triples accuracy (final error .158 → .051).
- **Metaplasticity (§16.1, §68).**
  - The BOOT rule `meta_rule` uses the §68 knobs `META.*`, bound in `knob-map.json`: stability lowers plasticity, novelty and repeated failures reopen it, saturation suppresses it.
  - A learned head (online logistic regression) predicts "the update held". Its features are snapshotted at each LearningTrace and labelled by the next `PlasticityState.retention_pass`.
  - SHADOW (default) only reports `gate()['meta']`. `:neuromod meta active` (explicit human only) multiplies the gate factor by the rule P × (0.5 + learned help).
- Tests: `tests/test_neuromod.py::LocalErrorAndMeta`, `tests/test_ablation99.py::DelayedReward`.
- Open: learners still use their own loss. Wiring `local_update` into a real worker (e.g. readout replay) and turning on ACTIVE meta need measured retention runs.

## WP-U6 Lokale Updates in allen gelernten Köpfen (§12.4, §12.7)

Die globale Wertung (ModulatorPackets, ohne Pfad über die Credit-Map auf alle beteiligten Pfade verteilt) skaliert jetzt die eigene Schrittweite jedes gelernten Kopfes:
- Attention-Policy, Callosum-Kanäle, Context-Policy, Deliberation-Modi, Fast-Forward (NLMS), JEF-Brücke (SGD), C5-Modulatoren.

Jeder Kopf ruft `neuromod.step(n, PATH)` und rechnet mit `Schritt × Faktor`. Der eigene Fehler δ bleibt lokal im Kopf.

Der Faktor hängt vom Modus ab:
- **SHADOW** (Standard): 1,0, die Köpfe lernen wie bisher; `:neuromod path <Pfad>` zeigt den vorgeschlagenen Gate-Faktor.
- **ACTIVE**: nur per `:neuromod local active` (Mensch). Dann gilt der Gate-Faktor des Pfads: Eligibility × Modulator × Age/Meta/Homöostase. Er liegt mindestens bei 0,25 (menschengeführtes Age 0); Veto oder ungeklärter Konflikt ergeben 0.

**Grenze:** Der Faktor spiegelt den Pfadzustand vor dieser Stichprobe, weil Touch und Signal des Kopfes erst nach seinem Update kommen.
**Tests:** `tests/test_local_updates.py` (3).
