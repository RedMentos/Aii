# Research & Perception — Run 23 handoff (2026-11-25)

## Product change

Draft PR #2511 was extended on branch `research-perception/v14-anchor-preserving-tokenwise-20261125-run22`.

- `v13/code/v13/native_receiver_utility.py`: adds a source-bound, ephemeral target-token log-probability receipt and paired task-utility evaluator. It binds task/session/source, target-token hash/count, receiver role/model/tokenizer, adapter, input, llama.cpp revision, binary and native execution metadata.
- Required per-task conditions: `NO_MESSAGE`, `EXACT_MESSAGE`, `LATENT_CANDIDATE`, `ZERO`, `SHUFFLE`, `REPEAT`, `OOD`, `ENTITY_SUBSTITUTION`.
- Default gate: >=20 task groups, >=2 held-out sessions, >=2 task families; candidate must beat each control on paired mean target log-probability, win rate and deterministic bootstrap interval.
- Result is only a teacher-forced target-logprob proxy. It explicitly reports no semantic-use proof, no generated-answer correctness, no persistence, no production route, zero training authority and zero native receiver authority. Synthetic fixtures always return `FIXTURE_ONLY`.
- Existing anchor-preserving tokenwise input builder remains additive and opt-in. No replacement of the current input path.

## Exact checkpoints and readback

- Evaluator module commit: `7031958809b6479231d87d74631d79de359ebf73`; blob readback `2bf3f17ab3695af51d7d00184ff945321dbaa3d8`.
- Focused tests commit: `be00992147f46165489684f82fba1891c86b986b`; blob readback `655425b2bd1df7da6fef35fbc954aaee3aa6b55d`.
- Research ledger commit: `b4e0eef2a6cd208491d176f162accb2a32cbabc6`; blob readback `718e2406e52997ab16d12ce508ee869d52a1522e`.
- Workplan append commit: `08e185676dd141fc8ef676743250407d7779e2cc`; blob readback `88b1ad9441f7dac085a699d82a04be2749d9a1ee`.
- User-next-action append commit: `fd6f744b30cc9320261ef31049351bf80f6fe1fb`; blob readback `38a5ea107063549e91f2a0bd4660f9038f1d2b07`.

## Tests

LOCAL_LINUX, CPython 3.13.5, pytest 9.0.2:
- `python -m py_compile native_receiver_utility.py test_native_receiver_utility.py` — PASS.
- `python -m pytest -q` — 8/8 PASS, isolated focused harness.
- The tests cover complete synthetic cohort, synthetic-not-native classification, tamper rejection, missing controls, paired target mismatch, OOD source mismatch, weak candidate failing exact-message/no-message comparisons, native decode/consumption failure, and no-message source/adapter refusal.
- Full Aii checkout pytest and native llama.cpp build: BLOCKED / NOT_RUN (no full repository checkout mounted; clone/DNS unavailable).
- Exact PR CI for the new head: NOT_YET_OBSERVED at handoff time. Prior #2511 adapter-contract CI on SHA `68ce8ca` was reported PASS (86 tests on Python 3.13 and 3.14); that is not evidence for the new commits.

## Integration boundary / risks

Core's current native receiver probe returns decode/input-effect metrics, not target-token log-probabilities or generated answers. The new evaluator therefore has no real native producer/consumer yet. It is a typed Perception contract for Core, not proof of receiver task utility. Its Python hash checks provide integrity and binding but do not cryptographically attest that a native binary generated a supplied receipt; Core must emit the receipt directly from the pinned native execution path.

Core PR #2510 is the next consumer owner:
1. Add a bounded teacher-forced target-token scoring operation (or bounded answer generation) to the native receiver, preserving exact target IDs/hash/count and per-token log-probs.
2. Emit the required native receipt from the same pinned model/binary execution, with decode status and explicit input-consumed evidence.
3. Call `evaluate_native_receiver_task_utility()` over the eight conditions on >=2 held-out sessions; keep training and B3 authority zero.
4. Run native negative controls, restart/rollback and resource tests before any Redmi experiment.

B3 remains OFF. No native GGUF inference or target-score measurement occurred in this run. No gradients, weight diffs, retention, Android ARM64, Termux or Redmi evidence. REDMI_UNVERIFIED; NOT_RELEASED.

## Research added (R-156–R-161)

- Co-observation is a distinct continual-learning constraint beyond forgetting/plasticity; current evidence reviewed at abstract plus secondary-summary level only.
- Mistake-gated learning's primary abstract reports 50–80% fewer updates and smaller replay buffers; full paper/appendices not reviewed.
- mzCache artifact is MIT, but its reproducible path requires root, Snapdragon 8 Elite/Gen 3, large storage and host resources; not compatible with the Redmi 732G target.
- PowerBench suggests phase/backend-specific NPU scheduling; no confirmed official repo/license was found.
- V-JEPA-LM's official code is Apache-2.0 and reports counterfactual supervision for temporal dynamics; its 1B–30B models and H100-scale training are not mobile candidates; model weight license unverified.
- ThinkJEPA's official code has a custom attribution license and CUDA/V-JEPA2/Qwen3-VL requirements; no code or weights reused.

## Deployment and next action

No private live phone receipt was obtained and no device command was sent. The last available private V13OBS snapshot is historical (2026-11-24): updater enabled, but AI runtime STOPPED_BY_USER at SHA `8d93236c753f0194224c19edc7411d8d7082b1d6`. Current installed SHA is unknown. No model, weight, permission or data change.

User action: **keine Aktion nötig**. No Termux command or model decision.

Next executable step: Core adds native target-score production and consumes this evaluator; then exact-head CI, independent review, native held-out utility and restart/rollback. Boss should port the verified checkpoint to the shared board after review.


## Cross-lane update — Core PR #2512

Core PR #2512 was opened on head `93fa02a75d68409a1cca6c2f2fcd338c1813a0bb`, stacked on #2510 and carrying the earlier anchor-preserving helper. It connects the fitted adapter to the native receiver under the separate `NATIVE_RECEIVER` approval and validates the current Runtime source/session. Direct source readback confirms the probe still reports only decode/input-effect metrics; it does not score target tokens or generate an answer. The #2512 snapshot does not yet include the new #2511 task-score evaluator. Core was notified to refresh/rebase #2511 and add a bounded target-score producer before task utility can be measured. Exact-head CI was queued; no PASS claimed.


### CI readback after Run 23 checkpoint (2026-11-25)

- Core PR #2512 exact head `93fa02a75d68409a1cca6c2f2fcd338c1813a0bb`: native input-embedding extractor PASS (Python contract 3.13/3.14, Linux pinned API, Android ARM64 cross-compile); staged-runtime PASS; integrated-regression PASS; offline deployment integrity PASS (Python 3.11/3.14). These are GitHub-hosted CI/cross-compile results, not Redmi runtime evidence.
- Perception PR #2511 exact head `9d864d66f6d66f1f5ead3284a85cf22814aa69d9`: staged-runtime PASS; offline deployment integrity PASS (Python 3.11/3.14); integrated-regression still IN_PROGRESS at last readback. The connector did not expose a new exact-head adapter-contract run for the appended task-score tests, so no CI PASS is claimed for those eight tests.
- #2512 still does not contain the new `native_receiver_utility.py` evaluator; Core has been asked to refresh/rebase the Perception parent and add the native target-score producer. Its current green consumer CI only validates the input-effect probe path.


### Run 23 evaluator hardening — balanced cohorts and Android evidence (2026-11-25)

- Perception evaluator branch head `f1e84db9d3140c53927ff3ef301a1d981d96e69d`: now requires one adapter revision across the entire cohort, >=5 tasks/session and >=4 tasks/family by default, in addition to >=20 tasks, >=2 sessions and >=2 families.
- Native `TERMUX_ANDROID`/ `REDMI` receipts must include a digest of the private device-execution receipt and a runtime-build identifier; raw private receipt bodies/IDs are not stored. This is an evidence-shape check, not cryptographic attestation.
- Three additional focused tests cover missing Redmi receipt metadata, per-session/family minima and adapter-revision drift. LOCAL_LINUX CPython 3.13.5 isolated evaluator harness: 10/10 PASS. Exact repository test target/new-head CI still NOT_YET_OBSERVED.
- Research ledger R-163 appended at commit `becf115df76f861d7332b8e735511b49319a26f6`. B3 remains OFF; no native target-score producer, no Redmi receipt and no release.
