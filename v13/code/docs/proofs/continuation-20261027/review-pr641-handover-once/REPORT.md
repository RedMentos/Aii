# GPT independent cross-review: Claude PR641 handover counts one source event once (2026-10-27)

Review-only child of PR644 `4abc439c12d38e7034a3506b40005248e685fb1f` on Claude PR641; not merged. Scoped source: `v13/code/v13/route_supersede.py`, new `tests/test_review_pr641_handover_once.py`, isolated CI. No change to human rule authority, threshold `HANDOVER_N=8`, route head weights, cohorts or original gates.

## Concrete defect
Before repair, `route_supersede.observe` appended each `decide` call as a new independent head/rule agreement, even with identical `event_id`. Eight retries of a **single** source event made `learned=True` and allowed a human to hand off the fixed rule without eight distinct observations. Repeated event with a changed route was also double-counted. This is a real handover evidence/authority boundary, not model quality.

## Preregistered RED and narrow GREEN
- Actions **40440230101** at `982e6e76139a281d1418c984c68aaa738e782b03`: **12 tests, 2 FAIL** (8 duplicates counted as 8; latest disagreement produced 2 records). Distinct-event positive control and old route-word tests PASS; privacy CLEAN. Original raw artifact **12705812472**, ZIP SHA256 **5e50814f63ca3b3a35f48323a7fabe599945a379faa5b33fe1f7fae69ec9fe23**.
- Repair deduplicates by non-null `event_id` within the existing optimistic state transaction, keeping the latest observation for the event; `None` retains legacy synthetic/manual observation behavior.
- Actions **40440330784** at exact source `1d92008da0fb8baa5b501f7487d255e14eb988c2`: **12/12 PASS**, privacy CLEAN. Original raw artifact **12705847505**, ZIP SHA256 **4ffd2762bbc0887f681095ec8cdc221ada227f2be53f40453a29e75a0edcc882**.
- Both original raw ZIPs downloaded; CRC, source HEAD and test/privacy exit flags checked; private Library `/V13-Checkpoints/2026-10-27/Review-PR641-Handover/` re-materialized byte-identical. No native model or Redmi test.

## Limits and next
This corrects retry accounting only. It does not prove that eight distinct questions represent semantic generalization or that a learned head should replace the fixed rule in daily use. Existing negative gates unchanged: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight0; Redmi unmeasured; V13 incomplete. Next: Claude cross-review/cherry-pick this isolated fix when integrating PR641, test real human feedback lifecycle and full-suite on the selected integration head; no main merge.
