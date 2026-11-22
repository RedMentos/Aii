# Run33 prereg — source-exact B2 quote × C3 extraction controlled envelopes (2026-10-28)

**Owner / base:** Independent review-only child of Run32 #940 at exact source `4e5002e9f80850f04c1ef9f6c548210bf2229f44`, verified original-raw aggregate Actions `40726753785`. New files only; no frozen Runtime/Store/Cognition/STEP2 runner, existing cohorts, model/seed pins or Canon edits. This package constructs and tests **counterfactual C3 inputs only**; it does not run C3, claim native utility or authorize live answers.

**Motivation:** Original Run26 Keldara CQ `both_exact` delivered B1 options but B2 delivered **zero verified quotes**; `b2_only` delivered two quotes but not complete rules. The Run32 original-raw audit cannot causally distinguish B2 source delivery from C3 extraction. A controlled input intervention is required before any new native inference.

**New disjoint six-fixture synthetic cohort, frozen before implementation:**
```
(name, language, type, old rules, Option A, Option B, revised)
Velaris EN SPLIT (171,11,true) (118,9,true) (144,12,false) none
Elyndra EN SPLIT (195,12,false) (174,11,false) (181,10,true) none
Seloria EN SPLIT (182,10,true) (168,11,true) (171,9,true) none
Zeradia DE SPLIT (213,14,true) (205,13,false) (198,12,true) none
Torvian DE SPLIT (154,7,true) (165,6,true) (141,8,false) none
Veyron DE SPLIT (164,9,true) (153,10,true) (174,8,true) none
```
Intended outcome balance: A=2, B=2, NONE=2; EN=3, DE=3. New independent future native seeds `20261121,20261122,20261123`; never overwrite original Run15/Run26 Keldara seed `20261114` or frozen 96-route corpus. Reuse Run15 source-text fixture constructor only if its Git blob remains exactly `635e5727a42cb1eac4f84441afda2977b0c8109c`. Fixture generation must be deterministic; freeze the new cohort digest in source tests after prereg.

**Predeclared counterfactual arms (same C3 system/schema, current source, seed and decoding settings):**
- `CURRENT_ONLY`: current user request, no analyst quote.
- `B1_ONLY`: exact options quote from current project's supplier sheet.
- `B1_B2_MISSING`: B1 exact options plus B2 role with empty quotes (observed Run26 failure form).
- `B1_B2_EXACT`: same B1 plus exact earlier rules quote from original kickoff note (software intervention, **not** a native B2-generated offer).
- `B1_B2_DISTRACTOR`: same B1 plus same-project nonrule kickoff introduction of comparable source scope; not a forged rule or other-project quote.

**Source-only acceptance:** Build deterministic user-message JSON with only `current_source` and `analysts`, source hashes and byte offsets stored out-of-band; never place `oracle`, expected action, scoring fields, source hashes, hidden full history or model output in the C3 prompt. Verify every quoted span exactly belongs to its declared source and project; reject wrong project, tampered source, changed source identity, unsupported arm, or a quote that contains unregistered data. Verify A/B/NONE balance, EN/DE balance, deterministic hashes and no native/learning/authority flags. Focused real Python tests, full source-only suite, compile, privacy and diff, RED-first evidence and private backups if possible.

**Future native gate (NOT authorized as completed by this package):** Separate exclusive native owner installs/verifies pinned models/runner, runs 5 arms × 6 fixtures × 3 seeds serially with restart/retention, C3 outputs and exact field scores sealed privately. Compare `B1_B2_EXACT` vs `B1_B2_MISSING` and `B1_ONLY`, include `DISTRACTOR` and `CURRENT_ONLY`, inspect C3 extraction and uncertainty, never optimize on Keldara. The exact-source intervention tests *C3 ability given information*, not actual B2 quote-generation quality or STEP2 two-body complementarity.

**Negative gates:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; whole V13 incomplete. Remaining platform budget UNKNOWN.
