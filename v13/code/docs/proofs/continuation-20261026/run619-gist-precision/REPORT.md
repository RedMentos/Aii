# Run619 — B2 Gist SQLite full-precision cosine ranking correction

2026-10-26. **Review-only child** of Run618 PR613 at exact observed head `23d366d137360b5ce9ca09375fe672661a403935`. Separate owner/files: `v13/code/v13/gist_similarity.py`, `v13/code/tests/test_gist_similarity_run616.py`, new Run619 CI/proof only. No Run618 prereg, cohort, native capture script, pinned models, or runner changed. No main merge.

## Reproduced defect and patch

Before correction, `gist_similarity.lookup()` sorted candidate matches by six-decimal *display* cosine, not original full-precision cosine. Distinct candidate similarities rounded to the same displayed value were treated as ties; the latest candidate could incorrectly beat the closer older candidate. This contradicts the original native full-precision `rank_raw` used by Run617/Run618. A local pure-numerical counterexample showed the two rank policies disagree; **this is not a claimed native model run**.

Now candidates retain the unrounded cosine for internal sorting and expose only the original six-decimal display value. Python stable sort still makes genuinely equal full-precision scores prefer the newest candidate. The public output schema, max 64 scan, top five cap, session/model/generation/source validation, and all read/learning/receiver authorities are unchanged.

New SQLite/Runtime regression `test_near_equal_display_cosines_rank_by_full_precision` inserts older vector [1, .0014], newer [1, .0015], query [1, 0]; both candidate scores display equally rounded, but the older is mathematically closer and must rank first. Original exact-tie, revocation, restart, source isolation, and no-leak tests remain. This test is *designed* to fail against the original implementation, but a pre-fix SQLite execution has not been observed; do not claim observed RED.

## Verification and evidence level

- Source remote readback: `gist_similarity.py` blob `b6aa89a8d954dde524217171cd28c4bdf09a0cf0`; tests blob `24cd16a52dbce9329339f34c8037a1bf3e845c4a`; workflow blob `a50f094965cc701785f10a3247a5d1d13edf6119`.
- Real SQLite CI workflow `.github/workflows/run619-gist-precision.yml`: runs prior Gist readout + Run616 SQLite tests + Run618 synthetic fixture, with source hashes, raw output/exit, SHA256 manifest, privacy scan. **PENDING**, do not claim PASS until exact Actions run, exits and artifact are verified.
- Local pure-numerical review counterexample only; no new model inference, native body training, actual Redmi measurement or semantic utility.
- If CI fails: retain original raw logs, classify and fix on this child branch; never alter frozen Run618 protocol to hide failure.

## Gates / continuation

STEP2=UTILITY_FAIL; B3_L1=FAIL; Body_JEPA=UNAVAILABLE; jepa_weight=0; Redmi=UNMEASURED; V13=INCOMPLETE. `canonical_architecture_complete=false`, `user_full_scope_complete=false`. No new Age, tools, approval or learned-body authority.

Next command after CI appears: inspect exact Run619 commit workflow runs, download/verify raw artifact + per-stage exit statuses, independently re-evaluate near-tie regression and original exact-tie behavior, then checkpoint result; continue next distinct functional package. Concurrent Run618 native owner remains independent and serialized; do not overwrite its branch.
