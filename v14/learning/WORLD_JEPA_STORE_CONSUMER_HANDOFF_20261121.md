# V14 JEPA Store-backed WorldJEPA consumer — handoff 2026-11-21

**Owner:** JEPA & Memory. **Work item:** V14-004.  
**Dependency/base:** boss/v14-temporal-outcome-semantics-20261120 at cb8fa5555b9b4ed577676ef7d62d135dc67aaa17.  
**Candidate branch:** jepa-memory/v14-world-jepa-store-consumer-20261121-r2.  
**Status:** implementation candidate; not merged, not released, not runtime-wired.

## What was added

v14/learning/world_jepa_consumer.py implements a Store-backed consumer for VerifiedT8Transition receipts from t8_store_authority.verify_committed_transitions().

- Reuses the existing V13 WorldJEPA encoder/predictor/EMA implementation, the deterministic source-disjoint world_jepa_action_outcome_adapter split, and the existing private WorldJEPA checkpoint format. No new third-party package or external model was introduced.
- The consumer admits only Store-verified terminal T8 outcomes. It retains bounded numeric replay rows plus action IDs and source/outcome SHA-256 digests; it does not copy source text into the V14 learning state.
- It trains on the train partition only and measures the disjoint holdout before/after. It also records shuffled-action and zero-action controls, old-holdout retention, online-parameter delta, EMA-target delta, and checkpoint SHA before/after.
- A small role-specific readout is trained from predicted latents: B1_DETAIL predicts action duration/output size; B2_GIST predicts terminal success probability. These are numeric SHADOW receiver heads, not native B1/B2 model activations or GGUF weight updates.
- The checkpoint is written as a fresh immutable private file. Store.set_state(..., expected=version) atomically commits the checkpoint pointer together with processed receipt fingerprints, replay memory, train/holdout IDs, receiver heads and self-metrics. A stale compare-and-swap discards the candidate checkpoint. The previous complete record remains available for rollback. After a successful commit, orphaned older checkpoint files are pruned while active and previous generations are retained; a crash between file creation and pointer commit can leave an unreferenced file until the next successful update.
- restore(), rollback() and readout() verify the checkpoint hash/source binding before use.
- The existing V13 checkpoint stores encoder, EMA target and predictor weights but not Adam moments or the temporary inverse-dynamics optimizer head. A resumed partial_fit warm-starts from model weights and resets those optimizer states; this is explicitly measured as optimizer_moments_persisted=False.
- Learning is default-off per consumer and each update separately requires optimizer_permission=True. These are code-level gates; optimizer_permission is caller-supplied and is not an OS/identity security boundary. Age, installed GGUF models, native body weights and phone permissions are untouched.

## Tests added

v14/learning/test_world_jepa_consumer.py creates a real V13 SQLite Store directly and persists synthetic source blobs, EventEnvelope, ActionSelection, ActionIntent/CorollaryCopy and ActionOutcome records. It then exercises verified T8 admission, numeric WorldJEPA/EMA training, B1/B2 readout, holdout controls, a second replay update, restart/readback and rollback. A separate test verifies both learning gates remain closed by default.

The existing test_t8_store_authority_real_store.py on the dependency branch independently exercises the Runtime-created Store and duplicate-ActionOutcome negative control. This candidate does not replace that test.

## Verification status — do not overstate

- GitHub readback: both new source/test files were fetched from the candidate branch after push.
- Exact local repository execution: **BLOCKED**. The current worker environment could not resolve GitHub for a local checkout; no exact-source py_compile or pytest run was executed here.
- Candidate CI: a dedicated Python 3.13 workflow was added to compile the learning files and run PYTHONPATH=v13/code python -m pytest -q v14/learning. A workflow result must be fetched on the exact candidate HEAD before calling it PASS.
- Environment classification: SYNTHETIC_DATA / REAL_SQLITE_STORE_TEST_DESIGN; this is not live user data, not live Runtime chat, not native model inference, not native GGUF weight learning.
- Runtime consumer: NOT_WIRED. The existing runtime Python is under SourceHandoff freeze; do not edit runtime.py or claim the app calls this consumer.
- Redmi/Termux: REDMI_UNVERIFIED. No authenticated device receipt or native benchmark was available.

## Research consequence

New primary-source review is appended to v14/V14_RESEARCH_LEDGER.md:

- JEPA-TTT (arXiv:2610.00722, 2026-09-30) updates an action-conditioned latent dynamics predictor persistently and uses dense replay; the paper keeps the visual encoder/reward head fixed during test-time adaptation. V14 should compare predictor-only and joint encoder+EMA updates, rather than permanently freezing any organ.
- ER-JEPA (arXiv:2609.36952, 2026-09-29) adds episodic replay and compares content/uniform/hard selection. The current full bounded replay is only a baseline; later ablate these retrieval policies with retention and holdout utility.
- V-JEPA 2 is a useful action-conditioned world-model reference, but its released backbones range from 300M to 1B parameters (and V-JEPA 2.1 up to 2B); its video stack is not a Redmi/Termux drop-in. The public repository is primarily MIT-licensed with selected Apache-2.0 files; model/weight terms still require separate per-checkpoint verification. Nothing was downloaded or imported.

## Next executable step

1. Fetch exact workflow results for the final candidate HEAD and fix all failures before requesting review.
2. Have Boss/QA review the real Store test, the Store-state CAS/checkpoint crash ordering, and the WorldJEPA checkpoint compatibility.
3. If accepted, stage a hash-bound caller through an allowed extension point outside frozen runtime.py; keep it disabled until the local per-organ permission is explicitly enabled.
4. Add a real consumer-side B1/B2 integration only after a typed receiver contract exists; do not relabel these numeric readouts as native body injection.
5. Measure on an authenticated Redmi only after a separately authorized deployment. Until then, no Termux action is required.
