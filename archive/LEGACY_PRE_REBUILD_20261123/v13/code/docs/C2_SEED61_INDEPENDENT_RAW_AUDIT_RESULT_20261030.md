# Seed61 original native RED independent review — 2026-10-30

Review-only branch `assistant/v13-seed61-independent-raw-audit-20261030-0635`, parent PR #1216 at `d1bc56ba6c77c19c9e9ddc71595424df4dc3a548`. Prereg committed first at `f05611a99f1c1a57a39a90eccf16fe546d39415a`. This is a **posthoc audit**, not a fresh native run or a replacement gate.

## Original observed native evidence (never relabel original RED)
- Actions `41007813416`, artifact `12955848461`, original ZIP SHA256 `5296bf6bdf9fda8ac2c2b95ec9b73e10a1a1eb53574038c803a9d3ac12c55ad1`: **CI FAILURE** from an indented shell here-doc terminator. Original ZIP CRC clean, 40 unique files, **24/24 native rows generated**, no SHA256SUMS because script stopped before it was written; original 24 rows and original report retained. Native prerequisites PINS/VENV/DEPS/TEST/BOOTSTRAP/NATIVE exit 0. Scores A/B/C/D/E/F = **0/0/6/1/1/0 out of 8**.
- Actions `41008162051`, artifact `12956867267`, original ZIP SHA256 `dd7d00dc04a82180171bc3d1739bb21cd53ead7d3a05e26e4e6ac3b2b8e8556a`: **CI FAILURE** from REPORT_CHECK Python assertion at line 61. Original ZIP CRC clean, 49 unique files, SHA256SUMS **48/48 verified**, **24/24 native rows generated**, PINS/VENV/DEPS/TEST/BOOTSTRAP/NATIVE/COMPILE/PRIVACY/DIFF exit 0, REPORT_CHECK exit 1. Scores A/B/C/D/E/F = **0/0/6/0/0/0 out of 8**. Native C2 invoked and selected **4/4**, but **no measured utility improvement**.
- Both original ZIPs are backed up byte-identically to private Library `/V13-Checkpoints/2026-10-30/Run12-Seed61-IndependentRawAudit/`. The rejected anyone-writable Drive location was not used.

## Concrete verifier bug
The corrected workflow's inline Python line 61 is `assert score_pair(f,row['final_output'])==row['score']`. Frozen `equation_diagnostic()` builds tuples for equation triples; persisted JSON converts these to lists. Therefore direct Python equality is false on valid equation rows even when numeric values are identical. Original second ZIP has nonempty equation triples at indices **2, 4, 7, 12**. A JSON-wire roundtrip comparison, with strict bool/int/float type checks and no numerical tolerance, is implemented separately in `scripts/c2_seed61_wire_score_audit_20261030.py`. The original frozen scorer and original failed workflows are untouched. A changed equation result still fails the new comparison.

## Independent software verification
A separate standard-library raw ZIP auditor was executed locally against both **exact original ZIP SHA256 pins**, checking CRC, manifest, 24 row/report/event/output bindings, native flags, post-close FINAL/OfferPacket PID receipts and C2 PID/context source; both original archives passed these **posthoc integrity checks only**, with 46 post-close PID receipts each. Its nine local adversarial tests passed, including ZIP tamper and PID tamper rejection. This is **not** original workflow PASS or full source/model acceptance.

The review-only GitHub package contains a frozen-scorer exact-source replay, nine adversarial tests and a source-only GitHub Actions workflow. At this checkpoint, Actions `41009888264` was launched at head `988e22f7712613c702f98b731c28f384d8fa6e02`; **result pending**, so do not claim that 24/24 scorer replay is verified until its raw artifact has been checked. This workflow does **not** download model weights or perform native inference.

## Gates and exact next command
Age0 `RECORD_ONLY`; STEP2 `UTILITY_FAIL`; B3 `NO_PROMOTION`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; Redmi `UNMEASURED`; whole system **INCOMPLETE**. No source, fixture, seed, model or scorer was modified.

Next: inspect Actions `41009888264` terminal jobs, download original audit artifact, verify ZIP SHA/CRC/inner manifest and all stage exits, check 24/24 frozen-scorer JSON-wire replay on both immutable originals. If RED, preserve raw and fix **only** independent audit candidate; no native rerun before need is established. Then independently review and continue the next Canon package. Remaining platform budget UNKNOWN.

## Exact-source independent CI verified — 2026-10-30 05:43 UTC

Actions **41009967996 GREEN** at head `46f879d9b02dd62232ad2f4b1d4a492420f4275a`, original artifact **12957500126**, original ZIP SHA256 `987cb6b131d94c282c1c0d73989f9c3670780c847e3deea52047492323e78f5a`. Downloaded original ZIP: CRC clean, 29 unique entries, **26/26 inner SHA256SUMS**, all 11 recorded stage exits zero, privacy scan CLEAN, diff check clean. **9/9 adversarial software tests PASS**. Frozen original scorer source blobs matched; **24/24 JSON-wire-exact scorer replays for each original ZIP** (48/48 total), while preserving original native workflows **RED** and their original scores, source, models and seeds. CI artifact copied to the private Library checkpoint folder. The first CI attempts 41009888264 and 41009934698 were RED because the new test class accidentally bound a function as a Python descriptor (`self.scorer`); corrected to `staticmethod`, no frozen scorer or original evidence changed. All failed attempts remain preserved. This is a **posthoc read-only replay**, not a native-run acceptance or STEP2 promotion.

**Next independent package:** preregister a disjoint German paraphrase/negation/count stress cohort for seed67 SHADOW and measure out-of-template generalization without retuning the frozen seed67 cohort or enabling any live consumer.
