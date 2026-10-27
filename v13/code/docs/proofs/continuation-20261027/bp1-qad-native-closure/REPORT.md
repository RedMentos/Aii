# Independent BP1 native closure — 2026-10-27 (review only)

Owner: GPT-6 automation11. Parent source: PR #689 head `7a276b66ead51fe0f617f83e05d03c9b87499a2a`; no runtime or registered cohort edits. This is a post-run audit, not a prospective training preregistration.

## Original train proof — Linux-native SHADOW, GREEN

Actions [40479267584](https://github.com/RedMentos/Aii/actions/runs/40479267584) at exact source `6373b5fe576ec824993f451ce16b09de7f2a75ef` completed successfully on 2026-10-27 09:27 UTC. Original artifact ID `12721929819`, ZIP SHA256 `bc4b1846e2c571749ab68db761dcb962177d2d43a943cf275e1aa150334fdf62`, 9,984 bytes, 22 members, CRC PASS, no duplicate/traversal paths. Six original exit files all `0`: BUDGET, DATASET_FETCH, DEPS, GGUF_SOURCE, MASTER_FETCH, TRAIN. Source hash, HEAD, original train SHA `9f356917911983e887f80aaadd8b58365fe43ecbf6632bb5e9e0a1aa8628ff86`, FP32 master `1d90518482c4ec204bebb4820bbaee4f8a38c5a6df72256f86bcd21fe52ad079` and frozen trainer blob `49a752879ae5d19391963742a0f042e740edb2cc` agree with preregistered proof. `BP1_QAD_TRAIN_PROOF.json` SHA256 `895bf212080ec1b2878c8c5aeb49339f51c9f1f5d3a231722c78db1958b0ddc1`. Original 25 train rows, seed13, rank2/alpha4, 2 CPU steps, max1024, 0 anchors/JEPA, CE 0.90984 → 0.64171, 44 GGUF adapter tensors, 38,912 nonzero LoRA-B elements, peak RSS 4,323.2 MB. Heldout files not opened during training. No adapter weights published. These prove a short optimizer/export path, not retained/generalized learned utility.

## Original base-only heldout proof — Linux-native, GREEN

Actions [40479795455](https://github.com/RedMentos/Aii/actions/runs/40479795455) at `c2a245f37d20e813d6f7720ef91f06c41bf87467` completed 2026-10-27 09:29 UTC. Original artifact ID `12722019001`, ZIP SHA256 `d218fcb6ff3c5b820c00921428822ff46cba18c3a60b1bdb2634160f356e3248`, 11,398 bytes, 23 members, CRC PASS, no duplicate/traversal paths. All five original exit files `0`: BUDGET, DATASET, MODEL, RUNNER, COLLECT_SCORE. Original prediction bytes SHA256 `2eae621e4c375f019bb793e4342abf26b69b36e5e245f7f3a53864406ed5e092` match FINAL_MANIFEST and SCORES; binding bytes SHA256 `4a1f0b68054be1d37c79ce81642e1f50d42f5fa35d27b5c56bc82c11b6d913fc` match both. Exactly 11 source pairs × two arms = 22 unique base responses; no candidate tested. Supported no_offer 0/11, offer 2/11; 2 wins, 9 ties, 0 losses, but unsupported commitments 11/11 and 9/11 respectively. This is weak base-only support evidence, not utility promotion.

## Durable raw backup and gates

Both **original ZIPs** were uploaded to the user's private Library `/V13-Checkpoints/2026-10-27/BP1-QAD-Native-Verified-20261027/` as `TRAIN-40479267584-ORIGINAL.zip` and `BASE-40479795455-ORIGINAL.zip`; both were re-materialized and their SHA256 independently matched byte-for-byte. This folder is not the previously rejected anyone-writable Drive destination. Original failed native export and all earlier RED evidence remain untouched.

**No promotion:** STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; Redmi not measured; whole V13 incomplete. No production activation or weight authority.

## Next command and prerequisites

Prerequisites for PR #689's separate prospective native same-job V2: confirm no active/queued heavy owner via Actions, verify its current head and workflow/PREREG unchanged, then create **only** `v13/code/docs/proofs/continuation-20261027/bp1-qad-train-v2-samejob/ACTIVATE.txt` on the explicitly registered trigger branch. Do not change immutable train/heldout/model/runner/seed. Same-job 25-row train + 44 source-disjoint base/candidate responses will take a new isolated runner and upload only proof/logs/predictions/scores, never adapter weights. Independently audit original raw ZIP and failed attempts before interpreting any outcome. If this path is blocked, continue another canonical package.

Local independent audit command (if original ZIPs available under these names): `python audit_bp1_native.py` (private Library audit script; no raw artifact committed to public GitHub).
