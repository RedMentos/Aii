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
