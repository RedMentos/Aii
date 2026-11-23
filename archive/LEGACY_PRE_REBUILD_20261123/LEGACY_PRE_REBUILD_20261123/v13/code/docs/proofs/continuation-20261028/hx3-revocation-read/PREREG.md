# HX3 ExperienceLibrary read-side approval revocation — prereg 2026-10-28 UTC

Owner: GPT-6 independent HX3 child review; only this branch and new review files. Base is PR #803 exact candidate `1a412fae18204dd4f33ffd1ef7e7998ad9c863a7`, itself dependent on PR #802 GREEN. **No production edit until parent PR #803 full CI GREEN.** No main/foreign owner modification.

Hypothesis: current `v13/code/v13/agi/experience.py` (blob `83ede4b83161bc78b5cc718c647d984e06d9f54a`) validates durable AG8 approval at `record()`, and rechecks evidence hashes at `lookup()`, but does not recheck later revocation of the human approval request when returning previously recorded lessons. Existing Run133 test covers revoked writers only. A stale `DATA_NOT_INSTRUCTION` lesson can still reach evaluators after request revocation, even across restart. This is a read-side authority/provenance integrity question; no live HX consumer is claimed.

RED-first actual Runtime/SQLite synthetic test: create two independently approved HX3 experiences with real local evidence files, confirm lookup, revoke only one request row, restart, assert revoked lesson absent and valid other lesson remains; assert no update/weight write. Capture exact old source blob, raw exit, privacy, hash and preserve RED. If observed RED, implement narrow source guard by rechecking `require_approved_origin` on lookup/verify, distinguish revocation from missing evidence, keep existing evidence-stale behavior, never execute lessons. Run focused and full software suite and independent review.

Keep canonical SSOT and all cohorts/pins untouched. No native/Redmi/weight learning, Age/approval/authority promotion, or auto-merge. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 incomplete. If parent CI fails, repair/record parent before source integration.

Next command: read PR803 Actions 40607477386 exact outcome; run preregistered RED test against current HX3 blob, then narrow fix + full Linux software evidence if parent green.
