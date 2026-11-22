# Run12D independent original native raw audit — software-only GREEN (2026-10-30)

Review-only PR #1261, child of Run12C PR #1260. Parent exact `61d4b05d080296962e72e4501c933993545d4ce1`. New read-only `scripts/bodyjepa_350m_contrastive_raw_audit_run12d.py` blob `904e6a2b21c1bc4f9e1e61178adcdc78bd84fc08`, test blob `8dc82984329bac7db14176bd20fca21e758e7518`. No changes to frozen Run12B trainer, Run12C native runner/trigger, original Run11P, model, Canon or runtime.

## Verified evidence

GitHub Actions **41047068994 SUCCESS** at exact HEAD `94dc1c15be7b4b6319399ff3c1bdc581a87ce25f`; **15/15** software tests (8 new synthetic ZIP tamper/partial/negative cases + 7 Run12C protocol), stages PINS/TEST/COMPILE/PRIVACY/DIFF **5/5 zero**, privacy CLEAN. Original artifact `12972852317`, ZIP SHA256 `71e4d7e5ea3591857d0e3134dd86d7e97b3961760cd1b863ed5f52b668619d56`, 3,590 bytes, CRC clean, 12/12 inner SHA256. Private Library backup `/V13-Checkpoints/2026-10-30/Run12D-BJEPA-Raw-Audit/SOFTWARE_GREEN_41047068994_sha71E4D7E5.zip` re-materialized and byte-exact `cmp=0`.

The auditor accepts **only** an operator-supplied original ZIP SHA256 and exact launch HEAD `35c163f19f3ccdc1e8ebed1df5821c679d96a13a`, checks ZIP paths/duplicates/CRC/inner manifest, stage exits and source pins, validates 12 arms/3 seeds and NLL rows/means/metrics, and independently recomputes prereg thresholds. A partial or RED stage returns `ORIGINAL_RED_OR_PARTIAL_PRESERVED`, never a utility PASS. The synthetic test ZIP is not native evidence. Original native Run12C Actions **41046804934** launched and was still in progress at this checkpoint; actual native result UNKNOWN.

## Open and next

- **Known audit coverage gap:** current auditor checks row count, uniqueness and means but does not yet compare each question/answer byte-for-byte with the preregistered fixture. Close with a disjoint synthetic tamper counterexample and rerun CI before using the auditor on real native raw.
- After native Actions 41046804934 terminal: download original ZIP, record exact SHA, CRC and inner hashes; run auditor with `python3 v13/code/scripts/bodyjepa_350m_contrastive_raw_audit_run12d.py --zip ORIGINAL.zip --expected-zip-sha256 <verified_sha> --expected-head 35c163f19f3ccdc1e8ebed1df5821c679d96a13a --out NEW_AUDIT.json`. Back up original and audit privately, re-materialize byte-exact, preserve RED.
- All gates unchanged: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, runtime jepa_weight0, Redmi UNMEASURED, V13 incomplete. No auto-merge.

## Fixture-identity audit gap closed — second verified source-only proof

The previously recorded gap was corrected without changing frozen Run12C source or any original cohort: auditor blob `40d94e455091d411cf5e1619fbd61f2bbd2bc6b4`, tests blob `e0fbe189e3fc97460ebf8c668e1df8427d2302bd`. Auditor independently reconstructs and hashes preregistered seed239 fixture, then checks **every exact question and answer byte** in train/paraphrase/near-miss/retention, in both after-fit and disabled-adapter baseline rows, for all 12 arms. It also binds evidence class and baseline measurement method. New tests reject fabricated question/answer and upgraded Redmi/pre-fit evidence labels.

Final source-only Actions **41047316148 SUCCESS** at `5950ba696589d8c3b731eed5cda727e459786815`, **17/17 PASS**, 5/5 stage exits0, privacy CLEAN. Original artifact `12972513499`, ZIP SHA256 `d9f7107dfef575518a7f1c53803444adc86e43fd1eea6f18db718fe9f33f054f`, CRC clean, 12/12 inner SHA256. Private byte-exact re-materialized backup: `/V13-Checkpoints/2026-10-30/Run12D-BJEPA-Raw-Audit/FIXTURE_BOUND_GREEN_41047316148_shaD9F7107D.zip`, `cmp=0`. Earlier Actions 41047068994 GREEN and its original raw are retained. This is still synthetic software verification, not a native NLL outcome or promotion.
