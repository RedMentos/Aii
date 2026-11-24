# STEP2 four-arm evidence analysis — preregistration, 2026-10-28

Review-only, independent branch `assistant/v13-step2-fourarm-evidence-analysis-20261028`, forked from fixture PR #817 at exact `c11fc2a9e88933f41db1da0b297c43b26d40364b`. This is **not** a native run or a revision of any registered Z2/Z2b/Z2c cohort. Do not touch their source, seeds, or archived failures. PR #818 is a separate runner preflight with a stale fixture parent; no automatic merge.

## Problem and registered analysis
The next four-arm TP/TC/SP/SC native experiment needs a fail-closed scorer before evidence exists. Its source-only synthetic unit tests must not be presented as an observed gain. Analyze exactly ten fixture identities × three seeds (27,28,29) × four arms and all seven fixed STEP2 variants. Reject missing/duplicated rows, unregistered settings, stale raw hashes, mismatched fixture/source/runner/registration identity, mixed evidence levels, changed B1/B2/C3 model weights, invalid numerical scores, and missing executive question activation. The native collector must separately verify raw bytes against reported hashes; this script cannot authenticate supplied digests.

Primary comparisons: TP both_exact versus TP best single, TP same-policy, TP prompt-only, and SP both_exact (shared-body pointer). Pair all three seeds by episode; 2,000 deterministic episode-cluster bootstrap replicates; require lower 95% percentile bound > 0. Also require each solo body win at least one episode, complementary error profiles (>=0.25 opposite advantage), and TP beat both solos per seed. Report TP vs TC and SP vs SC as secondary pointer contrasts, not substitutes for the primary gate.

Even a synthetic positive must report `canonical_gate_pass=false`, `step2_gate_promoted=false`, `jepa_weight=0`, Body-JEPA unavailable. No B3, Redmi, learning or whole-system promotion. The input summary schema is a **future collector contract**, not a claim that existing Z2b summaries contain all identity fields. The frozen original evidence remains untouched.

## Verification
Locally: `python -m unittest -v test_step2_longnote_fourarm_analysis.py` in the isolated candidate folder (stdlib only). Repository: `cd v13/code && python -m unittest -v tests.test_step2_longnote_fourarm_analysis_20261028`; compile and full suite through review CI. Preserve RED attempts, exact tested commit, workflow exits and hashes. Do not launch models or access unowned cgroups.
