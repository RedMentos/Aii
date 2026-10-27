# BP1 QAD independent software review — closed RED/GREEN checkpoint (2026-10-27)

## Ownership and source
Reviewer: GPT-6 automation11, **review-only**, parent PR #682 at exact `a71121d30fa1b83fa4c9b86b8f5fa3bc5fe710aa`. Child branch `codex/automation11-bp1-qad-review-20261027`, verified source head `ce1833f99d142e44d4abe0076247f89f7fb892af`. This does not modify the parent's branch or production `main`. Scoped paths: `scripts/bp1_qad_native_smoke.py`, its software tests, isolated software-only workflow and this proof folder.

## Concrete changes
1. Corrected the Python nested-class test-scoping bug in `test_batch_encoding_is_normalized_to_tensor` (`class Torch: Tensor = Tensor` raised NameError on Ubuntu). Parent Actions `40473645747` software RED (10 tests, 1 ERROR, native SKIPPED) remains unchanged. Parent earlier native Actions `40473240028` was also RED from Transformers BatchEncoding `.shape` mismatch, already separately addressed in parent's source, **not** native-retested here.
2. Hardened `compare()` to reject mismatched/missing type-strict preregistered schema, official revision, seed 13, token budget 24, temperature, four fixed prompts, model hashes, negative gates, training/utility flags and evidence class for both arms. Genuine report fixtures still compare; different generated text is only a diagnostic mismatch, not a failure or parity claim.
3. Added fail-closed loopback port-availability preflight before launching the GGUF server. A pre-existing process on port 8834 can no longer be silently mistaken for the pinned QAD runner. **Residual race:** port could be taken between preflight release and server bind; this is not full process/socket ownership proof.
4. Created an isolated review workflow that performs no heavy model inference, preserves raw logs and exit codes, and does not cancel earlier runs on subsequent pushes.

## Evidence (all original raw ZIP bytes verified)
- Original parent RED: Actions `40473645747`, job `122086516186`: 10 tests, 1 ERROR, native skipped. Original parent's native RED: `40473240028`, job `122085269510`, `HF_NATIVE` failed before GGUF; not reinterpreted.
- First fixed software-only GREEN: Actions `40474463360`, source `ab21adef3b94ed84821d58ede234a2f639bc17dd`, artifact `12718854391`, ZIP SHA256 `5006dade64b149ed3b541185595bbf2ab17f4087965697b450bb9d2154d1049e`: **12/12 PASS**, UNIT/COMPILE/PRIVACY exits 0, privacy CLEAN.
- Port preflight prospective RED: Actions `40474634836`, source `4c4d59537cd3bc3c9a3bfdfa754dbd279273880b`, artifact `12719859918`, ZIP SHA256 `8336cebd46a77958b0b1b658fdb7ce87bcc9c2ba37608301fe1fcfb4ca3470ba`: **13 tests, 1 ERROR**, missing `assert_loopback_port_available`, UNIT exit 1; COMPILE/PRIVACY exits 0.
- Final port-preflight GREEN: Actions `40474687659`, source `ce1833f99d142e44d4abe0076247f89f7fb892af`, artifact `12720127094`, ZIP SHA256 `0247be778ed921d44efd9dd2cbcd9661356793892e2ed97297f8a26a804f0611`: **13/13 PASS**, UNIT/COMPILE/PRIVACY exits 0, privacy CLEAN.
- All three downloaded original ZIPs were checked with `zipfile.testzip()==None`, exact `HEAD.txt`, source SHA256 and exit files. All three are stored in private Library `/V13-Checkpoints/2026-10-27/BP1-QAD-Software-Review/` and their retrieved Library copies were byte-identical (`cmp=0`, same SHA256). Cancelled intermediate workflow runs are not reclassified as PASS.

Final source hashes (from original GREEN ZIP): script SHA256 `e99d0b0223a03e2edbdb28b04eef69ba54e370a103af82d78764e08c13c117e2`, tests SHA256 `2360ffe406663d3c017fac7b74b982615fd7d8fa4f7d29fae5de1adcab61089f`.

## Negative gates and next
**Software-only, no native execution in this child, no new C3 training, no learned utility, no Redmi.** STEP2 `UTILITY_FAIL`, B3 `L1_FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, full V13 incomplete. No frozen model, registered cohort, seed, prompt, Age/approval or main change.

Exact next command on a checked-out review branch:
```sh
cd v13/code
PYTHONPATH="$PWD:$PWD/scripts" python3 -m unittest -v tests.test_bp1_qad_native_smoke
python3 -m compileall -q scripts/bp1_qad_native_smoke.py tests/test_bp1_qad_native_smoke.py
```
Next integration prerequisite: independent review of this child against PR #682, then **separate serialized** genuine native QAD FP32/GGUF smoke on exact licensed pinned source and runner, with original raw logs and exits. Do not trigger duplicate heavy jobs while another owner is active. Only after true native source smoke should the separately preregistered 1024-token train-only C3 consumer LoRA and source-disjoint paired heldout scorer proceed. Retention/near-miss, Redmi and whole-system acceptance remain separate.