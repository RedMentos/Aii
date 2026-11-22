# WP-N2 rest: learned deliberation space (§10, §10.1, §24.17, G5)

Module: `code/v13/deliberation.py`. Hooks are in `focal.py` (Inquisition.run, FocalLoop halt gate and record), `runtime.py` (`_world_error`), `inputs.py` (rating) and `operator.py` (`:delib`).

- **World-error trigger.** A recent own world-prediction error opens Inquisition as `WORLD_PREDICTION_ERROR`. It is either a ModulatorPacket with `world_prediction_error >= 0.5` (WP-F fast-forward surprise, WP-N9 residual) or a WP-N9 `SelfWorldAttribution` of class MIXED, in the same session within 15 minutes.
- **Learned deliberation space.** Each (trigger set, mode) pair keeps a running value. An informative verdict (CONTESTED, UNSUPPORTED, SUPPORTED, ...) counts 1 and NO_TARGET/CONSISTENT/PROPOSED count 0. Ratings feed in through `on_rating`. Once a pair has at least 3 observations, the proposal re-ranks the modes; HYPOTHESIS stays first and the step count does not change.
  - SHADOW (Age 0 default) only logs the proposal.
  - `:delib active` (explicit human) applies the proposal, and only when the Age right `deliberation_modes` exists.
- **Halt only after a stable trajectory (§10.1, G5).** The learned halt readout is still computed and logged (`halt_decision.steering`). It may only steer once the last 10 trajectories of that trigger pattern ended in the same decision at least 80% of the time and their cycle counts differ by at most 1. Otherwise the BOOT scaffold decides (log `halt_gated`).
- **Neuromod.** Path `inquisition_policy` (control). The `touch` call carries the trigger, the proposal and whether it was applied; ratings arrive as `signal(task_success)`.
- **Claim limit.** These are BOOT thresholds. There is no measurement yet showing that the learned order raises the hit rate; that belongs on the cloud bench (WP-N12).

Tests: `tests/test_deliberation.py` (6 tests). `tests/test_focal.py` was adapted: without a stable trajectory the halt readout does not steer.
