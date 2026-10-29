# P2X CAL36 review checkpoint — 2026-10-29

## Baseline, ownership and evidence
- PR #1099, branch `codex/v13-p2x-cal36-transport-20261029`, review-only child of PR #1093 at `6cf8a19ead783ec12461edbe54230a8d94fe3ac1`. Owner: this isolated CAL36 branch. Do not rewrite #1093 or #1090.
- Preregistration committed before source at `8a670fca39f200c850cf66c7ff9638e59dfa0d87`. Frozen fixture SHA256 `cd3edfdb464c6f99650b1ea32b5b09854268f0b53faa79df22ddcd135f21985a`; 36 calibration rows, 12 A/12 B/12 NONE; 72 calls if native enabled. No training or held-out validation rows used.
- New code: `scripts/p2x_cal36_transport.py` (plan, pinned asset preflight, owned loopback 72-call runner, per-call durable raw, fail-closed offline score and receipt verifier); `tests/test_p2x_cal36_transport_20261029.py` (six tests, fake server only). Parent fixed LoRA `--lora-scaled FNAME:SCALE` reused unchanged. No runtime integration, AG6 adapter registration, weights update or new user authority.
- Exact source-only GitHub Actions run `40884064422` on commit `e7fc937fd69d98d137ae3f1f94554d8f4b503000`: 6/6 focused tests PASS; plan check 36/72 and frozen fixture hash PASS; compile PASS; all stage exits 0. **No native calls**. Original artifact ID `12901762304`, ZIP SHA256 `6191dfa682c6651ffde5d803d348b9aef38aab135e5c454359d5ea240948feb1`; CRC clean, 4/4 internal SHA256SUMS match, stage JSON 0/0/0. Independently downloaded and checked.
- Original ZIP privately backed up at `/V13-Checkpoints/2026-10-29/GPT6-Review-Raw/V13_P2X_CAL36_SOURCE_ONLY_40884064422.zip` and re-materialized byte-identical SHA256. Rejected anyone-writable Drive destination not used.

## Gates and blockers
- Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; AG6 unapproved; Redmi UNMEASURED; V13 INCOMPLETE. No native inference or new learning proof from source-only tests.
- Parent #1096's actual 360 candidate calls all returned NONE, no measured gain. CAL36 is a diagnostic on disjoint calibration data; it cannot replace held-out validation or authorize a production model.
- Native 72-call run remains unexecuted at this checkpoint. Requires exact pinned model/runtime/adapter/binary artifacts, a verified empty serial owner slot and no competing heavy job. Linux-native and Redmi evidence remain distinct.

## Exact next steps
1. Inspect active GitHub Actions native jobs and serial owner; if clear, create a **single** native CAL36 workflow using the same concurrency group as #1093 and exact frozen pins. Do not run overlapping heavy jobs.
2. Install original pinned C3 GGUF with existing `python -m scripts.p2x_base360_native_executor --home HOME --install`; obtain exact llama b10964 tar and original adapter ZIP by SHA. Execute `python -m scripts.p2x_cal36_transport --server-binary BIN --runtime-archive TAR --model GGUF --adapter ADAPTER --out NEW_DIR` once. Independently run `python -m scripts.p2x_cal36_transport --verify NEW_DIR` and audit every original raw call, ZIP CRC and hashes.
3. Preserve native failures and partial raw, publish aggregate results only with claim limits. If transport remains NONE, investigate fresh calibration-only prompt/schema/model-tokenization mechanism; never tune the held-out 72 validation rows. Continue unrelated canonical packages if native blocked.

Remaining execution budget: UNKNOWN. This is a verified intermediate checkpoint, not V13 completion.
