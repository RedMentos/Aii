# BUILD_STATE — Run108 runner activation staged review checkpoint (2026-10-31)

Owner GPT-6. Review-only child of Run107 #1476, exact parent `5d816feda3469a5149ab73e59116ef785a272848`. Original Canon `v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged; original pinned b10964/model/source/seed hashes untouched. Run105 full-suite RED preserved, no merge.

Prereg `23b205be5b14d152371fc49bc31cd6ef942814f5` BEFORE implementation. New `v13/runner_activation.py` at `9fabf1579f07ec97e53ad149640a98b12f35d1c3`, integrated `v13/bootstrap.py` at `5126efe31e4d544e684419d4b1bd1f127b18f431`, model-free tests at `fbd9e00e5a294f20a39734a52f67c544b9174550`, workflow at `ccf9ac2ddddb17a5bed2b0a8a438cd8632b9a47b`. Independent local helper-only test with temporary shell executables: 8/8 PASS; **not** a test of integrated bootstrap on GitHub/Redmi.

Fix scope: unique native candidate staging so retry never destroys active target; version and SHA before symlink activation; old symlink/legacy regular runner preserved on version failure and manifest promotion failure; no external model/runner changes. Existing runtime source frozen outside bootstrap. Power-loss two-file atomicity NOT proven. Older successful staging directories retained for rollback; future storage reclamation must be separately specified.

GitHub Actions `41212957856` exact HEAD `ccf9ac2ddddb17a5bed2b0a8a438cd8632b9a47b` observed IN_PROGRESS at initial checkpoint. It must close original raw 10-case integrated test, original 11 safe_tar, Run104 21-case, compile, current phone ZIP/manifest, privacy and diff; **do not claim GREEN before terminal ZIP verification**.

Next exact commands: GET `/repos/RedMentos/Aii/actions/runs/41212957856`; on terminal GET `/actions/runs/41212957856/artifacts`, independently download original ZIP, verify outer SHA/CRC and every inner SHA256SUMS, test exits, exact tested HEAD and no native/Redmi claims. Preserve RED if present. Then review helper failure rollback and candidate staging, update scoped BUILD_STATE and create draft PR. Do not run competing native jobs.

Negative gates: Age0 RECORD_ONLY; STEP2_EXIT EVIDENCE_NOT_PASSING, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, jepa_weight=0, Redmi UNMEASURED, whole V13 INCOMPLETE. Remaining platform budget UNKNOWN.
