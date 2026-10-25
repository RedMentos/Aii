# Run282 — registered actual-weight Linux STEP1 retest (2026-10-25)

## Verified source and native prerequisites
- Independent Run282 owner: new native workflow and prereg; exact tested source checkout `059f0cf4b6bfdf881e9284e741da83662d8c93b7` (PR282), based on verified Run281. This report is persisted on the *downstream PR283* branch to avoid retriggering a heavy PR282 native job by adding a new commit to its own workflow-triggering PR.
- Public registered model manifest Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99` unchanged from PR269; bootstrap `dc23e192bcd01589475692666ebb6568c80d078b`; original acceptance harness `432b2e33eb53142b0d4246813b96fc791b0900f0`. Actual current `proofs.py` Git blob `a4bf9d9247dcbff727a2ccd12c979596658692cb`; executive integration `0d71d97868cc3a0785846f1073afcc2784550b2c`.
- Fresh GitHub Ubuntu 24.04 x86_64 Linux runner, kernel 6.17, 15 GiB RAM (not Redmi); Python 3.12.3; pinned isolated dependencies and public native model/runner downloads hash-verified. Native concurrency group shared with PR269, no overlapping heavy job.

## Exact native evidence
- GitHub Actions run `40192685057`: **SUCCESS**, all steps including privacy scan PASS. Actual model bootstrap exit `0`. Four original registered native stages `jef-modes`, `experience`, `learning`, `executive` each exit `0`, status `PASS`.
- JEF combined C2/C3, C3-only, C2-only, no-B manifest, **no-B AG0 slots**, integrity and restart all TRUE; `no_b_dependency_proven=true` for this bounded Linux probe. Executive first and second actual C3, task source context, corollary, restart, no weight update, body slot absence all TRUE. This directly repairs the three previous PR269 no-B false checks on a fresh exact-source run.
- Original `scripts/acceptance.py --stage-limit 4` returns exit `2` with `DIAGNOSTIC_INCOMPLETE` because **16 of 20 stages were not executed**. Workflow success means **only 4/4 bounded native stages PASS**, not full registered acceptance or all V13.
- Closed raw artifact `12598915530`, ZIP SHA256 `8d6da82d4f1a766cc63214bc574e30f10cb9640f553fbd5ab8b23e0ced8ef6b3`. Downloaded ZIP SHA256 independently verified. Includes exact head, host/model preflight, bootstrap logs, acceptance stage JSON/logs, exit codes, summary and privacy.
- Raw: https://github.com/RedMentos/Aii/actions/runs/40192685057/artifacts/12598915530
- Earlier PR269 full native 20 stages attempted, 12 PASS / 8 FAIL, `IMPLEMENTED_PATHS_PARTIAL` (artifact `12597232047`, SHA256 `eac321b4f8119f0ce10cbd65c050c87e56f11b94ec8d56322f450014f13054d0`) remains preserved; not overwritten by this limited rerun.

## Original negative gates and exact next step
- STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; V13 `INCOMPLETE`. No Redmi thermal/energy/RSS or phone-native proof; no AGI claim. No model/seed/age/learning right changed.
- Next: serialize any additional actual-weight job. Prioritize unresolved readouts Halt Pareto, control calibration support, retrieval human-source consumption, output adapter first-token/calibration and cancel process ownership; preserve their negative gates and do not change thresholds merely to obtain PASS. Also resolve PR277 offline diagnostic CI independently without overwriting its active owner's files.
