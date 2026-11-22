# Research & Perception — verified handoff 2026-11-22 16:50 CET

**Keine Nutzeraktion nötig.** Kein Termux-Befehl, kein neuer UPDATE_REQUEST, kein Modell-/Gewichts-/Rechtewechsel und keine Mikrofonfreigabe.

- **Release-development HEAD:** gpt6/v13-private-remote-bridge-20261111 = c4eb82deec915f65894c20d6ebbaf0ebf58fa335 (0 ahead / 0 behind). c4eb changes only a WorldJEPA rollback/source-forget test file; exact commit workflow readback 21/21 SUCCESS. Last code-bearing release remains 283ac1c9.
- **Device receipts:** private #567 confirms installed c4eb, auto-update ON, pipeline runtime/dashboard UP_TO_DATE, last_error NONE. Later #569 HEALTH reports runtime.state=UNAVAILABLE, 983 MiB available of 5,569 MiB and 1,629 MiB free disk. #568 has an opted-in but redacted diagnostic excerpt, so no correctness conclusion. Installed SHA is verified; functional runtime health is inconclusive. No new update request was sent.
- **PR #2346:** current docs/evidence head e68c2488cb474e1b70149f2e3d95f2bbb29220c6; last code-bearing head b72633927e2849f50de69614306e5f27650b6a9c; code commit 1db8fd5fc2e18c115c632cf60577200d68db2c0b. Focused B3 run 45032406629 on b726 passes 52 tests, touched-module py_compile and CLI import/help smoke. Current docs-only head has 12 queued, 1 pending, 1 skipped, 1 cancelled workflows; no exact-current-head green result. Previous broader code-bearing head had 6 success / 7 failure / 1 cancelled / 1 skipped. PR remains DRAFT / NOT_RELEASED.
- **PR #2343:** Boss head 55b76c4c79b24b5ac674366d6bcb32aa15ab1f9d; 7 success / 4 failure / 2 queued / 2 in progress / 1 skipped / 1 cancelled. Current failures include integrated-builder hash mismatch in staged tests on Python 3.13 and 3.14, old-to-new updater migration returning PARTIAL, and Python 3.14 owner-read staged startup refusing the builder. Runtime-deployment-integrity itself passes; the staged consumer chain does not. The observer-overlay anchor was previously flagged and the same-turn workflow remains in progress.
- **C3 budget:** the fair-slice candidate changes C3 reserve to 55% and observers to 45%. A consented Redmi observation still showed slow C3 prefill and only two generated tokens; no same-prompt A/B proves the candidate reserve produces a correct final answer. Keep #2343 DRAFT.
- **LOCAL_LINUX:** CPython 3.13.5 / NumPy 2.3.5. Exact source-reproduced _secure_shadow_output_dir helper: 7 targeted checks PASS. Exact _source_disjoint_split: 12 source hashes × 2 spans (24 experiences), deterministic and source-disjoint; conflict labels, malformed hash, boolean label and undersized-class negatives rejected. Not a full repository import or pytest run. Full checkout remains BLOCKED because GitHub DNS is unavailable to the container.
- **Research:** R-081 Hypnos and R-082 XKV/XBridge/kvloom are recorded. No code, models, weights, data or dependencies were imported.
- **E2E impact:** no new Runtime code or user-visible behavior changed in this run. B3 remains OFF/SYMBOLIC; no real paired native taps, L1 training, receiver injection, permanent weight change, microphone capture or Redmi B3 proof.
- **Next:** Boss repairs the staged-builder hash/migration path and completes the observer/same-turn/C3-reserve evidence; then rebase #2346 and preserve R-080 → R-081 → R-082 → R-083. After accepted release plus a separate device receipt, collect source-bound native B1/B2 pairs with explicit labels and full L0/same-model/no-message/zero/shuffled/OOD and held-out/retention controls. No user action required.

---

# Research & Perception — verified handoff 2026-11-22 16:39 CET

**Keine Nutzeraktion nötig.** Kein Termux-Befehl, kein neuer UPDATE_REQUEST, kein Modell-/Gewichts-/Rechtewechsel und keine Mikrofonfreigabe.

- **Release-development HEAD:** gpt6/v13-private-remote-bridge-20261111 = c4eb82deec915f65894c20d6ebbaf0ebf58fa335 (0 ahead / 0 behind against the exact commit). c4eb is QA/test-focused; exact commit workflow readback 21/21 SUCCESS.
- **Device receipts:** private #567 confirms installed c4eb, auto-update ON, pipeline runtime/dashboard UP_TO_DATE, last_error NONE. Later private #569 HEALTH reports runtime.state=UNAVAILABLE, 983 MiB available of 5,569 MiB and 1,629 MiB free disk. #568's opted-in diagnostic excerpt has redacted input, so no correctness result can be inferred. Installed SHA is verified; functional runtime health is inconclusive. No new update request was sent.
- **PR #2346:** exact branch head b72633927e2849f50de69614306e5f27650b6a9c; code commit 1db8fd5fc2e18c115c632cf60577200d68db2c0b. Exact current head has 6/15 workflow successes, 7 failures, 1 cancelled, 1 skipped. The focused B3 workflow 45032406629 passes 52 tests, touched-module py_compile, and L1 CLI import/help smoke. Failures outside the B3 job remain in shared Lab-Age, migration, deployment, staged/integrated, native receiver, same-turn and audio/arithmetic chains. PR remains DRAFT / NOT_RELEASED.
- **PR #2343:** Boss head 1084bf902c9d6bebd83436d7d7908d382ddd1984, 8 pass / 8 fail / 1 skipped. Remaining exact blockers: stage/deployer source pin mismatch and observer overlay anchor mismatch. The fair-slice candidate changes C3 from the prior 87%-style reserve to 55% (16.5 s in a 30 s turn) while assigning 45% to observers; no Redmi A/B proves the reduced C3 window is safe for answer quality. Do not rebase #2346 until Boss has a green exact matrix and the C3 trade-off is explicitly resolved.
- **LOCAL_LINUX:** CPython 3.13.5 / NumPy 2.3.5. Exact source-reproduced _secure_shadow_output_dir helper: 7 targeted checks PASS (private writes, 0700 mode, descriptor path, outside-write prevention, top-level/nested symlink rejection, traversal rejection). Exact source-reproduced _source_disjoint_split: 12 source hashes × 2 spans (24 experiences), deterministic and source-disjoint; conflict labels, malformed hash, boolean label and undersized-class negatives rejected. This is not a full repository import or pytest run. Full checkout remains BLOCKED because GitHub DNS is unavailable to the container.
- **Research:** R-081 Hypnos and R-082 XKV/XBridge/kvloom were read and recorded. No code, models, weights, data or dependencies were imported.
- **E2E impact:** no new Runtime code or user-visible behavior changed in this run. B3 remains OFF/SYMBOLIC; no real paired native taps, L1 training, receiver injection, permanent weight change, microphone capture or Redmi B3 proof.
- **Next:** Boss repairs #2343; then rebase #2346 and preserve R-080 → R-081 → R-082 → R-083. After accepted release plus a separate device receipt, collect source-bound native B1/B2 pairs with explicit labels and the full L0/same-model/no-message/zero/shuffled/OOD and held-out/retention controls. No user action required.

---

# Research & Perception — B3 paired native tap handoff

Date: 2026-11-22 13:00 CET

## Source of truth
- Current release-development branch: `gpt6/v13-private-remote-bridge-20261111`
- Verified HEAD at branch creation and handoff: `c4eb82deec915f65894c20d6ebbaf0ebf58fa335`
- Candidate PR: https://github.com/RedMentos/Aii/pull/2346
- Candidate branch: `research-perception/v14-b3-paired-native-current-20261122-run11`
- Code checkpoint after B3 fixes: `20a510d829d34d5847f3adde5546cf5cef5d3fe7`; the PR branch subsequently advances for documentation-only handoff commits, so refresh the live PR head before review.

## Actual runtime path added
1. `:tap pair` queues a cancellable Runtime job.
2. `Cognition.tap_pair` invokes separate native B1_DETAIL and B2_GIST prefill taps for one event/source span/generation.
3. B1 is represented with source-aligned fine native slots; B2 uses its own tokenizer and adaptive Gist readout. The implementation never assumes token-index alignment between different model families.
4. `B3PairedTapPacket` binds tap packet IDs, model revisions, token geometry, feature file hashes and source provenance. Numeric feature artifacts are stored under the local data blob directory.
5. `:b3 pairs` reports unique source pairs, pinned revisions, fine/Gist slot counts and the 64-pair threshold.
6. `b3train.train_l1_shadow` accepts only explicit labels and provenance. It splits by full source SHA-256 groups, rejects conflicting labels, requires at least four source groups per class and binds L0 v2 evidence to exact train/test indices, source groups and seeds. It writes shadow adapter artifacts only.

## Safety / claim boundary
- No foreign state is injected into a model.
- No B1/B2 foundation weights are changed.
- `injection_authority=0`, `learning_authority=0`, `body_learning_authority=0` remain enforced.
- L1 training is not a native receiver proof and not an accepted B3 channel.
- Production B3 remains OFF/SYMBOLIC until same-source native taps, independent labels, L0 baselines, same-model parity, no-message, zero, shuffled and OOD controls, held-out utility, role retention, restart and target-runner measurements all pass.

## Evidence
- **CI / exact code checkpoint `20a510d829d34d5847f3adde5546cf5cef5d3fe7`:** `V13 B3 paired native tap regression` run `45021891591` PASS. All 50 tests passed, touched Python modules compiled, and the Termux L1 shadow CLI import/argument-parser smoke passed. This is GitHub Linux CI, not Redmi/Termux execution.
- The first B3 CI attempt exposed two real issues: the completion check lacked a literal `:tap pair` help entry, and the B3 utility scorer updated callosum state despite `RECORD_ONLY`. Both were corrected; the current B3 run passes. `Callosum.outcome` now returns `SKIPPED_RECORD_ONLY` before consuming pending utility messages when the Runtime is in `RECORD_ONLY`.
- LOCAL_LINUX CPython 3.13.5 / NumPy 2.3.5: exact `_source_disjoint_split` helper passed 32 source hashes × 2 spans; 52 train / 12 test; no hash crosses splits; deterministic; negative controls for conflicting labels, undersized classes, boolean labels and malformed hashes all rejected.
- LOCAL_FULL_REPOSITORY: BLOCKED because no repository checkout is available and `git ls-remote` cannot resolve `github.com`. No full local `pytest` or compile pass claimed.
- CI beyond the focused B3 job: staged/integrated, role-specific tap-provenance, JEPA and deployment workflows were queued/in progress at the last poll. Do not call the PR merge-ready until all required exact-head checks finish.
- TERMUX/REDMI: REDMI_UNVERIFIED. No phone, microphone, native B1/B2 weights or live device was accessed.

## Prior work and failure reconciliation
- The previous #2313 branch was stale and failed exact-head staged integration; it also had a test assertion expecting two seed values when the code correctly returned three for seeds `(3, 7, 11)`.
- #2317 fixed the source-disjoint split and the seed assertion; its focused B3 workflow passed, but staged/integrated CI still failed on stale composed Runtime pins.
- This PR ports only the B3-specific source changes onto current release HEAD `c4eb82`, preserves the current `operator.py` voice path, and does not copy stale composed builder pins or other agents' overlays.

## Research note
- R-080 records Hypnos (arXiv:2611.24637v1, posted 2026-11-18): low-cost prototype wake updates plus replay-based sleep consolidation on CORe50/FPGA. It is not an LLM/JEPA/voice result; the official repo README is WIP and no LICENSE file was visible. No code or weights reused.

## Next concrete actions
1. Check exact PR #2346 head and focused B3, staged and integrated workflows.
2. Request Core/QA review of Runtime/contract composition and confirm no source-pin overlays were omitted.
3. If CI and review pass, let Boss integrate on the current release branch and update the shared board/coverage ledger.
4. Only after integration, and only through the existing explicitly authorized local runtime, collect actual same-source B1/B2 pairs. Do not issue new remote commands or change device settings.
5. After enough independent pairs and human-provided labels exist, run L1 shadow training with source-disjoint L0 evidence and held-out/retention controls. Keep B3 OFF until all Canon gates pass.

## User impact
No immediate phone or user-visible behavior changes. No user action is required for the repository candidate. No manual Termux command, microphone grant, model download, weight swap or update request.

---

## Checkpoint — B2 native token-span alignment / CacheBack review (2026-11-22 18:00 CET)

### New executable path
- B3 paired packet schema advanced to /4.
- B3PairedTapPacket.native_token_readout now persists the exact B2_GIST native token IDs and a lossless, source-bound character interval for every B2 token, separately from the adaptive Gist pooling slots.
- training_batch() now exports sender/receiver token IDs and spans in both B1→B2 and B2→B1 directions plus an explicit character-interval intersection map. It never equates token indices across the different tokenizers.
- load_pair() rechecks the B2 token plan against the persisted native tap ID, token IDs, source reference and feature geometry after restart.
- The contract rejects token-span gaps, identity drift, token-count/dimension mismatch and any nonzero injection/body-learning authority. Legacy /3 packets are intentionally counted as legacy by the existing :b3 pairs schema filter; they are not silently interpreted as /4.

### Exact code/test evidence
- Code-bearing commit: 7229c93b143d5f9d81ed1a3d6a376764d4b307e0.
- Exact focused GitHub workflow: V13 B3 paired native tap regression, run 45051365567, PASS. The job ran 54 tests; the touched-module compile and Termux L1 shadow CLI import/argument-parser smoke also PASS.
- Earlier iterations exposed and fixed two test-contract mistakes: Gist plans do not store a duplicate token-ID list, and the reverse claim-limit string changed with the new source-span output. The final focused run is green.
- LOCAL_LINUX isolated reproduction: CPython 3.13.5 / NumPy 2.3.5; py_compile PASS for the isolated source-span exercise; different-tokenizer character-overlap forward/reverse coverage PASS; source-gap negative control REJECTED; UTF-8 byte-piece boundary smoke PASS. This is not a full repository import or full pytest run.
- LOCAL_FULL_REPOSITORY remains BLOCKED: no Aii checkout is mounted and GitHub DNS is unavailable in the container. Full local pytest is not claimed.
- Other staged/integrated, native receiver, role-specific tap, JEPA, Lab-Age and deployment workflows for this PR head were still queued at last read. Do not mark the PR merge-ready from the focused B3 result alone.
- Latest branch documentation checkpoint: a4a9ce971364020f9558e2a8106fe4b8291ba3e6; it appends research/handoff text after the code-bearing commit without changing code. Branch remains one commit behind the release branch and must not be rebased until Boss PR #2343's exact matrix is green.

### Research update
- R-087 now records a full-text review of Rossi et al., Receiver-Conditioned Latent Communication gives 94% CacheBack, arXiv:2609.32046v1 (2026-09-25, preprint), plus the Apache-2.0 CacheBack repository/dependency readback.
- Useful idea: condition evidence selection on the receiver's actual query. Not directly reusable for B1/B2: the paper's public API explicitly requires the same model or matching copies, does not support cross-model alignment, and its reported evaluation uses an 8×80-GB H100 node. No CacheBack dependency or model was imported.
- Current B3 packet change provides source-span/token-ID alignment metadata only. It does not supply receiver embedding rows, KV transfer, semantic utility, native injection or accepted B3.

### Integration handoff
- Core's row-only receiver-token embedding extractor is still the required next seam. It should accept the exact receiver model revision plus requested token IDs and return only those embedding rows with verified dimension/dtype/quantization metadata; never materialize the full vocabulary matrix on Android.
- Perception can then train/evaluate a source-disjoint low-rank sender-tap → receiver-input projector using the new overlap map, with exact receiver rows as targets, held-out sources, OOD, shuffled/zero/no-message controls, parameter-diff, retention, restart and rollback evidence.
- Core PR #2350's approval/hash checks do not themselves implement that row extractor. B3 stays OFF/SYMBOLIC and no receiver injection authority is granted.

### Device/deployment boundary
- A fresh private V13OBS read was available, but it is not a test of this PR. The existing updater reports UP_TO_DATE at installed release c4eb82deec915f65894c20d6ebbaf0ebf58fa335; this candidate is not released or deployed.
- The latest private turn still shows B1/B2 TIME_BUDGET with zero valid offers and no native latent exchange / C3 semantic-use proof. C3 prefill remains slow. No new update request, remote command, model/weight change or permission change was sent.
- TERMUX/REDMI proof for this code remains REDMI_UNVERIFIED.

### Next actions
1. Core: implement the pinned, read-only, row-bounded receiver-token embedding extractor against llama.cpp's exact internal tensor ABI, with quantized-row and overflow tests plus Android ARM64 cross-compile.
2. Perception: consume only those rows through the new training_batch() span map and build a low-rank receiver-input projector; do not train from synthetic vectors as if they were model evidence.
3. Boss/Integrator: update the shared V14 next-action/board only after reviewing this exact checkpoint; do not rebase #2346 until #2343's staged/deployer source pins and resource trade-off are resolved.
4. Keep B3 OFF/SYMBOLIC until real native receiver utility, source-disjoint holdout, OOD, retention, restart and target-device evidence pass.

No user action required. No model, weight, dependency, device setting or production route changed.



---

## Checkpoint — source-disjoint receiver-input projector candidate (2026-11-22 23:00 CET)

### New executable path
- Added `v13/code/v13/b3projector.py`: a factorized low-rank B1↔B2 sender-state → receiver-input-row projector. It consumes the persisted B3 paired-tap /4 records through `b3pairs.load_pair`, recomputes the exact character-interval overlap map, and never equates token indices across tokenizers.
- The receiver target is the exact row from the receiver model's input embedding table for each aligned receiver token ID. The adapter is not trained against the receiver's final-layer tap and does not pretend that equal hidden dimensions imply compatible semantics.
- The trainer uses trainable A/B matrices with Adam gradients, a deterministic source-SHA-disjoint holdout, and no-message / shuffled-input controls. It reports held-out MSE, cosine, pairwise-cosine Spearman and mutual-kNN edge Jaccard. Checkpoints bind sender/receiver roles, revisions, actual model SHA-256 values, the pinned llama.cpp revision and the receiver-row export hash.
- Adapter checkpoints are unique/no-overwrite, mode 0600, integrity-hashed and explicitly zero-authority. A loaded candidate must pass its shadow-alignment gate and exact model/role binding. Foundation weights are never edited.
- Exposes `train_from_pairs(cognition, packets, rows, row_manifest, ...)` as the executable consumer API. It calls the real persisted-pair loader, recomputes source-span alignment, and returns a zero-authority candidate checkpoint. No CLI or automatic invocation is added until Core's native row exporter and runtime contract are ready.

### Required Core row-export seam
The Core native receiver still does **not** export receiver input rows. This Perception consumer expects the following bounded read-only contract from Core:
- Core supplies an in-memory mapping `{token_id: float32[embedding_dim]}` plus manifest schema `v14.llama.receiver-input-rows/1`.
- Manifest fields: `receiver_role`, exact `model_revision`, actual model `model_sha256`, pinned `runner_revision`, `embedding_dim`, sorted `token_ids`, `row_count`, `rows_sha256`.
- The row digest is SHA-256 over sorted little-endian int64 token IDs followed by the row-major little-endian float32 matrix. Only token IDs requested by the paired packets are exported; never the full vocabulary matrix.
- Current code caps training examples/row exports at 1,024 and feature elements at 4,194,304. The native exporter must reject invalid token IDs, quantization block/row offsets, overflow, wrong model bytes and unsupported tensor layouts before returning rows.

### Local test evidence
- **LOCAL_LINUX_ISOLATED / CPython 3.13.5 / NumPy 2.3.5:** 7/7 synthetic unit tests PASS. They cover row manifest/model binding, forward and reverse character-span alignment, persisted-pair consumer wiring (with only the storage loader mocked), nonzero gradients and parameter changes, source-disjoint holdout, shuffled/no-message controls, checkpoint round-trip, no-overwrite and authority-escalation rejection.
- **LOCAL_LINUX_ISOLATED:** `py_compile` PASS for projector module and tests. Single-thread BLAS environment used. These are isolated algorithm/contract tests, not a full Aii checkout, real GGUF tap or native receiver run.
- **LOCAL_FULL_REPOSITORY:** BLOCKED — no Aii checkout is mounted in this execution environment. No full-repository unittest/compile is claimed.
- **CI:** pending on the exact updated PR head.
- **TERMUX/REDMI:** REDMI_UNVERIFIED. No phone, model, microphone, updater, native receiver or installed app was accessed.

### Research note ready for central ledger (R-088; Boss append pending)
- **StateBridge**, Peng et al., arXiv:2608.13317 (2026-08-13), COLM 2026 release; official repository revision `3f6bf5442c6e8848555a6132516e6d36f35444fb`, Apache-2.0 code. It uses whitening + orthogonal Procrustes + norm calibration + vocabulary anchoring and reports best/tied-best on 22/26 model-task pairs. Crucial boundary: the released method explicitly targets homogeneous agents sharing the same pretrained weights; its repository depends on PyTorch/Transformers and reports A100-80G runs. It is a geometry-preserving baseline, not a drop-in for independently trained B1/B2 on Android.
- **XBridge**, Yang et al., arXiv:2608.11676 (2026-08-12), preprint. It combines discrete receiver-vocabulary/entity anchors with a continuous latent-enrichment bridge; reports 264M trainable parameters and 7 benchmarks across Llama/Qwen/Mistral. It is direction-specific and evaluates one exchange, not multi-turn latent dialogue. No official code/license link was found on the primary arXiv page; no reuse is selected.
- **Architecture-Dependent Causal Transfer**, Piepereit, arXiv:2608.16347v2 (2026-11-09), preprint. With 0.5B–7B models and 30 causal trials per pair, projected-state retrieval reached 45–50% vs 5% chance for decoder-only pairs, but generation-level causal transfer was positive for only one pair (Qwen2-0.5B→Phi-3-mini: 23.3% vs 0% negative control; FDR-corrected p=0.047); both Mistral-targeting pairs failed despite similar retrieval alignment. The paper explicitly warns that representational similarity is not semantic-use proof and identifies monitoring risk from opaque activation channels. No code/license reuse is claimed.
- **V14 adaptation:** keep a small source-disjoint adapter as one candidate only; measure geometry as well as reconstruction; require actual receiver-generation task utility, same-model parity, zero/shuffle/source-exact controls, OOD, retention, restart and rollback. A passing embedding-alignment metric must never be renamed “semantic latent communication”.

### Integration / deployment
- This is a Perception-owned continuation of PR #2346 and remains DRAFT. The PR base is still release SHA `c4eb82deec915f65894c20d6ebbaf0ebf58fa335`; the shared branch has a later documentation HEAD, so Boss must reconcile/rebase the candidate after the exact combined matrix is green. No force-push.
- Core PR #2350 currently verifies local probe approval and actual model-byte hashes; it does not implement the row-only extractor. Core owns that native ABI seam. Perception owns this consumer/trainer.
- Production B3 remains OFF/SYMBOLIC; `semantic_use_proven=false`, `production_route=false`, receiver-injection authority 0, body-learning authority 0. No release/deployment or updater request.
- **Next concrete step:** Core supplies the pinned row-only extractor and exact manifest; then Perception runs the projector against real paired B1/B2 taps and compares source-exact, projected, zero, shuffled and no-message receiver outputs. Boss updates the shared board, research ledger and user-next-action after reviewing this handoff.
- **User action:** none. No model download/swap, weight change, permission change or manual Termux command.


### Implementation correction (2026-11-22)
The first draft's file/CLI wrapper was removed before publication to avoid inventing a row-export transport or an unverified Runtime command. The committed interface is the direct Python API `train_from_pairs`; it becomes runnable end-to-end only when Core supplies the exact row mapping/manifest. No native row export, native receiver injection or Redmi proof is implied.
