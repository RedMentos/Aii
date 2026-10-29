# Run11 native cancel-worker identity — independent raw audit (2026-10-29)

**Scope / status:** independent review-only checkpoint on child branch of PR #1122 source commit `00c33007dbe4e4ddae1f8ec25840e5b6827ad894`. Not a merge, no production integration, no new model run, no source/cohort changes, no age/learning promotion.

## Exact source and raw evidence

- Original review PR: #1122; native workflow `.github/workflows/v13-native-cancel-identity-real-20261029.yml`; workflow Actions run **40916463645**, completed **success** at 2026-10-29T16:58:23Z.
- Exact workflow HEAD `00c33007dbe4e4ddae1f8ec25840e5b6827ad894`; test-script blob `f35d36ceab9acd473abebc8c59958aa6b784e42d` (`v13/code/tests/integration_real.py`). 24 registered source blobs (23 inherited unchanged; this test script is the intentional new cohort change). Historical original 20-stage 15 PASS / 5 FAIL is NOT replaced.
- GitHub original artifact ID **12916950536**, ZIP SHA256 `b48b630d402137931e46fc15d0a11bdbed1840a32026b449822f350dc4c2ec69`, 30,500 bytes. Independently downloaded ZIP and verified SHA256 and ZIP CRC; **19/19** internal `SHA256SUMS.txt` entries match.
- Private Library copy: `/V13-Checkpoints/2026-10-29/GPT6-Auto10-Run11-Native/RUN11_CANCEL_NATIVE_40916463645_SHA_b48b630d.zip`. Independently re-materialized: same SHA256 and `cmp` byte-exact. Never put native raw transcripts in public git.
- All eight recorded stage exits are `0`: BLOBS, INSTALL, BOOTSTRAP, MODEL_VERIFY, NATIVE, CHECK, PRIVACY, DIFF. GitHub job `cancel-native` success.
- Raw `CANCEL_RESTART.json`: `uses_real_weights=true`, Linux x86_64 Python 3.12.3, `android=false`, `all_passed=true`, 13/13 boolean `checks` true. Cancel status and runner status `CANCELLED`; canceled C3 native worker PID **2630**, `interruption_unload.process_reaped=true`, pool after cancel contains **[2604]** (unrelated resident role), `native_process_stopped=true`. Runner reports 12 generated tokens before cancel, sampled peak RSS **456,007,680 bytes**. The test helper verifies the canceled PID is absent from pool and OS; the unrelated resident PID is not mistaken for a failure.
- Real source/answer/memory/restart checks were exercised within this *new narrow Linux-native cohort*. No Redmi measurement or broad human utility inference.

## BUILD_STATE delta and negative gates

`RUN11_CANCEL_WORKER_IDENTITY_LINUX_NATIVE_PASS` **only for the new 2026-10-29 cohort**. Original historical cancel stage remains FAIL in its original immutable artifact; do not rewrite the 15/20 result. **No** STEP2, B3, Body-JEPA, jepa_weight, AG6, LP3, Redmi, or full V13 promotion. Age0 `RECORD_ONLY`, STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, LP3 `FAIL`, `jepa_weight=0`, AG6 unapproved, Redmi unmeasured, V13 incomplete.

## Open review questions and next command

- This new native proof is a **single-run** result on GitHub Linux x86_64, not an independently repeated native run or Redmi evidence. Check consistency of canceled PID resolution and OS liveness under PID reuse/rapid worker exit before widening the claim.
- Review PR #1122 against the immutable original Run11 20-stage acceptance harness. Do not merge the isolated child without cross-chain owner approval.
- Reproduce with a new preregistered cohort (never reuse the old cohort ID), only after checking no other heavy native owner: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_native_cancel_worker_identity_20261029` if the scoped test module is present; otherwise run the actual registered workflow's `tests/integration_real.py --installed-home <deep-hash-verified-home> --out <raw>` on a suitable Linux host. Recheck all source/model hashes, worker PID, exact raw JSON, CRC and internal SHA256SUMS.
- Separate independent package under review: AG6 rated-candidate answer-dependency revocation in PR #1120; do not alter its owned branch.

**Owner:** this independent audit child branch, documentation only. **Next review owner:** PR #1122 original owner. **Source of truth:** Canon `v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`, `v13/AGENTS.md`, current branch-scoped BUILD_STATE and raw evidence. Platform remaining budget: UNKNOWN.
