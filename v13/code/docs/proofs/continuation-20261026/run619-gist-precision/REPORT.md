# Run619 — B2 Gist SQLite full-precision cosine ranking correction

2026-10-26. **Review-only child** of Run618 PR613 at exact observed head `23d366d137360b5ce9ca09375fe672661a403935`. Separate owner/files: `v13/code/v13/gist_similarity.py`, `v13/code/tests/test_gist_similarity_run616.py`, new Run619 CI/proof only. No Run618 prereg, cohort, native capture script, pinned models, or runner changed. No main merge.

## Reproduced defect and patch

Before correction, `gist_similarity.lookup()` sorted candidate matches by six-decimal *display* cosine, not original full-precision cosine. Distinct candidate similarities rounded to the same displayed value were treated as ties; the latest candidate could incorrectly beat the closer older candidate. This contradicts the original native full-precision `rank_raw` used by Run617/Run618. A local pure-numerical counterexample showed the two rank policies disagree; **this is not a claimed native model run**.

Now candidates retain the unrounded cosine for internal sorting and expose only the original six-decimal display value. Python stable sort still makes genuinely equal full-precision scores prefer the newest candidate. The public output schema, max 64 scan, top five cap, session/model/generation/source validation, and all read/learning/receiver authorities are unchanged.

New SQLite/Runtime regression `test_near_equal_display_cosines_rank_by_full_precision` inserts older vector [1, .0014], newer [1, .0015], query [1, 0]; both candidate scores display equally rounded, but the older is mathematically closer and must rank first. Original exact-tie, revocation, restart, source isolation, and no-leak tests remain. The initial registration had no pre-fix SQLite run; an independent local Run601-source/Run616-overlay **pre-fix SQLite execution was subsequently observed RED**, as detailed below.

## Executed independent local Linux SQLite regression (closed)

After the initial remote checkpoint, restored the **original Run601 phone source ZIP** from private Library (original head `fdcbefc129b28b085fcfa84a4bc3ee44cce74b62`), overlaid the exact Git blobs from Run616/Run618 and the Run619 patch/test, then executed actual SQLite/Runtime `unittest` on Linux with NumPy 2.3.5 and prompt-toolkit 3.0.52. The overlaid `gist_similarity.py` and test Git blobs exactly match the remote Run619 source/test; original Run616 `gist.py` and Run618 script/cohort hashes also match. The underlying Run601 `operator.py` is older (`c5eb02a4cf3c4e8a63bd4aeaf4491a98778199c8`) than the current branch (`60892780b4beb6ad62efcdd3215e5b646b16efab`), so **this is not a full exact-current-head integration run**.

- Baseline original Run616 `gist_similarity.py` + new regression: **observed 1 FAIL**, the near-equal score case reverses the two candidates (other tests pass). Raw log SHA256 `5e48e64d7ca66ef74bb3aed1b06692097f75a1106648f624231072fda1f20656`.
- Run619 patched `gist_similarity.py` + original Gist tests: **21/21 PASS**. Raw log SHA256 `b1b7df00cbdb4a107086b373036ab61fcb73d79fab5d9b01bc8f9df89348bcc4`.
- Run618 unchanged synthetic/SQLite replay fixtures: **5/5 PASS**. Raw log SHA256 `4427468cc8438927ca6443e1cfa87165119cc87dd0f12a2bf8d6be69939476d0`.
- Combined `tests.test_gist_similarity_run616 tests.test_gist_readout tests.test_run618_prospective_b2_native`: **26/26 PASS**, exit 0. Raw log SHA256 `d19a913b3944c7b0502324dd4f50baa16e7460cdc2672efeb13d7cf6fb39cd57`.
- Independent fake-store source-identical harness: baseline near-tie FAIL; patched **6/6 PASS** (not counted as SQLite).
- Private Library `/V13-Checkpoints/2026-10-26/Run619/run619-local-closed.zip` SHA256 `68c38fbd5785810096fd417c47bd96a394313b02bd56e64e54ea6a4cd0d7d318`; SHA-closed raw logs, original failure, tests, source, branch checkpoint. **Round-trip byte-for-byte readback verified**. No user/private source text in public Git.

## Independent retrospective original-native audit

Original SHA-closed Run614 B2 states (`RUN614_STATES.npz` SHA256 `cb535df87749c0cf5d698d26268e6b03f3d6f57690b95434aebc6c875a3ea189`) were checked separately without new inference. For 20 original heldout queries, the old six-decimal rounded ranking and full-precision ranking had **0 top-five order differences and 0 rounded-score collision pairs**. This **does not** imply the bug affected the observed Run614 cohort; its demonstrated effect is the independent adversarial near-tie SQLite regression. Audit JSON SHA256 `a2954884d700e0c7a5d02fa962fab09cd3ef00e457e8d3b3ecacff919ca1eef1`, script SHA256 `155b957cd810cc333a9aa6ba02355e3e870770bcdb2e339cf20f09405626134a`; script rerun reproduced identical JSON bytes. Both stored privately in Library Run619.

## Verification and evidence level

- Source remote readback: `gist_similarity.py` blob `b6aa89a8d954dde524217171cd28c4bdf09a0cf0`; tests blob `24cd16a52dbce9329339f34c8037a1bf3e845c4a`; workflow blob `a50f094965cc701785f10a3247a5d1d13edf6119`.
- Real SQLite CI workflow `.github/workflows/run619-gist-precision.yml`: runs prior Gist readout + Run616 SQLite tests + Run618 synthetic fixture, with source hashes, raw output/exit, SHA256 manifest, privacy scan. **GitHub Actions run status still UNVERIFIED** (connector exposes no push-triggered run listing); local executed Linux SQLite results above are separate and do not establish Actions success.
- Local pure-numerical review counterexample only; no new model inference, native body training, actual Redmi measurement or semantic utility.
- If CI fails: retain original raw logs, classify and fix on this child branch; never alter frozen Run618 protocol to hide failure.

## Gates / continuation

STEP2=UTILITY_FAIL; B3_L1=FAIL; Body_JEPA=UNAVAILABLE; jepa_weight=0; Redmi=UNMEASURED; V13=INCOMPLETE. `canonical_architecture_complete=false`, `user_full_scope_complete=false`. No new Age, tools, approval or learned-body authority.

Next command after CI appears: inspect exact Run619 commit workflow runs, download/verify raw artifact + per-stage exit statuses, independently re-evaluate near-tie regression and original exact-tie behavior, then checkpoint result; continue next distinct functional package. Concurrent Run618 native owner remains independent and serialized; do not overwrite its branch.
