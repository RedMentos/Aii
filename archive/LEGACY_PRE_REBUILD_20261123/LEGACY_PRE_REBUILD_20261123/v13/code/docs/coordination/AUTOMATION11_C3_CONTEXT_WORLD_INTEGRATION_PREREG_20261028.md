# Preregistered review-only three-organ integration (2026-10-28)

Owner: ChatGPT automation continuation, isolated branch `assistant/v13-run11-c3-context-world-merge-20261028`. This document is committed **before** any donor tree import or integration workflow. No active Claude/Codex branch will be modified.

## Frozen inputs / parentage
- Primary parent: independently audited Linux-native C3 merged CLI/renderer source #900, `3ca9a6d158759f5abc9c00883135487c0a33e3ae` (native source `b2efcf4f4848b8e50213921ae3e6d23f342bb6db`); 2/2 disjoint native budget positives and 8/8 no-native negatives are **historical parent evidence**, not evidence for this integration tree.
- Context OS donor: #898, `ff6658b2c1a57239836c9745f0e0dddefe6fdd21`, independently audited 38 focused / 2323 full software PASS, exact long/multiline quote preservation.
- World-JEPA donor: #899, `f360b9453eb706755e8afc1c3ca5d62a6e514f5d`, Actions 40671561339 **completed SUCCESS**, raw evidence independent audit pending. Invalid/nonfinite transition input guard remains SHADOW.
- Shared pre-donor source: integrated #896 software-verified `c6cc1bf4a4c6b72948494366dad9a3d7670b7ad4`. The donors change disjoint source/test paths; compare must confirm no silent overwrite of primary-parent C3 paths.
- Frozen runtime `v13/code/v13/runtime.py` Git blob `68e7ed1352800174972558f1e0b0683a42c8689a`; model catalog `v13/code/specs/models.json` `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`. No model/seed/cohort/learning authority change.

## Implementation contract
- Create one real multi-parent Git commit with parent 1 = this preregistration commit, parents 2/3 = the exact donor heads. Build its tree from the preregistered primary parent and import **all** donor-added/modified paths byte-identically; never replace unrelated primary-parent paths.
- Add only an isolated integration-specific source-pinned workflow, not production Runtime._turn edits. It checks exact source/test/runtime/catalog blobs, C3 F1/F5 source admission + postgeneration revocation veto, Context OS quote pinning, World-JEPA fit input guards, and the entire software test suite.
- Negative counterexamples: long multiline quotation, invalid World-JEPA n=1/NaN/mismatched dimensions, active unreadable/conflicting C3 scoped correction; all must remain fail-closed.
- Record raw logs, per-file SHA256, exit codes, Git commit SHA, privacy scan and diff check. Independently audit the raw artifact before claiming integration GREEN. Preserve every failure and avoid retries with changed seed/fixture.
- No Linux-native revalidation on changed integration source yet; original C3 parent native proof is not an integrated native proof. No Redmi, STEP2, B3, Body-JEPA, LP3, Stage11, Age, jepa_weight or whole-system gate promotion. Keep `jepa_weight=0` and Age0 SHADOW.
- A passing integration test is an intermediate checkpoint, not a completed blueprint. Next packages: integrate measured C3 consumer into an authorized runtime seam without violating frozen SourceHandoff; continue registered Body/STEP2/World utility work separately.

## Planned commands (Actions ubuntu-24.04, isolated dependencies)
`python -m unittest -v tests.test_context_os tests.test_context_sleep_f5_crossorgan_20261028 tests.test_world_jepa_fit_input_guard tests.test_world_jepa_coverage_integrity tests.test_source_consumer_admission tests.test_source_consumer_live_render_revalidation tests.test_source_consumer_render_seal tests.test_ask_verified_budget tests.test_c3_cli_no_worker_pinned`
`python -m unittest discover -s tests -p 'test_*.py' -q`
`python -m compileall -q v13/code/v13 v13/code/tests`
`python v13/code/scripts/public_repo_privacy_scan.py --base 3ca9a6d158759f5abc9c00883135487c0a33e3ae --head HEAD`
`git diff --check 3ca9a6d158759f5abc9c00883135487c0a33e3ae HEAD`
