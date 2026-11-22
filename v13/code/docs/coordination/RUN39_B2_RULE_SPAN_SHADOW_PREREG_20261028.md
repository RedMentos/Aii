# Run39 — source-exact older B2 rule span SHADOW prereg (2026-10-28)

**Owner:** independent review-only candidate, branch `assistant/v13-run39-b2-rule-span-shadow-20261028`, exact parent Run37 PR #946 at `b8f4cd794a6c3fbe371c62a117144be3ebb960a2`. This document is committed **before** the candidate source, tests, or any experiment. No changes to frozen Runtime, SourceHandoff, TP/s27, Run12b, Run33–37, original raw or model weights.

## Prior evidence and falsifiable hypothesis

Original TP/s27 native Run12 visibility diagnosis: all six SPLIT/RULE earlier-rule fixtures had zero source-verified complete earlier-rule visibility in B2. Run12b offline source-only candidate recovered the relevant old project note in 6/6 synthetic replays but used a **first 240-character** excerpt, and scanned only `retained[:slots]`. These limitations can omit the actual binding rule if it lies beyond the first 240 characters, or the note lies outside the newest slots. Run38 original Keldara diagnostic separately identifies a missing earlier rule in B2's actual native context. Run36 shows a distinct C3 consumer failure even when exact rules are delivered.

**Hypothesis:** A strictly read-only source-exact span selector, scanning a separately bounded historical-offer window and choosing a 240-character span containing at least two literal rule *cue types*, can expose a binding older rule without using a model or oracle. This is a software visibility claim only; it does not show B2 native quote generation, C3 correct decision, or end-to-end utility.

## Frozen comparison and safeguards

- Baseline: `scripts/run12_b2_context_identity_candidate.py` as read at parent Git blob `66e80c6d049646303263398551e00429aefe24ba`. Do not edit it.
- New isolated module: `scripts/run39_b2_rule_span_candidate.py`, not imported by production. New test: `tests/test_run39_b2_rule_span_candidate.py`. No config or authority change.
- Input: original B2 offer identity/session/generation/model/source refs; a caller-provided `Store.read_source`-equivalent integrity-enforcing reader. No oracle or model outputs in selector. Exact source spans and empty hypothesis only; `PRIOR_HYPOTHESIS_NOT_FACT` and `SOURCE_POINTER_ONLY_SHADOW` labels.
- Trigger only for one unambiguous named project and an explicit earlier/prior/previous rules request. Reject cross-project, mixed-project, missing/deleted/changed source, ambiguous equally qualified rule sources, insufficient lexical cues, malformed refs, over-budget output, and mismatched session/generation/model. No answer selection or rule truth is inferred.
- Fixed bounds: at most 64 supplied offers, default scan 32, default excerpt 240 characters, default context budget 768, output at most one source item. The `slots` argument is an output bound, not the scan horizon. Runtime integration would require a separate audited read-only historical-offer query and a new cohort; no implicit use of unretained history.
- Tests: synthetic old rule after char 240; beyond newest output slots; same-project sheet negative; Atlas distractor; mixed-project; conflicting old rules; revocation and mid-read mutation; wrong generation/session/model; no-trigger; malformed ref/bool bounds; negative superseded note; tight context cap. Run focused tests, compile, frozen-blob check, privacy and diff in source-only CI. Record RED/failed attempts and original raw.

## Acceptance and limitations

Software candidate succeeds only if exact old rule excerpt is selected in positive tests and every negative control remains excluded, with immutable original Run12b and frozen source unchanged. A CI pass is **synthetic/source-only**, never native, never evidence of utility or a STEP2 promotion. The next meaningful experiment is a fresh preregistered B2+C3 native long-note comparison with actual quote verification, action and remaining fields, and exclusive native owner.

**Negative gates remain:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi UNMEASURED; V13 incomplete. Remaining platform budget UNKNOWN.
