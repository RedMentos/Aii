# WP-J (model-free part): dynamic B3 callosum

Module: `code/v13/callosum.py`. Hooks are in `cognition.communicate`, `runtime` (turn outcome), `inputs.record_rating`, `verification.doctor` (B3 block), `neuromod` (path `callosum_channel_policy`) and `operator` (`:callosum`).

- **§85.2 B3_MESSAGE.** Every MessagePacket now carries `salience`, `confidence`, `signed_gain`, `urgency`, `temporal_scope`, `compatibility_score`, `utility_history`, `bytes` and `channel_proposal`.
  - `signed_gain` is only a proposal to the receiver, never an override.
  - **+0.5:** the sender agrees with the receiver's current hypothesis (shared numbers or quotes).
  - **−0.5:** the sender's numbers contradict the receiver's and the sender has exact evidence.
  - **+0.25:** the sender raises an open issue (`needs_reentry`).
  - **0:** otherwise.
- **B3-5 learned channel policy.** Each direction keeps a utility per channel: NO_MESSAGE, SOURCE_EXACT, CONTROL, SYMBOLIC.
  - Every baseline keeps p ≥ 0.05; LATENT stays at p = 0 (B3-H9).
  - SHADOW (default) logs the proposal and uses the configured channel.
  - `:callosum active` (explicit human) uses the proposal and passes `signed_gain`/`urgency` to the receiver as CONTROL fields.
  - A channel worse than NO_MESSAGE is never chosen; at least 5 observations are needed.
- **B3-H9 utility.** Utility is measured from the receiver's next offer: task_gain (reached the focal coalition) + uncertainty_reduction + source_recovery_gain − latency cost − bytes cost − penalty when the turn did not end FINAL. Ratings add human value.
- **B3-H10 degradation.** A change in the receiver's model revision resets that direction to the configured channel (`resets`).
- **B3-H11 :doctor.** Per direction, `:doctor` reports the latent level (`unavailable`), calibration, receiver revision, taps, rank/slots, latent gain, router KL / expert flip (None), utility per channel and vs NO_MESSAGE, experience count, policy p, fallback channel and hardware proof. Status FAIL would only apply to latent without calibration, which cannot happen here.

## Open (native, cloud bench)
- L1 receiver-adapter latent read, L2 calibrated prefix, L3/L4 (B3-H3), B3-H2 message subspace, B3-H7 mobile bridge and the G-CALLOSUM-UTILITY-002 latent gate all need real sender states and llama.cpp prefix injection. The `B3_LATENT` status stays `unavailable`.
- Whether `signed_gain` in ACTIVE improves the receiver offers must be measured with models (WP-N12).

Tests: `tests/test_callosum.py` (5).

## B3-H2 / B3-H7 message bridge (Pakete E, 2026-10-10)
- `v13/b3bridge.py`: learned K-slot selector over sender tokens → shared rank-r projector → z[K,r] in BF16 → receiver projector + calibration (mean/sd, OOD threshold at the 99th fit percentile) + learned gate → additive residual on the frozen NO_MESSAGE readout. Private states never leave the body; bodies frozen (B3-H8). Anti-collapse: variance hinge, decorrelation, slot-overlap penalty. Numpy only, manual gradients (finite-difference test).
- `budget()` (B3-H7) reports parameters, BF16 weight/message/buffer bytes, Age-0 limit 2 MiB. `diversity_report()` (B3-H2 checks), `l1_gate()` (G-CALLOSUM-UTILITY-002 for L1, incl. utility per byte vs EXACT/CONTROL/SYMBOLIC), manifest with sha256 + sender/receiver revisions (B3-H10: `load` refuses a changed revision).
- `:doctor` B3 block reads `<home>/b3/<direction>.json`: calibration, rank, slots, params, L1 verdict, stale revision. Latent authority stays 0; `latent_level` becomes `L1_PASSED_L2_SHADOW_ALLOWED` only after a PASS verdict.
- Measurement `bench-results/b3-h2-20261010/`: learned selector beats mean-pool and NO_MESSAGE on detail and on unseen tone/hedging, but L1 gate FAIL on all 8 tasks (EXACT/SYMBOLIC cheaper). LATENT stays `unavailable`.
- Tests `tests/test_b3bridge.py` (7).

## WP-U9 B3-H12 Abschluss-Gate (LOCKED) und B3-H13

`b3bridge.completion_gate` prüft für jede Richtung die 14 Bedingungen aus B3-H12, jeweils aus Belegen:
- Code,
- echter Sender-Pfad (native Taps),
- echte Empfänger-Wirkung (Tap-IDs + latent_gain),
- empfängerspezifisch kalibrierte Bridge (Manifest, Revision nicht veraltet),
- Rückfall-Kanäle mit Erfahrung,
- OOD-Gate,
- Router-Metriken,
- Neustart-Reproduzierbarkeit,
- Integrationstests,
- Telemetrie (MessagePackets),
- NO_MESSAGE-, EXACT- und SYMBOLIC/CONTROL-Ablation,
- Messung auf dem Zielgerät.

**Status:**
- `unavailable`
- `scaffold`
- `L1_shadow`: nur bei L1-PASS mit passender Empfänger-Revision.
- `active`: nur wenn alle 14 Bedingungen erfüllt sind. Dann gilt `B3_LATENT_IMPLEMENTED=true`.

Die LATENT-Autorität bleibt 0. `canon` enthält den Satz aus B3-H13.

Abrufbar über `:doctor` unter `B3.<Richtung>.completion`.

**Tests:** `tests/test_b3_completion.py`.
