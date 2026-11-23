# V13 Automation11 C3 CLI post-generation source veto — preregistration (2026-10-28)

Owner: independent ChatGPT automation continuation. Review-only child of PR #891 head `0b821c8f50b9181b19bd2382e1ed10c7fa182066`. This is a new branch; do not modify the parent branch, production main, frozen runtime, model files or historical evidence.

## Observed gap (source read before edits)
At `v13/code/scripts/ask_verified_budget.py` blob `bd8d419820cb42cfaa2b3bd79f7322f77fbda9bf`, native `query()` verifies source before dispatch, generates, unloads and then publishes a string if it contains the source amount. A memory correction revoked or contradicted *during generation* is not rechecked before publication. The answer predicate also accepts extra unverified numbers or a different named project alongside the correct amount. These are observable source-consumer safety/utility defects, not proof that the normal Runtime is integrated.

## Locked plan before source edits
1. After native generation and proven unload, re-run the existing full `_preflight` on the same session/query, including current Age0, pause/idle, F1/F5 recall, active conflict veto and SourceRef. Publish output only if the current authorization (memory ID, SourceRef and rendered prompt SHA256) equals both pre-dispatch and original. On any change or failed check, suppress generated text, fail closed with explicit `SOURCE_CHANGED_AFTER_GENERATION` or a bounded refusal; never leak the raw model output. Preserve native-call and process-reap accounting.
2. Tighten `_answer_uses_euro_source`: require exact Euro amount, reject other numeric tokens and any explicitly named foreign project in the model answer. This is a conservative, narrow answer gate, not a semantic factual verifier.
3. Add deterministic software tests: source revocation and conflict inserted by fake runner during generation; output with extra amount, wrong project, correct bare amount; unchanged happy path. No native-model claims from mocked tests.
4. Run focused and full existing software tests in pinned-source GitHub Actions on this new review branch; retain raw logs, exact blobs, exit codes, privacy/diff, SHA256 manifest, and failed attempts. If no CI can run, mark unverified; do not infer PASS. Independent source review of edge cases after edit.

## Unchanged gates
Original Stage11, STEP2, B3 L1, Body-JEPA, LP3, Age promotion and Redmi gates remain negative. C3 CLI is opt-in and separate from frozen `Runtime._turn`. No claim of atomic revocation during inference; this package only prevents publishing a stale answer at a verified post-generation check. Concurrent revocation after the final check remains an unresolved TOCTOU risk. No model/seed/catalog changes. Do not touch Drive anyone-writable destination.

Next after verification: integrate live renderer authorization with the operator CLI only through an independently reviewed branch; measure actual native CLI two-turn utility and review outstanding gate failures.
