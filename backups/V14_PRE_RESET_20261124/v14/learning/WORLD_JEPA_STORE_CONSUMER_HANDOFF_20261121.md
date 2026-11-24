# V14-004 JEPA & Memory handoff — 2026-11-21

**Lane:** JEPA & Memory  
**Base:** `gpt6/v13-private-remote-bridge-20261111` at `c3c32c05a0374e970d274f8a777a7ab85c067d66` (latest verified branch HEAD at implementation start)  
**Candidate branch:** `jepa-memory/v14-world-jepa-source-disjoint-paginated-20261121` at code commit `2311b039eb49375829876e1bea8f2ac2d6975fe8`  
**PR:** [#2143](https://github.com/RedMentos/Aii/pull/2143) (ready for independent review)  
**Historical V13 files:** unchanged; no runtime.py or online_world.py edit in this slice

## Implemented in this candidate

1. **Source-bound oldest-first T8 feed.** Added `verify_committed_transition_page` to the merged Store authority. It keyset-pages SQLite actions by monotonically increasing local rowid, verifies each candidate through the existing persisted event/source/CorollaryCopy/ActionOutcome authority, and does not repeatedly read only the latest N rows. The scan cursor is numeric Store position, not a learned action ID.
2. **Censoring at the read boundary.** Only observed terminal outcomes (`FINAL`, `FAILED`, `ERROR`, `DEADLINE`, `REJECTED`) can enter the WorldJEPA learner. `CANCELLED`, `ABORTED`, `OUTCOME_UNKNOWN`, and `INTERRUPTED` are excluded before receipt creation; a skipped count is telemetry only. They create no training label, processed ID, prediction error or receiver update.
3. **Source- and content-digest-disjoint holdout.** Experience rows now retain verified `source_id`; the deterministic split hashes `source_id`, not `action_id`, so actions from one source cannot be distributed across train and holdout. Source digest changes, content overlap, ID overlap and incomplete persisted splits fail closed.
4. **Persistent cursor + rollback.** State schema v2 persists the scan cursor alongside the active/previous JEPA checkpoints. Restart resumes the next oldest page. Rollback restores the previous checkpoint and its scan cursor, so the rolled-back page can be replayed.
5. **World/Self/Memory and body readouts.** The trainable WorldJEPA online encoder/predictor and EMA target continue to receive verified numeric T8 outcomes. Separate numeric shadow heads now expose B1_DETAIL, B2_GIST and SELF_MODEL readouts. A source-linked episodic `recall()` API retrieves nearest persisted numeric experiences with source/outcome digests; it returns no raw chat content.
6. **Python compatibility.** The dedicated workflow tests Python 3.13 and 3.14.

## Follow-up review correction — 2026-11-21

QA found that two distinct source_id values can still carry the same source_sha256. This child change partitions on source_sha256, keeps source_id-to-digest stability checks, validates source digest disjointness again on checkpoint readback, and adds a regression where two differently partitioned source IDs share the same digest. The earlier source_id-only rule was insufficient.

## Evidence required / current boundary

- Targeted GitHub Actions run `44848998581` passed on tested PR head `a2788aacdae09bb675fff220cbda4ba74d400912`: Python 3.13 — `57 passed in 4.35s`; Python 3.14 — `57 passed in 7.83s`; `py_compile` passed on both. New regressions cover source grouping, all four censored statuses, a 2,050-action backlog with two oldest-first pages, restart/cursor continuation, numeric parameter/EMA deltas, negative controls, receiver readouts, checkpoint retention and rollback. The additional `v13-private-remote-bridge-tests` run `44848994421` passed. A subsequent docs-only commit records this evidence.
- No local Aii checkout is available in this runner; no LOCAL_LINUX pytest result is claimed. These are GitHub Actions/Linux CI results, not local-device proof.
- No Redmi/Termux connection or owner-authenticated device receipt is available. `REDMI_UNVERIFIED`.
- The consumer is not wired into the normal `Runtime.online_world_update -> OnlineWorld.update` postcommit call. The #2135 exactly-once OnlineWorld candidate remains blocked by its nested SourceHandoff builder hash chain.
- Numeric WorldJEPA/EMA checkpoint changes are real trainable parameters in the isolated Store-backed experiment; B1/B2/SELF heads are readout adapters, not native B1/B2 GGUF weight updates. No GGUF or installed model changed. Learning defaults OFF; no device permission, Age, model or updater setting changed.

## Next executable step

After this PR is reviewed, compose this consumer with the #2135 exact-once OnlineWorld checkpoint in the automatic postcommit path without modifying frozen `runtime.py`. Expose source-bound World predictions to a real cognition/world/planner consumer in SHADOW, compare against no-predictor and replay-only baselines, then test restart/rollback and resource use. Keep the learning/optimizer gates closed by default until the actual runtime opt-in and device proof exist.

**User action:** none.


## Action-conditioned negative-control correction — 2026-11-21

- The source-digest child PR #2147 fixed the identified train/holdout byte-identity leak, but its exact CI run `44852394807` failed on both Python 3.13 and 3.14 in the end-to-end test's `negative_controls_separated` assertion. The trained holdout loss was slightly worse than the shuffled-action control (3.13: 0.480152 vs 0.479097; 3.14: 0.511960 vs 0.510329); zero-action loss was worse in both runs. The source/digest disjointness assertions passed before this failure.
- This exposes a weak action-identifiability signal in the old synthetic fixture, not a reason to relax the negative control. The follow-up branch `jepa-memory/v14-action-conditioned-control-20261121` makes the synthetic transition's route effect explicit in duration and output size, keeps independent nuisance variation, and raises the first JEPA update from 40 to 120 steps. This is a controlled positive test fixture only, not a claim about real-user outcome distributions.
- Follow-up code commit: `52690943522df331b20ab3990c7dd8ee72c1ba84`. Exact CI is pending until the stacked PR is opened. No full local checkout is available because the container cannot resolve `github.com`; no LOCAL_LINUX exact-repository test is claimed. No Redmi receipt, normal Runtime consumer, or native B1/B2 body-weight update is claimed.
- Keep the action-shuffled negative control strict. If the follow-up still fails, investigate action-conditioned predictor/encoder gradients and the synthetic source split rather than weakening the assertion.


## Replay ablation implementation and exact CI — 2026-11-21

- Follow-up PR #2148 adds an explicit replay_mode to the persistent Store-backed learner: uniform remains the default and replays all prior train-fold rows; none is an explicit ablation that trains only on newly admitted train-fold rows while retaining the complete cohort for future replay. Metrics persist the actual fit action IDs, candidate/selected replay counts and old-holdout retention delta. Holdout rows are never used for gradients.
- The SQLite Store test executes a three-step sequence: initial cohort, no-replay update (asserts no old train IDs enter the fit), then uniform update (asserts old train IDs are replayed), followed by checkpoint restore. This is a matched code-path ablation and retention measurement; it does not yet establish that replay improves utility on real user data.
- Exact current PR #2148 head 10e058a7418a5356b96f22f5344a5a3384f96214; CI run 44853980297 PASS: Python 3.13 59 passed in 12.19s, Python 3.14 59 passed in 10.30s, with compile and both test jobs successful. The earlier action-control-only commit also passed 58/58 on both versions, but the 59-test run supersedes it.
- PR chain remains open and unmerged: #2143 (base JEPA consumer), #2147 (source-content digest grouping), #2148 (strict action-control fixture + replay-on/off ablation). No release SHA exists. The PR is not wired into the normal Runtime postcommit consumer and does not change native B1/B2 GGUF weights.
- Cross-lane runtime PR #2145 exact T8 workflow run 44853558359 compiled and passed 52 V14 learning tests but failed one of four Runtime tests because it indexes record["prediction_error"]; the persisted TemporalOutcomes dataclass field is error and the derived learning-intent field is prediction_error. A review comment also records that #2145 still uses newest-first world_model.transitions(limit=64) without the persistent oldest-first cursor, and currently records SHADOW outcomes with weight_updates=0 rather than invoking the JEPA consumer.
- Local full-repository test remains BLOCKED because this container cannot resolve github.com; CI/Linux is the only new execution proof. Phone receipt remains UNKNOWN / REDMI_UNVERIFIED. No Android test, update, model swap, permission change or optimizer activation occurred.
- Next integration: independent review of #2143→#2147→#2148, then compose the digest-disjoint oldest-first receipt page/cursor into #2145's postcommit Runtime consumer and invoke the Store-backed WorldJEPA learner in SHADOW. Keep learning_enabled and optimizer permission closed by default until the user/device opt-in path is explicitly wired and tested.


## Final PR-head and CI readback — 2026-11-21

- Code/test head remains 10e058a7418a5356b96f22f5344a5a3384f96214. The full docs/board/coverage update head 3d8e55441d208eb8aec76cd121cc9f068376a88c was tested by exact GitHub Actions run 44854219157: Python 3.13 59 passed in 8.18s; Python 3.14 59 passed in 7.74s; compile and both jobs PASS.
- Current PR #2148 head is 6fec2dec1534285b654db60349efcd81f81b846c. The only commit after the tested 3d8e head is a research-ledger-only addition documenting JEPA-TTT's replay/retention limitations; no code or tests changed after the tested head. PR remains open and mergeable, stacked on #2147.
- No local exact-repository run, Android install, Redmi receipt, native GGUF change or release is claimed. REDMI_UNVERIFIED; RELEASE_SHA=NOT_RELEASED.


## Latest exact CI readback — 2026-11-21

PR #2148 current head is fb5e75f28dc4ac5b3f547388c48ea387b0e4d4c5. Exact code/test tree head e46b87d7d5cf1da31f58f6561d21193a4dfc9e87 passed GitHub Actions run 44854338438: Python 3.13 59 passed in 6.52s; Python 3.14 59 passed in 8.81s; compile and both jobs PASS. The only later commit is a next-action Markdown table refresh; no code or test file changed after the tested e46b head. The earlier run 44854219157 also passed 59/59 on both versions and is superseded by this readback.


## Backlog-liveness correction — 2026-11-21

QA identified that an insufficient source-disjoint cohort or fewer than two new train-fold rows returned without committing the verified page cursor. Repeated updates therefore rescanned the same oldest page and could starve later diverse outcomes.

The follow-up candidate bumps the Store state schema to v3 and adds a bounded pending_rows buffer. Verified but not-yet-trained receipts and the oldest-first scan cursor are committed together by Store compare-and-swap when a cohort is insufficient. The next update combines the retained rows with the next page; a successful model/checkpoint commit atomically clears the pending buffer and advances the active checkpoint cursor. Rollback restores the previous checkpoint cursor and clears pending rows so those later receipts are re-read. Legacy v2 state is read and migrated in memory without dropping its active/previous checkpoint.

Two new real-SQLite Store regressions cover (1) 64 rows from one identical source digest followed by a diverse second page, and (2) a single new train-fold row under no-replay followed by a second row from the same digest. Both must progress without losing receipts. These are synthetic T8 rows through the real Store and numeric learner, not live user data, Runtime wiring, native GGUF learning or Redmi proof.



## Exact CI verification — pending-cohort liveness follow-up (2026-11-21)

- PR #2150 tested code head: 3743302118298bfe7939ddd913955424e54823c0.
- GitHub Actions run 44856839722 passed the full V14 learning suite and compile on both Python versions: Python 3.13 — 61 passed in 8.43s; Python 3.14 — 61 passed in 8.12s.
- The new two SQLite liveness regressions passed on both versions: same-digest first page resumes with a later diverse page; a one-row no-replay train fold persists until the second matching-fold row arrives.
- Additional private remote bridge push run 44856794261 passed. This is CI/Linux evidence only.
- Exact local Aii checkout tests remain BLOCKED because the container cannot resolve github.com. No Redmi receipt, normal Runtime postcommit wiring, native B1/B2 GGUF learning or device deployment is claimed.
- PR #2150 is a draft stacked on #2148/#2147/#2143, pending independent review. RELEASE_SHA=NOT_RELEASED; REDMI_UNVERIFIED; user action none.


## Superseding exact CI readback — rollback of pending cohort (2026-11-21)

- Current code/test head: afd71180e1c87d9081bf84083315bb7f6a923da6.
- Exact PR workflow run 44857040946 passed compile and the full V14 learning suite on both versions: Python 3.13 — 61 passed in 10.00s; Python 3.14 — 61 passed in 14.53s.
- The existing no-replay liveness regression now also creates a pending one-row cohort after a successful checkpoint, rolls back to the prior checkpoint, verifies that pending rows are cleared and the scan cursor rewinds, then re-reads and learns the previously pending ActionOutcome. This keeps rollback/replay semantics covered, not only the ordinary successful-checkpoint rollback.
- GitHub Actions/Linux only. Exact local repository checkout remains blocked by DNS; no Runtime wiring, native body-weight update or Redmi proof.


## Primary-source research review — 2026-11-21

### R-010 follow-up — JEPA-TTT (full paper + official project page)

- Sources: [arXiv:2610.00722](https://arxiv.org/abs/2610.00722) and [official project page](https://jepa-ttt.github.io/). The full arXiv text and project-page method/ablation/limitations were checked, beyond the abstract.
- Method: self-supervised action-conditioned latent prediction from executed action and next observation; dense windows at every valid temporal offset; predictor parameters, optimizer state and replay buffer persist across episodes. The visual encoder and offline reward head are held fixed.
- Reported scope: eight dynamics shifts in four continuous-control environments, one fixed shift per deployment for 500 episodes; average five-block autoregressive latent MSE reduction 83%, best held-out planning score +153%, AUC +113%. Dense replay adds a small aggregate gain over a dense stream (best score 0.678 vs 0.671; AUC 0.571 vs 0.548); broader temporal coverage contributes more than replay alone.
- Critical limitation: the paper explicitly does not test sequences of shifts, returning to previous dynamics, retention, transfer or catastrophic forgetting. It is therefore a useful predictor-only experimental baseline, not a justification for freezing V14 encoders/targets permanently.
- No code repository or code license was linked from the inspected arXiv paper/project page. No code or weights were downloaded or adopted.

### R-011 follow-up — ER-JEPA (full method and experiment sections)

- Source: [arXiv:2609.36952](https://arxiv.org/abs/2609.36952). The method, replay policies and matched-compute/retention controls were inspected.
- Method: replay stores source-target token pairs and reapplies both next-token and representation-alignment supervision; content, uniform and hard selection share the same replay path. The replay path is removed at inference.
- Reported scope: Llama-3.2-1B-Instruct on five language tasks. On SYNTH at 240.31 PFLOPs, content replay reaches 83.65±1.48% vs 68.75±4.92% for LLM-JEPA; uniform historical replay reaches 85.04±0.54%, 3.80 percentage points above the current-batch replay-loss control, across five seeds.
- Limitation: this is a language-model fine-tuning study with paired token views and large training compute, not a small Android online learner, not source-bound T8 action learning and not proof of B1/B2 cross-organ coupling. No code repository or code license was linked from the inspected arXiv page. No code/weights adopted.
- V14 test implication: retain the existing uniform-vs-none numeric T8 ablation, then compare content/error-prioritized replay only with fixed update/byte budgets and a separate source-disjoint audit holdout. A JEPA-TTT dense temporal-window comparison is only valid once V14 has a genuinely time-ordered multi-step action trajectory; do not synthesize trajectory continuity from unrelated user turns.

These papers reinforce persistent replay and independent retention testing, but neither removes the need for V14's source provenance, rollback, active encoder/EMA comparison, real runtime consumer and Android evidence.


## Strict optimizer-gate regression and final code/test readback — 2026-11-21

- Exact code/test head: 06868d23e681d9ee2a71e52cf7856cd575333514.
- Run 44857847187 PASS: Python 3.13 compile PASS + 62 tests (9.82s); Python 3.14 compile PASS + 62 tests (9.75s).
- The no-new-receipt cursor path now reports the persisted cursor, not a speculative next cursor, and only writes when optimizer_permission is the exact boolean True. The API already rejects non-boolean values; a new regression verifies that integer 1 raises before any Store-state write. A censored-only page with no eligible action does not create a cursor or state.
- Two intermediate test attempts were correctly rejected by CI and corrected without weakening the API: run 44857621212 passed integer 1 into the strict bool API; run 44857721741 then expected a cursor advance for a page containing only censored actions, although the authority deliberately returns no eligible scan row. The corrected exact-head run above is green on both Python versions.
- Current PR head after this handoff update is expected to contain documentation only after the tested code/test head; no Android, native body weights, model swap, or deployment occurred.
