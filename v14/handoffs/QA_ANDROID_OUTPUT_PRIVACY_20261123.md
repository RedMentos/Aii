# QA & Android — internal organ output boundary

Date: 2026-11-23  
Owner: QA & Android  
Release-development base at PR creation: `fb563d771fe2d493c4ec25abe94280981d24ef5c`  
Candidate branch: `qa/v14-internal-hypothesis-output-20261123-run1`  
PR: [#2446](https://github.com/RedMentos/Aii/pull/2446)

## Defect and scope

A sanitized private diagnostic summary reported internal B1/B2/C3 hypothesis material appearing in the user-facing console. The raw excerpt and all conversation text remain private and are not copied here.

The current C3 system prompt called body offers fallible hypotheses but did not explicitly tell C3 not to reveal internal offers or organ roles. C3 receives selected source-bound body offers as context. Removing those offers would break the intended B1/B2-to-C3 path, so this change preserves the input path and adds a compact presentation-boundary instruction.

## Final code and tests

- `v13/code/v13/prompts.py`, final code commit `19b4526257c10f1d982a4b3fc3e0b3862b22e172`: both English and German system prompts now instruct C3 not to reveal internal offers or roles.
- The typed hypotheses prefixes remain byte-for-byte unchanged: `Internal hypotheses: ` and `Interne Hypothesen: `. The native offer receipt contract depends on the exact English prefix; changing it broke an existing receipt test, so it was restored.
- `v13/code/tests/test_prompts.py`, final test commit `84b7cb998e07146bc0240b71b8da98fd85a8d8ef`: checks both language instructions and exact receipt prefixes.
- `.github/workflows/v13-integrated-context-stage-20261111.yml`, workflow commit `c806fc116f1475626cb3e89dc2a34139bcb83822`: the existing staged-runtime job now runs both `tests/test_prompts.py` and `tests/test_native_offer_prompt_receipt_20261118.py`. No new workflow was created.
- This does not remove source-bound B1/B2 offers, change C3 routing, alter a model/weight, enable a permission, or change Age/learning mode.

## Regression history and exact-head verification

- The first, longer prompt instruction caused `test_prompt_source_integrity_20261116.py::test_real_append_only_old_context_question_answer_removed_together` to exceed its deliberately tight 560-token fixture. That exact-head run failed; the instruction was shortened rather than weakening the context test.
- A later run caught the exact-prefix dependency in `test_native_offer_prompt_receipt_20261118.py`; the prefix was restored and the regression was added to the existing staged CI command.
- Another intermediate run caught a stale assertion in the new prompt test. The final test now checks the original exact prefixes and the compact privacy instruction.
- The final code/test/workflow combination is at candidate head `84b7cb998e07146bc0240b71b8da98fd85a8d8ef`. Its staged/integrated exact-head run was queued/in progress at this handoff refresh; no final PASS is claimed until the newest handoff commit's own run completes.
- LOCAL_LINUX repository tests: BLOCKED / NOT_RUN. Python 3.13.5 exists, but no repository checkout is mounted and `git clone` failed because this worker cannot resolve `github.com`.
- Redmi native output test: NOT_RUN / REDMI_UNVERIFIED. No chat was sent and the runtime was not restarted. Physical C3 behavior is not inferred from prompt unit tests or Linux CI.

## Proof boundary and risk

This is a prompt-level mitigation, not a hard information-flow sandbox. A generative model can still violate an instruction. The exact tests prove that both language prompts carry the non-disclosure instruction and that the typed offer receipt header remains intact; they do not prove that native C3 never leaks. Structural channel separation and an adversarial native output test remain open.

## Next action

Review the exact-head staged-runtime, integrated-regression, and private-bridge results after the handoff sync. Keep the B1/B2-to-C3 input path intact. When the user-controlled Redmi runtime is explicitly re-enabled, run a bounded output-only regression for ordinary turns and turns containing internal offers; do not restart or send a turn before that state changes.

No device action, chat send, restart, model/weight change, permission change, or user-data mutation was performed.
