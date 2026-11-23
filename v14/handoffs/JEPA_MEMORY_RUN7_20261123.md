# JEPA & Memory handoff — 2026-11-23

## Branch / PR state

- PR: https://github.com/RedMentos/Aii/pull/2405 (DRAFT, stacked; NOT_RELEASED)
- Branch: `jepa-memory/v14-temporal-episodic-recall-20261123-run7`
- Code/test checkpoint: `80ed58ff0b1e8351cbe8f68887ef7db6f6abba20`
- PR base branch: `qa/v14-jepa-source-lifecycle-rebase-20261123-run16`
- The base branch currently points to `c5d847ca36567ea265610b235941bf251f1425fa`, while this PR was opened against older base `de4143790bc9ff7e3dc32c40fbc2a4fe9d09dd64`. GitHub compare reports 22 commits behind and the PR is non-mergeable. QA/Boss must recompose the exact changes onto the current QA head; do not merge this stale stack directly.

## Concrete code change

1. `v13/code/v13/world_jepa_temporal.py`
   - Added one Runtime-scoped temporal consumer shared by idle postcommit and bodyview.
   - Added `warm_active_checkpoint`; idle processing warms the active read-only checkpoint, including when learning permission is off.
   - Added `warm_only` to receiver matrix and episodic recall. A cold checkpoint returns `MODEL_NOT_WARM`; foreground B1/B2 never calls the cold loader.
   - Episodic candidate embeddings are processed in batches of 32 with cooperative deadline checks between batches.
2. `v13/code/v13/sleep.py`
   - Postcommit temporal update uses the Runtime-scoped consumer, so the same checkpoint cache is available to B1/B2 after idle warm-up.
3. `v13/code/v13/bodyview.py`
   - B1/B2 bodyview reads only a warm checkpoint.
   - Prompt-visible contract includes `native_body_consumed=false`, `native_body_weights_changed=false`, and `decision_authority=NONE`.
   - Removed optional unsupported-action detail from the prompt (it remains in the audit) and shortened the note to `prediction_only` to preserve the 700-character budget.
4. Tests
   - Restored strict prompt-visible weight-boundary assertion.
   - Added a cold-loader negative control and a `Cognition.offer` test with a deliberately slow loader; the cold foreground path must not call it.
   - Added a cooperative episodic-recall budget check using a deliberately slow latent call; it must stop after at most the query plus one candidate batch.

## Existing learner evidence retained in this branch

The synthetic SQLite/T8 test suite already asserts:
- `parameter_delta_norm > 0` and `ema_target_delta_norm > 0`;
- source-disjoint train/holdout windows and separate sessions;
- shuffled-target and shuffled-action negative controls;
- persisted optimizer state and exact checkpoint SHA after restart;
- rollback to the prior checkpoint and retry of pending rows;
- replay-on/off matched-step ablation and A→B→C→A retention cohorts;
- source-forget protection while active or rollback checkpoints retain the source.

This is **numeric predictor/EMA learning in the local synthetic Store harness**, not GGUF base-weight training, not native B1/B2 weight updates, and not proof of Android learning.

## Test evidence / environment

- Exact code checkpoint `80ed58ff0b1e8351cbe8f68887ef7db6f6abba20`: GitHub Actions runs `45108720991` (Python 3.13 + 3.14 temporal JEPA) and `45108721030` (offline bridge/security) were queued at the last check. No PASS claim until both complete.
- Earlier CI iterations exposed and fixed a duplicate episodic cold load, the missing prompt-visible weight-change field, and prompt-budget overflow. The final exact-head run is intended to verify the complete fix plus slow-loader and budget negatives.
- Local exact-source checkout/tests are BLOCKED: `git ls-remote` could not resolve GitHub and the archive endpoint was inaccessible. GitHub Actions is the available exact-source environment this run.
- Current parent QA PR #2402 at `c5d847ca36567ea265610b235941bf251f1425fa` has five failing jobs; their logs show the same missing prompt-visible `native_body_weights_changed=false` assertion. This branch contains the fix, but the parent branch does not yet.

## Product boundary / Redmi

- The delivered B1/B2 path is still **source-grounded SHADOW prompt readout**. It is not native latent injection or cross-organ model-weight learning.
- No model, weight, permission, user data, or device state was changed. No release SHA was produced: `NOT_RELEASED`.
- New code is `REDMI_UNVERIFIED / NOT_DEPLOYED`.
- The shared V14 handoff's last recorded private Redmi receipts (#690–693) show installed release `aed1d2`, auto-update reported enabled, but also a 57.74 s turn, 41.63 s TTFT, and zero valid B1/B2 offers. Those are historical recorded observations, not a fresh device check in this run.

## Research note

Sony's Future-Aware Retrieval work suggests a useful next research direction: train cue-specific retrieval utility from future outcomes, but keep inference retrieval future-blind. The public `sony/far` implementation is CC BY-NC 4.0 and GPU-heavy; no code, weights, or dataset were copied. A small V14 cue-utility head should be trained from delayed T8 outcomes and compared against recency, latent-distance, random, and shuffled controls with disjoint retention holdouts.

## Next executable steps

1. Wait for exact-head Actions and fix any remaining failure.
2. QA/Boss to recompose the exact JEPA files/tests onto the current #2402 head while preserving newer source-lifecycle work, then rerun the integrated chain.
3. Coordinate a typed numeric receiver/adapter contract with Core. Keep native latent transfer and B1/B2 weight learning OPEN until an actual consumer and numeric weight evidence exist.
4. After an approved release, use only the verified normal updater and obtain a fresh private device receipt. Do not issue a new Termux command or model swap unless the updater is unavailable/defective and a manual step is truly necessary.

**User action: none.**

## Run 8 — exact-head correction and research handoff (2026-11-23)

- Recorded run start: 2026-11-23 05:06 CET. Completion timestamp: UNKNOWN (no measured platform completion clock).
- Code branch: jepa-memory/v14-temporal-episodic-recall-20261123-run7. Exact current code/test HEAD: 30c5522e4ff676d591a81427091d990e09389f37. Readback confirms the branch ref and bodyview/test blobs.
- Repaired the exact #2405 CI failure at prior code head 80ed58ff: the compact prompt note had been changed to prediction_only while the strict regression still required the explicit phrase "not fact/permission". Restored the explicit epistemic note "prediction; not fact/permission" and removed the redundant episodic_note field to preserve the 700-character body-state envelope. The structured fields native_body_consumed=false, native_body_weights_changed=false and decision_authority=NONE remain required and tested.
- Exact-head checks for 30c5522 are QUEUED at readback: temporal-jepa Python 3.13 and 3.14 (workflow 45110132321) and offline-bridge-security (45110132324). No PASS is claimed yet. Prior head 80ed58ff had 20/21 temporal tests passing and one note-contract assertion failing in both Python versions; offline-bridge-security passed. The latest fix is awaiting exact-head execution.
- LOCAL_LINUX full checkout/pytest/compile remains BLOCKED: no checkout mounted and GitHub DNS/archive access failed. GitHub Actions is the only exact-source test environment available here. REDMI_UNVERIFIED / NOT_DEPLOYED; no phone, model, weight, permission or user data was changed.
- PR #2405 remains DRAFT / NOT_RELEASED and stacked on the QA source-lifecycle branch. Its recorded base SHA de4143790bc9ff7e3dc32c40fbc2a4fe9d09dd64 is older than QA PR #2402 head c5d847ca36567ea265610b235941bf251f1425fa; do not merge the stale stack. QA/Boss must recompose the exact bodyview, temporal learner, sleep and test changes onto the current QA head while preserving the newer source-forget chain, then rerun the complete staged/integrated/optimizer/migration matrix.
- New research PR #2413 adds append-only ledger entry R-107 on the current documentation branch: Future-Aware Recall (arXiv:2609.34677) reviewed in full; sony/far main revision and CC BY-NC 4.0 verified; CUDA/H100-scale dependencies and simulation-only evidence documented. No code, weights or data reused. Proposed future experiment is a future-blind cue-utility head trained only from delayed committed T8 predictive utility, with source/session-disjoint holdouts and recency/latent/random/shuffled controls. This is a hypothesis, not current functionality.
- Canon boundary: temporal numeric JEPA/EMA/checkpoint updates and source-verified episodic retrieval remain synthetic Store/Runtime evidence. B1/B2 receive compact source-grounded SHADOW prompt readouts only. No native learned latent transfer, B1/B2 body-weight changes, GGUF training or Redmi learning is proven.
- User action: NONE. No manual Termux command, update request, model download/swap or permission change.


## Latest private device observation cross-check — 2026-11-23 04:05:46Z

The private V13OBS issue #115 is the newest receipt read during this run. Installed release remains aed1d2b826290c95c70356b5d8b864b5ef382be4; auto-update is enabled; Runtime and Dashboard report UP_TO_DATE with no last error. This is only deployment metadata, not acceptance. The latest stored turn remains 57.74 s total / 41.63 s TTFT / 38.95 s prefill / 2 generated tokens; B1/B2 native probes remain TIME_BUDGET at 53.2/54.2 s with zero valid offers in the five-turn aggregate. Correctness/semantic use remain unproven. The zero-mapped-process snapshot is instantaneous and not free-RAM or residency proof. Official Age remains 0; Lab selector 10/effective stage 5; physical feature execution false; learning commit authority still separately gated. No CHAT_SEND, UPDATE_REQUEST, LOG_PAGE, model/weight change, permission change or device mutation was made. This receipt was separately summarized to Boss/QA and in sanitized form on #1904; private transcript/device data were not copied.


The first R-107 documentation PR #2411 was closed as duplicate after its base branch advanced; replacement PR #2413 is based directly on current #2410 head and contains the same append-only ledger entry. No research content was lost.


## Exact-head CI follow-up — 2026-11-23

- The exact code/test head 30c5522e4ff676d591a81427091d990e09389f37 completed and FAILED the temporal-jepa suite in both Python 3.13.18 and 3.14.10: 20 passed, 1 failed. The failing consumer test showed that adding the explicit epistemic note pushed the 700-character prompt envelope over budget; bodyview removed the entire optional temporal context. This was a real prompt-budget regression, not a note assertion mismatch. Offline-bridge-security on that head passed.
- Fixed on exact current code/test head b44340d4346a316e78deddf381c7762758c6fa18: per-action support counts remain in the full source-bound audit but are no longer duplicated in each compact B1/B2 prompt row. The prompt still carries the explicit prediction/not-fact-permission note, numeric prediction, uncertainty, 12-hex checkpoint, source fingerprints, and native-body/authority false fields. Added regressions for compact B1/B2 row shapes and audit support counts >=8.
- Exact current-head checks were queued at readback: temporal-jepa Python 3.13 + 3.14 and offline-bridge-security. No PASS is claimed until these exact jobs finish. The prior 30c failure remains in history; do not erase it.


## Prompt-budget follow-up — exact current candidate (2026-11-23)

- Exact current code/test SHA: 89c0c7fcf3a598d7b99e2b07299f3aac4f82690b. Readback confirms the prompt still has the explicit prediction/not-fact-permission note, and per-action support counts are kept in the full audit rather than repeated in prompt rows.
- The 30c failure was repaired in two steps: (a) remove per-row support counts while preserving audit support >=8, (b) when the temporal readout is present, omit only the static WORLD_STATE scope label from the compact prompt; persisted WORLD_STATE is unchanged and mode + observed_actions remain visible. Added regression assertions for the compact world metadata and B1/B2 row shape.
- Exact-head temporal-jepa 3.13, temporal-jepa 3.14 and offline-bridge-security were QUEUED at readback (workflow 45111415768/45111415769). No PASS is claimed. Wait for this exact head before further integration.


## QueryPacket negative-control correction — exact current head (2026-11-23)

- Exact code/test SHA: b955b58a547223c1c823698d8f58ac43fc3b9ecb.
- The prior 89c0c7f head retained the temporal view within the 700-character budget, but exposed a second test assumption: the cold B1 negative-control offer correctly writes its own QueryPacket, so the event has three QueryPackets (cold B1, warm B1, warm B2), not two. The failure was at the test's count assertion after the temporal receiver prompt assertions had passed.
- Fixed the test to select only QueryPackets whose referenced BODY_STATE source has schema V14_BODY_STATE_WITH_WORLDJEPA_AUDIT/2, then require exactly the two warm B1/B2 temporal receiver queries. The cold query remains a required negative control and is not miscounted as a temporal receiver. Source-ref provenance and full audit checks remain for both warm queries.
- Exact-head Python 3.13, Python 3.14 and offline-bridge-security checks for b955b58 are IN_PROGRESS/QUEUED at readback; no PASS yet. The 89c head had 20/21 pass and one test-count assertion failure in Python 3.13; Python 3.14 was still in progress at that time. Postcommit tests were skipped after the temporal test failure; they must run on a green exact head.


## Omitted-vs-created receiver audit correction — current exact candidate (2026-11-23)

- Exact code/test SHA: 3b5da6cd8c74b42835e4ea7ea17988afa99a888b.
- The prior b955b58 head confirmed the compact prompt and authority checks but the query filter still counted the cold B1 negative-control BODY_STATE because it carries the same audit schema with status OMITTED. The test now distinguishes temporal receiver queries by audit status READOUT_CREATED and separately requires at least one non-temporal/omitted query, so the cold negative control remains visible without being misclassified as a trained receiver.
- Exact-head temporal-jepa Python 3.13, temporal-jepa Python 3.14 and offline-bridge-security were IN_PROGRESS at readback (workflow 45111861235 / 45111861096). No PASS is claimed yet. Earlier b955 head: both temporal jobs failed only at the overly broad query filter (20 passed / 1 failed each); offline bridge security passed.


## Postcommit exact-head regression correction — current candidate (2026-11-23)

- Exact code/test SHA: 9c61fb8a43c520ed91b794281b40af656fcc5760.
- On prior head 3b5da6c, both Python 3.13.18 and 3.14.10 passed the full temporal T8/JEPA/source-forget regression step. The subsequent postcommit worker/restart/rollback step ran 15 tests and failed one fixture assertion: the receiver's source text is the complete query string "The verified action history is ready. Estimate the next action duration.", while the assertion incorrectly expected only "verified action history". The quote is still checked in the captured receiver output; the source ref correctly points to the full original query.
- Fixed the assertion to compare the referenced source bytes with the fixture's exact receiver_text, preserving the provenance check rather than weakening it to substring matching.
- Exact-head temporal-jepa Python 3.13, Python 3.14 and offline-bridge-security checks for 9c61fb8 are IN_PROGRESS at readback. No PASS claim yet. The postcommit test step must finish green on this exact head before integration.


## B2 gated receiver test setup — current exact candidate (2026-11-23)

- Exact code/test SHA: d098095779abaaff9b8520277436fad42dd8081a.
- On 9c61fb8, temporal T8/JEPA tests passed but the postcommit receiver test failed because B2 body-state is OFF by product default (config.py explicitly defaults b2_offer_body_state=False after the prior STEP2 finding that body_state hijacked 41/50 B2 offers). The test was incorrectly expecting B2 to receive it without opting in.
- The integration test now explicitly sets runtime.cfg["b2_offer_body_state"] = True for this receiver experiment only. Product default remains OFF; no default, installed setting or user preference was changed. This verifies the gated B2 path without silently reintroducing the old B2 hijack.
- Exact-head temporal-jepa Python 3.13/3.14 and offline-bridge-security checks for d098095 are QUEUED/IN_PROGRESS at readback; no PASS claim yet. Prior 9c61 temporal tests passed in both versions, postcommit tests ran 15 and failed one B2 opt-in fixture assumption.
