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
