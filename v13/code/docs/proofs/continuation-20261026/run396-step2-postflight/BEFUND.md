# Run396 result — source-only verified, native input still pending (2026-10-26)

Run396 is an **independent read-only postflight auditor** of the already preregistered Run394 STEP2 pilot. It does not execute native inference. It validates the frozen manifest, original Run394 script/model catalog source hashes, all 42 required (fixture, variant, arm) pairs, recorded row SHA256, exact consumer-message binding, replay preregistration, model-artifact unchanged flags, typed finite utilities, zero wrong committed tool actions, and paired P−O/P−S differences. It distinguishes B2's **correctly quoted historical rule** in a revision episode from a wrong final action. No original scoring or registered cohort changed.

**Exact-head evidence:** `edc6918553ca4aa3ca116e988e1aa27340377375`, GitHub Actions run `40248203691`, job `121334184570`: 16/16 PASS (7 inherited Run394 + 9 Run396 adversarial synthetic), compileall PASS, privacy CLEAN. This is synthetic/source-only, not actual Run395 output.

**Raw integrity:** artifact `12619157230`, ZIP SHA256 `9812f9728f278306feff3b63a2fa1ea69a88b15a7004ab9088395518c1e3c48f`; ZIP CRC PASS, four internal SHA256 member checks PASS. Private Library copy `/V13_PRIVATE_CHECKPOINTS_20261024/Run396_STEP2_20261026/SOURCE_RAW.zip` materialized and compared byte-identical to downloaded artifact. No public model weights or private data included.

**Pending:** Run395 native pilot on PR390 is running separately; do not claim 42 real rows until its exact-head artifact is complete, SHA-verified and independently audited. Native output can be structurally RED without invalidating the source-only auditor. Run389 full-suite RED and STEP2 UTILITY_FAIL remain.

**Next command:** `PYTHONPATH=v13/code python3 v13/code/scripts/run396_step2_pilot_audit.py --input-dir <extracted Run395 run395-pilot> --output <private RUN396_NATIVE_POSTFLIGHT.json>`. Verify Run395 artifact ZIP CRC and all SHA before running. Preserve original failed attempts and original gates.
