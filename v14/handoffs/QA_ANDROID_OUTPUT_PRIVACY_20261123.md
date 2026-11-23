# QA & Android — internal organ output boundary

Date: 2026-11-23  
Owner: QA & Android  
Base release-development SHA: `fb563d771fe2d493c4ec25abe94280981d24ef5c`  
Candidate branch: `qa/v14-internal-hypothesis-output-20261123-run1`

## Defect and scope

A sanitized private diagnostic summary reported internal B1/B2/C3 hypothesis material appearing in the user-facing console. The raw excerpt and all conversation text remain private and are not copied here.

The current C3 system prompt called body offers "fallible hypotheses" but did not explicitly say that the offer text and organ labels are private. The runtime deliberately passes selected source-bound offers into C3 context, so removing the offers would hide the symptom by breaking the intended B1/B2-to-C3 path. This change preserves that data path and makes its presentation boundary explicit.

## Code change

- `v13/code/v13/prompts.py`: both English and German system prompts now say internal organ offers are private inputs, may be used for synthesis, and must not be quoted, listed, or exposed with their role labels.
- The hypotheses context prefix is explicitly marked private and not for user output in both languages.
- `v13/code/tests/test_prompts.py`: added a regression checking the private-input and non-disclosure contract for both supported languages.

No B1/B2 offer, source pointer, C3 context, model, weight, permission, Age, learning mode, or device setting was changed.

## Verification

- Prompt code commit: `b515eb5fbb690f03e8e2be3865eeb1a48cb64e72`.
- Regression test commit: `48494e583f3ac4af04d1938adec6a3414e0e2266`.
- Exact PR CI: pending at handoff authoring; only an exact-head result can close the CI check.
- LOCAL_LINUX repository test: BLOCKED / NOT_RUN. Python 3.13.5 exists, but no repository checkout is mounted and `git clone` failed because this worker cannot resolve `github.com`.
- Redmi native output test: NOT_RUN / REDMI_UNVERIFIED. No chat was sent and the runtime was not restarted. Physical C3 behavior is not inferred from the prompt unit test.

## Proof boundary and risk

This is a prompt-level privacy mitigation, not a hard information-flow sandbox. A generative model can still violate an instruction. The exact test proves that both prompt variants carry the non-disclosure instruction; it does not prove that native C3 never leaks. A later structural channel separation or a measured adversarial C3 output test is still needed before claiming the privacy issue fully closed.

## Next action

Review exact-head Python/CI results. Keep the B1/B2-to-C3 input path intact. When the user-controlled Redmi runtime is explicitly re-enabled, run a bounded output-only regression that checks greetings, ordinary answers, and internal-offer-bearing turns for leaked organ labels or hypothesis text; do not restart or send a turn before that state changes.
