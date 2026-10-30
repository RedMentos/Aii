# JEF WP-U1 self-label source admission — verified RED → GREEN 2026-10-30

## Exact source and observed failure
- Parent `81ca76bc6637a5f543f364cf7464f3a241ce0bf3` (full unfiltered suite branch running separately), prereg `541c656755ef7c3e1cec58378bae3aadc3740838`, Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.
- Original test-only head `db2be76fccdc3ce3a7af023b4491e21edf1727c8`, Actions **40988049715 RED**, **19 tests: 3 expected failures, 16 PASS**. A tombstoned self-outcome source, a substituted live source containing the wrong value, and a different event's ExecutiveDecision packet ID were all wrongly admitted by `jefoutcome.training_rows`.
- Original RED raw ZIP **12947364551**, SHA256 `e7aac9659ef6b4bbb280c20e3b7eae0509ff3c5b9e6e334297a9908b53e30927`, CRC clean, **18/18** inner hashes.

## Narrow repair and positive replay
- Candidate `5c4ae0f53528947ccee71760500dce4470bec7ca`, `jefoutcome.py` Git blob `b68661541990cf94b538b9aebf0c7dff35e0ac1a`. Read-only `training_rows` now checks the label's source is live, exact `OUTCOME_SELF_LABEL` kind and bytes/value match, then verifies ExecutiveDecision event/packet/component/context revision/hash/baseline before producing a training row.
- Actions **40988140394 GREEN**, **19/19 PASS**, **8/8** stages exit0; privacy CLEAN. Existing human RECORD precedence, >512 window, SkillLive correction, JEF outcome idempotence and original live-label behavior still pass.
- GREEN raw ZIP **12948335185**, SHA256 `6f08b4621119300158ad38e15f852dda060d7264aaeb5d10689214360a5b0670`, CRC clean, **18/18** inner hashes.
- Original RED and GREEN byte-identical private backups at `/V13-Checkpoints/2026-10-30/Run11-JEF-SelfLabelSource/`; re-materialized and SHA256 reverified.

## Limits, owner and continuation
The fix prevents revoked or corrupt self-outcome labels from entering the candidate data array, avoiding an avoidable later optimizer abort. It does not authorize training, alter learning permissions, create a new label, delete retained audit state or prove utility. Age0 RECORD_ONLY and every STEP2/B3/Body-JEPA/jepa_weight gate unchanged; software/SQLite only, no native/Redmi.

Owner: V13 hourly automation, review-only child of the current combined branch. Exact next: full unfiltered suite on the combined head with CPU torch/Transformers/PEFT; retain historical Run34/Run37 source-pin RED, then independent review and merge into the review chain. No force-push, no production/main integration without review.
