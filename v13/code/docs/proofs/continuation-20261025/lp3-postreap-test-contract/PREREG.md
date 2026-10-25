# LP3 Run18 post-reap orphan test contract — preregistration (2026-10-25)

Base: verified Age noise PR253 head `f5d2eaed19c1ff79cd4baec10912c03bc7a2eff0`. Exclusive file ownership: `v13/code/tests/test_lp3_serial_review_run18.py` **test only**, new isolated CI and this proof folder. No launcher, cgroup, production Runtime, registered native cohort, DS3, Age, WorldModel or active native owner changes.

Known Run221 full-suite RED: https://github.com/RedMentos/Aii/actions/runs/40180545459, 2646 tests, 2 FAIL, 36 historical candidate ERROR. The second FAIL is `OrphanGroupReview.test_successful_leader_with_live_descendant_is_not_success`: it demands that the wrapper kill a surviving grandchild after the direct process leader is reaped. This conflicts with independently reviewed Run21 `LP3_RUN21_POSTREAP_REVIEW.patch`, which **intentionally forbids signalling a reaped leader's numeric PGID** because PID/PGID reuse can target an unrelated process. Safe cleanup after reaping requires an owned delegated cgroup (or equivalent atomic ownership proof), not `killpg` on an unowned number.

Revised adversarial contract:
- In synthetic cgroup-only test, a leader exits successfully while its own descendant stays alive; the wrapper MUST refuse success and receipt, report `owned_group_residue_detected=True`, `owned_group_absent=False`, poison the local lock and block another attempt.
- The test must NOT demand unsafe post-reap numeric PGID signalling. The test itself, as creator of the fixture, may terminate its known spawned descendant through a stable pidfd handle; never signal an unverified process group.
- Explicit mock check must show `_cleanup_owned_group` does not call `os.killpg` when group is present.
- Preserve Run21 source reconstruction and SHA pins, all original gates and the original failure evidence; this is software/synthetic test semantics, NOT proof that production can safely clean descendants without delegated cgroup.
- No native model, Redmi, actual cgroup write or LP3 four-seed launch.

Expected: existing Run18 assertion RED, corrected test GREEN with unchanged Run21 launcher. Full suite remains RED until 36 source-bound historical candidate errors independently resolved and current full suite rerun.
