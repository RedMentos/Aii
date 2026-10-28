# Run78 prereg — heldout real-file ensemble mean vs first member (2026-10-28)

Owner GPT-6 scheduled continuation. Parent Run77 draft PR #984 at `cdb99f73c6d3af39ddd4e88dd8952cad636fed58`, **Run77 CI pending at preregistration**; grandparent Run76 #983 Actions 40780438158 reported GREEN, original raw ZIP not yet independently audited. This is a **new isolated SHADOW diagnostic**, not a modification of frozen Run60/64/67/69/71/72/76/77 cohorts or source.

## Fixed cohort before implementation

- Exact real temporary-file action fixture generator: `scripts.run60_z12b_slotlocal_real_file_baseline._rows` at parent SHA. This executes actual isolated Linux filesystem operations, but is not a live user/phone/Runtime environment.
- Seeds `(401, 409, 419)`; each seed chooses four held-out action/slot combinations with `random.Random(seed).sample(NON_NOOP, 4)`. Training 240 rows (`test=False`), holdout 60 rows (`test=True`) with distinct temporary directories/seed offsets; no registered historical seeds reused.
- SlotWorldJEPA and opt-in EnsembleMeanSlotWorldJEPA: same seed, ensemble=3, steps=240, six slots, six per-slot action categories (five operations + UNTOUCHED), no `calibrate` call. Both training paths must yield exactly equal enc/tgt/preds/zsd; otherwise abort, not compare. This is a comparison of **prediction aggregation**, not learned-weight differences.
- Primary metric: mean heldout target-slot normalized latent squared error, using each model's `slot_errors`; lower is better. Secondary: all-slot error and per-seed results. Report improvement ratio `(member0 - mean) / max(member0, 1e-12)`. Predeclared exploratory criterion: aggregate ratio >= 0.05 with each seed nonnegative. No significance claim with three seeds.
- Negative control: deterministically shuffle heldout action vectors with `np.random.default_rng(seed + 7000).permutation` while keeping states/targets fixed; report candidate shuffled vs correct error. Do not silently change control or discard failures. If correct action is not better than shuffle, record action-conditioning failure regardless of member aggregation.
- Hash each generated train/test (state, action, next-state) array sequence in little-endian float64 and each metric report; include exact source revision/commit and per-seed rows. Print JSON with nonfinite rejected. No private data, no network/model downloads, no native or Redmi inference.
- Source-bound CI: focused Run78 deterministic integrity tests, Run77/Run76/frozen JEPA tests, full software suite, privacy, diff check, original raw logs with SHA256SUMS. No changing frozen kernels or tests.

## Claim limits / follow-up

Even if mean beats member0, a latent error decrease is not a demonstrated grounded action-outcome benefit or semantic B2↔World-JEPA utility. Real-file source distributions are generated, and target-latent semantics can collapse. Any positive result needs a separate preregistered grounded outcome/readout comparison with persistence and negative controls before runtime integration. All Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi UNMEASURED and full-scope incomplete remain.
