# Run196 — R4 prospective stratified selective-abstention protocol (2026-10-25)

## Parent and file ownership
- Parent: Run195 PR223 `310084b5fa76c6e47c40058145e87b4895fef57e`, itself based on Run194. This is a separate review branch; it does not merge production Runtime or override Claude's work.
- Owner: Run196 isolated `scripts/run196_r4_stratified_future.py`, `tests/test_run196_r4_stratified_future.py`, `.github/workflows/run196-r4-prospective-contract.yml`, and this Run196 evidence directory. No edits to frozen `v13/` Runtime, Canon, registered cohorts, Phone installer, or active Run189 native B2/C3 owner.
- Read AGENTS, v13/AGENTS, HANDOFF_CURRENT, v13/ROADMAP, Run195 BUILD_STATE and independent review, user decisions, and the full canonical blueprint from remote. The Canon is unchanged.

## New candidate (not an executed native preregistration)
- Prospective **two-seed, four-stratum, 120-task** protocol. Seeds `20261101` and `20261103`, 15 `summary`, `long`, `notes`, `compare` tasks each seed. Run195 seed7-only threshold `0.5803461074829102` is fixed and hash-bound to original Run195 prereg `f501313e9daee53080d4f3ebe8e8e26394a40917085abe05d07a1f49df6200e4`. Run195 seed11 is explicitly not reused for calibration or scoring.
- Strict task-manifest prompt hashes, exact fixture set, unique prompts, source commit/tree/model/runner/capture-script SHA binding, closed write-once registration, future capture identity and feature/token consistency checks.
- Per-kind and per-seed risk/coverage controls prevent the Run195 compare 70% wrong/answered from being concealed by aggregate averages. Costs are explicit in quarter-units: correct delivered +4, wrong delivered -8, correct abstained -2, wrong abstained -1. Require aggregate positive utility delta, >=70% overall and each-seed coverage, >=60% each-kind and seed×kind coverage, <=20% wrong/answered in each kind and each seed×kind, >=10-point aggregate selective error reduction vs raw C3.
- Even if future criteria pass, output says `PROSPECTIVE_CRITERIA_MET_NO_DEPLOYMENT`; `production_authority=0` and `canonical_gate_pass=false`. No automated runtime wiring, JEF routing or Age promotion.
- The `prepare` stage generates a **candidate** only. The `seal` stage generates a registration that MUST be published/independently verified before any native capture. This run has NOT sealed a real model-bound preregistration, since the actual new tasks, source/revision and native model hashes must be rechecked with the native owner. The future capture schema is new and needs a separate native capture adapter/attestation; the historical R4 capture JSON cannot pass it.

## Evidence
- `tests_initial.log`: first software suite 14/14 PASS.
- `tests_final.log`: independent adversarial review added feature/token consistency, duplicate prompt and per-seed compare-risk guards; 17/17 PASS.
- `sha256sums.txt`: SHA-256 for new source, tests, workflow and logs.
- No model loaded, no native model run, no Redmi. Current scratch GitHub DNS unavailable; GitHub connector is usable for review branches. CI after remote publication still requires independent verification.

## Gates and blockers (unchanged)
- STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; DS2 H2 `FAIL`; full V13 `INCOMPLETE`.
- Run195 retrospective global threshold is **NOT** deployable (compare 7/10 wrong among selected, Wilson intervals overlap, seed11 was not blind). Run196 does not change that verdict.
- No claim that new seeds are genuinely unseen until task-generator source, exact prompts and historical overlap are independently checked and sealed. No source/model substitution during registered cohorts. Active native owner Run189 is not overlapped.

## Next exact steps
1. Independently review Run196 candidate against full checkout; run `cd v13/code && python -m unittest -v tests.test_run196_r4_stratified_future` and official privacy scan from parent to branch.
2. In a new authorized native window (after active owner releases it), pin full model GGUF SHA, runner binary SHA, source commit/tree and capture script, generate exact 120 prompts, audit novelty against historical R4 fixtures, then `prepare` and `seal` registration, commit and independently verify remote bytes **before** any capture.
3. Implement/validate the future capture adapter to emit `V13_R4_PROSPECTIVE_CAPTURE_V1` with exact bound row hashes and actual native token features. Only then perform serialized native inference and offline evaluation; retain all failures.
4. While native path is blocked, pursue other independent functional canonical packages (STEP2, Body-JEPA, Context OS, JEF/learning, etc.) without changing their gates.

### Commands
`cd v13/code && python -m unittest -v tests.test_run196_r4_stratified_future`
`python scripts/run196_r4_stratified_future.py prepare <tasks.json> <pins.json> <candidate.json>`
`python scripts/run196_r4_stratified_future.py seal <candidate.json> <sealed.json>`
`python scripts/run196_r4_stratified_future.py evaluate <sealed.json> <native_capture.json> <report.json>`