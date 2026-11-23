

## QA & Android run 2 — 2026-11-23 16:15 UTC

### Exact-head CI result

- PR #2446 current head at this checkpoint: `762105e36b46b5af9b2bbec11916554bd18d1cb4`; code-bearing commit remains `17ed403a1e8c3d9896d28a8b1be57eaffd427100`.
- Exact staged/integrated run [45211647723](https://github.com/RedMentos/Aii/actions/runs/45211647723) is **FAIL**: 41 failed, 232 passed, 10 skipped, 2 errors. The integrated-regression path also fails at source composition. The failures are currently explained by stale immutable builder pins after `runtime.py` and `verification.py` changed; they are not evidence that the sanitizer behavior itself failed.
- Exact PR source readback: `v13/runtime.py` SHA-256 `f8a86c7f659890b4a26450a292e5057f454621883c9f4090298210aed9d12380`, Git blob `43198ed1bd9b835c59583a117ebb14f8ad9259c2`; `v13/verification.py` SHA-256 `25d0fb139cf74105e9680c1b4b91cac5b4de2bb4d2b6e0d244e61d707c36d283`, Git blob `9347264b35e43d256210fe92e769e10cecc9ab36`.
- Direct pin consumers identified: `integrated_online_world_candidate_20261110.py`, `record_only_online_guard_candidate_20261116.py`, `integrated_observer_fair_budget_candidate_20261116.py`, `integrated_arithmetic_candidate_20261116.py`, `integrated_audio_context_candidate_20261121.py`, `integrated_arithmetic_guard_candidate_20261121.py`, `termux_probe_recovery_candidate_20261112.py`, `postcommit_observer_candidate_20261116.py` and `record_only_controller_guard_20261116.py`. Their parent chain must be re-bound bottom-up through the recovery wrapper, stager and deployer; no integrity check may be relaxed. Exact failure details and source hashes were posted to PR #2446. Boss owns Core source-pin integration; this QA run did not edit those shared builders.
- Separate JEPA receipt/transaction workflows on the same head passed. The two migration tests returning PARTIAL are downstream of the stage failure and must be rerun after re-binding.

### Current authenticated Redmi boundary

- Private owner PIPELINE_STATUS #821 reports exact installed SHA `fb563d771fe2d493c4ec25abe94280981d24ef5c`, auto-update enabled, runtime/dashboard UP_TO_DATE, last error NONE.
- Private DIAGNOSTICS #822 reports `STOPPED_BY_USER`, model service STOPPED, autostart false and zero resident native model processes. No restart, CHAT_SEND, UPDATE_REQUEST or device mutation was performed.
- The last stored turn is diagnostic only: 6.295 s total, 2.046 s TTFT, 358 admitted prompt tokens, 7 generated tokens, FINAL. B1_DETAIL/B2_GIST remain TIME_BUDGET at 53.2/54.2 s; native probe SMOKE_PARTIAL. HEALTH #823 reports 1,118 MiB MemAvailable and 1,611 MiB disk free; LEARNING_STATUS #824 is UNAVAILABLE. This is not the required 20-turn acceptance matrix or proof of B1/B2 contribution.
- The redacted opted-in console receipt confirms the explicit probe path exposed internal hypothesis material. No raw private transcript was copied into this handoff or public repository.

### Cross-lane QA review

- PR #2448 received a review with two adversarial findings: the temporal voice-onset result is returned separately from the persisted PerceptPacket and can be forged while reusing a valid packet/lease; and the same audio event/packet can be replayed under a still-live lease to interrupt a later turn because no one-use event/packet guard exists. Perception owns the code path; required negative tests are in the PR review. This is a synthetic bridge, not an Android microphone provider.
- The #2446 public sanitizer also received review comments: `model_revisions` currently accepts arbitrary strings up to 128 chars and `missing_proofs` copies arbitrary strings up to 160 chars. Close both with a safe grammar/closed label set and sentinel tests.

### Evidence limits and next step

- LOCAL_LINUX full Aii suite: BLOCKED / NOT_RUN (no checkout mounted; GitHub DNS unavailable). GitHub Actions are CI evidence only.
- Phone code installation is verified at `fb563d77`; new QA fixes, normal chat quality, process-death/reboot, rollback, Android AudioRecord and full Canon acceptance remain REDMI_UNVERIFIED.
- Keep the phone stopped. Boss should re-bind the exact source-pin chain and rerun the full staged/integrated/migration matrix. Perception should address the two audio-bridge findings before provider integration. Do not send another update request or manual Termux command.


## Follow-up after probe-output review — 2026-11-23 16:00 UTC

The code-bearing QA checkpoint is now `17ed403a1e8c3d9896d28a8b1be57eaffd427100` (PR #2446). The follow-up was prompted by direct source inspection: the default native `:probe` path returned the full `verification.probe()` object, including C3 `actual_output`, B1/B2 `structured_offer.actual`, and C2 `actual_control`; both `Runtime._worker` and the one-shot `v13 probe` CLI serialized that object to the visible console.

### Additional implementation

- `v13/code/v13/verification.py`: new `public_probe_summary()` is an allowlist, not a blacklist. It exposes bounded status, token/timing/resource metrics, prompt-admission counts, verified/rejected quote counts and proof gaps. It does not copy model output, body offer content, C2 control payloads, arbitrary metric strings or unapproved config values. Non-native report shapes fail closed; non-finite/oversized numbers are ignored.
- `v13/code/v13/runtime.py`: interactive default `:probe` now emits only the public summary.
- `v13/code/v13/__main__.py`: one-shot default `v13 probe` emits the same summary.
- The original full probe report remains in the existing local `exports/native-probe.json` artifact. No upload or remote diagnostic logging was added.
- `v13/code/tests/test_prompts.py`: adversarial sentinel test covers C3 output, B1/B2 hypotheses, C2 payload, prompt preview, private config, and oversized numeric input; a negative test rejects a non-native report and checks fail-closed numeric filtering. The existing staged-context workflow already runs this test file.

### Current evidence

- Code-bearing head: `17ed403a1e8c3d9896d28a8b1be57eaffd427100`. PR #2446 remains DRAFT. The first-page workflow listing has not yet returned exact-head staged/integrated results for this final code commit; no green claim is made. An earlier ancestor run reported JEPA receipt-integrity PASS and other queued jobs, but it is not evidence for the final head.
- Full LOCAL_LINUX suite remains BLOCKED: no checkout is mounted and the container cannot resolve `github.com`. No repository pytest or compile result is claimed locally.
- Fresh authenticated device receipts #819/#820 confirm installed SHA `fb563d771fe2d493c4ec25abe94280981d24ef5c`, updater UP_TO_DATE, but AI `STOPPED_BY_USER`, model process STOPPED and autostart false. No CHAT_SEND, restart, shell, LOG_PAGE or device mutation was performed. Stored-turn timing and B1/B2 timeout metrics are unchanged and are not a new acceptance sample.
- The 20-turn live matrix remains blocked until the user explicitly re-enables the runtime. No model/weight/permission/Age change was made.

### Remaining privacy boundary

This change structurally redacts the default `:probe` console and CLI response. It does not prove that a normal generative C3 answer can never reveal internal text, and the explicitly invoked `:tap` diagnostic still returns raw body inspection data by design. The prompt-level C3 rule remains a mitigation, not a hard sandbox. A native adversarial test is still required after user-controlled restart.

### Shared integration coordination

I reverted temporary edits to `V14_WORK_BOARD.json` and `V14_USER_NEXT_ACTION.md` from this QA branch because Boss's current integration PR #2443 is already editing those shared files. The verified status and exact code head are recorded here and in the #2443 coordination comment; Boss should carry them into the shared board/next-action without overwriting other lanes.


---


## QA & Android — fresh Redmi and output-boundary checkpoint (2026-11-23 15:47 UTC)

**Installed phone state:** private owner-read receipt #819 confirms the Redmi is on exact release-development SHA `fb563d771fe2d493c4ec25abe94280981d24ef5c`, matching the current release branch. Auto-update is enabled; Runtime and Dashboard are `UP_TO_DATE`; `last_error=NONE`. This is installation metadata only.

**Runtime is explicitly stopped by the user:** DIAGNOSTICS #820 reports `STOPPED_BY_USER`, model process `STOPPED`, `autostart=false`, service/dashboard processes still running. No restart or `CHAT_SEND` was attempted. The latest stored turn is not a new acceptance test: 6.295 s total, 2.046 s TTFT, 358 admitted prompt tokens, 7 generated tokens. B1/B2 still report `TIME_BUDGET` at 53.2/54.2 s; C2 is OK, C3 probe 3.1 s, native probe `SMOKE_PARTIAL`; native residency is unavailable because no verified model supervisor exists. The 20-turn acceptance matrix remains BLOCKED by the user's Stop state. No user action is required now; do not send an update request or manual Termux command.

**Output privacy implementation:** PR [#2446](https://github.com/RedMentos/Aii/pull/2446), candidate head `8b6b9e716886b1dbf3fccd8ade82d3cacb16ad3a`, now goes beyond the prompt-only mitigation:
- `verification.public_probe_summary()` creates an allowlisted console report. Raw C3 `actual_output`, B1/B2 `structured_offer.actual`, and C2 `actual_control` are not returned to the console.
- The interactive `:probe` worker and one-shot `v13 probe` CLI use that summary. Full raw evidence remains in the existing local `exports/native-probe.json` artifact; it is not uploaded.
- `test_prompts.py` adds adversarial synthetic coverage with sentinel C3/B1/B2/C2 payloads, verifying that none appear in serialized console output while numeric metrics and verified-quote counts remain visible.
- Existing English/German C3 non-disclosure instruction and exact native offer-receipt prefixes are preserved.
- Exact PR CI at this head is not yet fully confirmed: JEPA receipt-integrity run 45210326339 SUCCESS; combined online-JEPA and JEPA transactional-update runs 45210326439 / 45210326276 QUEUED at last read; safe-additive validation was SKIPPED. The exact staged-context result has not yet been observed. Do not mark the PR green.
- Full LOCAL_LINUX repository tests BLOCKED: no checkout is mounted and `git clone` fails because this environment cannot resolve `github.com`. No Redmi output test was run.

**Important boundary:** the new redaction closes the explicit native `:probe` console path, not every possible generative leak. The prompt instruction remains probabilistic; normal C3 output and the explicit raw `:tap` diagnostic still require separate review/native adversarial testing. No raw private transcript was copied into this repository.

**Current release-branch CI:** exact `fb563d771fe2d493c4ec25abe94280981d24ef5c` has 20/21 observed PR-triggered workflows SUCCESS; the only failure is the experimental V14 M1 DATA workflow (Python 3.13 and 3.14, 36 tests: malformed fixture newlines prevent intended parsing; strict-NaN affected-origin interval also incorrect). QA fix PR [#2444](https://github.com/RedMentos/Aii/pull/2444), head `88e2115af9e1acf3bfba01ce3cd07a1ebf45a14b`, has exact M1 CI SUCCESS with 43 tests on Python 3.13 and 3.14 plus offline-bridge security PASS. It remains a separate open candidate, not merged or trained on real UCI data.

**Next:** finish exact-head CI for #2446; keep the phone stopped. When the user explicitly re-enables the AI runtime, perform the 20-turn source-bound matrix, then separately validate lifecycle/rollback. No model, weight, permission, Age or user-data changes.

---

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


## QA & Android run 3 — closed metadata grammar and probe exception boundary (2026-11-23 18:11 CET (run start))

### Code checkpoint
- QA branch: \`qa/v14-internal-hypothesis-output-20261123-run1\`.
- New commits:
  - \`fd6ebb3d76c099f8d755880441993ea542b09b72\`: field-specific allowlists in \`v13/code/v13/verification.py\`.
  - \`33f2dc5baea4b43678dace17bf1f5cbcacfb5995\`: non-string metadata values fail closed before allowlist lookup.
  - \`5e90f18d62a915fd0f80062c49735e04b5e891af\`: interactive probe worker emits only fixed \`PROBE_ERROR\` to console and telemetry on exceptions.
  - \`279e5c8120cfe8a14a37d593b2de2c92de4b3c51\`: one-shot \`v13 probe\` CLI emits a fixed safe error object.
  - \`632dc2a9ef729e1985f92db366415b8c14e3a1d7\`: adversarial regression tests.
- The public probe summary now uses closed sets for status/role/phase/error-kind, duration keys, prompt-admission revision/status/removal labels, fixed proof codes, and strict 64-hex model revision digests. It rejects non-string/unhashable values before set/dict lookup. No arbitrary model-revision or missing-proof text is copied.
- Interactive worker and CLI exception paths no longer persist or print \`str(exc)\` for probe failures. Raw model output/offer/control content remains only in the existing private local artifact; no new upload/logging path was added.

### Tests and evidence
- Added tests for secret sentinels in every previously permissive metadata field, the interactive worker exception path (console + telemetry), and one-shot CLI exceptions.
- Exact-head GitHub Actions on test commit \`632dc2a9ef729e1985f92db366415b8c14e3a1d7\`: staged/integrated run \`45226042195\`, JEPA receipt \`45226042201\`, transactional update \`45226042174\`, and combined online JEPA \`45226042185\` were **QUEUED** at the last poll; safe-additive candidate workflow \`45226042312\` was **SKIPPED by policy**. No CI PASS is claimed yet.
- Full LOCAL_LINUX repository suite remains BLOCKED / NOT_RUN (no mounted checkout and GitHub DNS unavailable in the earlier probe). No local test PASS is claimed.
- The PR remains DRAFT / NOT_RELEASED. The branch is still based on \`fb563d771fe2d493c4ec25abe94280981d24ef5c\`, 10 commits behind the current release-development head \`8d93236c753f0194224c19edc7411d8d7082b1d6\). Boss owns the safe rebase and downstream immutable source-builder pin composition; do not weaken pins.
- Redmi remains STOPPED_BY_USER per authenticated receipt #826. No restart, CHAT_SEND, UPDATE_REQUEST, LOG_PAGE, shell, model/weight/permission change, or device mutation was performed. No fresh receipt confirms any new QA candidate installed.

### Next gate
1. Wait for exact-head staged/integrated and JEPA checks; repair only reproduced failures.
2. After Boss's #2443 source-forget integration is accepted, rebase #2446 onto the resulting release head, rebind the exact downstream source-pin chain bottom-up, and rerun staged-runtime, integrated-regression, migration and privacy tests.
3. Keep the phone stopped. A post-install adversarial native probe test requires a later explicit user restart; it is not authorized by this code-only run.


## Exact staged CI readback — code/test checkpoint 2026-11-23

- Follow-on unhashable-value test commit: \`4d3ab4b8fd97f3f4d0372f41300f03aba967cec2\` (current PR head; handoff/body metadata updated separately).
- Exact staged/integrated run for preceding code/test commit \`632dc2a9ef729e1985f92db366415b8c14e3a1d7\`: run \`45226042195\` **FAIL** in both jobs.
  - \`integrated-regression\`: \`integrated_online_world_candidate_20261110.py\` rejects the changed \`v13/runtime.py\` at its immutable SHA check.
  - \`staged-runtime\`: the same runtime pin mismatch plus \`termux_probe_recovery_candidate_20261112.py\` rejecting the changed \`v13/verification.py\`.
  - Therefore the newly added privacy tests were not exercised through the composed staged consumer. No claim of test pass.
- Exact workflow evidence on \`632dc2a\`: \`45226042201\` JEPA receipt integrity PASS; \`45226042174\` JEPA transactional update PASS; \`45226042185\` combined online JEPA PASS; \`45226042312\` safe-additive candidate SKIPPED by policy.
- Latest exact source Git blob readback: \`verification.py\` \`c8c6ab663c10db00ac17b2e4aa18a500cf8f0a7e\`; \`runtime.py\` \`451c14238e35e1040308638c8197f5f2390cd186\`; \`__main__.py\` \`54444e0be17a2f773530056fd996c69f03547c33\`; \`test_prompts.py\` \`3bff42d6e0af5d574f24573b5f134bbde383c008\`. These are Git blob IDs, not source SHA-256 pins.
- Full LOCAL_LINUX tests: BLOCKED / NOT_RUN. The current PR branch is 10 commits behind release-dev \`8d93236c753f0194224c19edc7411d8d7082b1d6\`; Boss must coordinate rebase and bottom-up pin rebind after #2443. No source-integrity gate was weakened.
- Redmi remains STOPPED_BY_USER per receipt #826. No device action was attempted.


## Test-harness correction and pre-stage regression gate — 2026-11-23

- The first exact staged run exposed one defect in the new test harness itself: the \`Runtime.__new__\` worker fixture omitted \`_session_local\`, causing \`AttributeError\` in the worker cleanup. Added \`runtime._session_local = threading.local()\` in commit \`f9ee637b5a569e874020fba2afcbc06273470bbc\`. This is a test-fixture correction, not a production runtime change.
- Added an explicit pre-composition step to the existing \`.github/workflows/v13-integrated-context-stage-20261111.yml\` workflow so \`tests/test_prompts.py\` runs before source-stage pin checks. Workflow commit/current PR head: \`ee809a0e7839b2074185c0d70325ec03b847076a\`. This is not a new standalone workflow.
- Exact-head workflow runs at last poll: staged/integrated \`45227342231\`, JEPA receipt \`45227342248\`, JEPA transactional update \`45227342438\`, combined online JEPA \`45227342247\` all QUEUED. Safe-additive candidate tests \`45227342215\` remain SKIPPED by policy. No new test PASS is claimed.
- The previous staged run \`45226042195\` showed the new worker test failed only because of the missing fixture attribute; the remaining failures were the expected immutable \`runtime.py\` and \`verification.py\` source-pin mismatches. The new pre-composition step is intended to give independent direct evidence for the privacy tests while preserving those stage gates.
- Current PR head is \`ee809a0e7839b2074185c0d70325ec03b847076a\`; latest code/test commit is \`f9ee637b5a569e874020fba2afcbc06273470bbc\`. The branch remains based on \`fb563d771fe2d493c4ec25abe94280981d24ef5c\` and 10 commits behind release-dev \`8d93236c753f0194224c19edc7411d8d7082b1d6\`. Boss owns the coordinated rebase and exact source-pin chain.
