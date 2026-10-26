# Run551 prereg — one answer, one effective AG9 quality calibration label

2026-10-26, committed before source changes. Base Run550 PR #549 exact head `51a187292adf3851a8f58b317c69863dced520e7`. Run550 exact-head source suite and phone ZIP Actions 40340315450/40340315451 succeeded, software/host evidence only; no native inference or Redmi. This is a fresh independent package, not an amendment of the frozen Run550 cohort.

## Observed bug and authority boundary

`inputs.record_rating` replaces the stored rating for the same answer and origin, but calls `agi.live.on_rating` on every edit; `Metacognition.record` appends an unkeyed calibration pair each time. A single answer rated 40 times can therefore manufacture 40 nominally independent AG9 samples, trigger the MIN_SUPPORT=20 calibrator and raise live effort. A later neutral 5/10 cannot retract the old AG9 label. Implicit chat may also override an explicit note if it arrives later. This is not evidence of 40 independent user judgements or grounded correctness.

## Intended isolated fix

Only the `answer_quality_v2` lane gets a stable event-scoped label key. Preserve all pre-existing unkeyed AG9 pairs without retrospective attribution, do not migrate historical `answer`, and do not touch grounded fact/route/AG12 calibration. The latest explicit note takes precedence over implicit feedback for the same answer regardless of arrival order. A 5/10 explicit note suppresses/removes that answer's keyed AG9 quality label; a changed non-neutral note replaces, never appends. Keep original rating history, source/seed/model hashes, learning/age/approval rights and all negative gates. Use a bounded parallel key list aligned with existing `pairs`, including mixed old/new writes and window eviction; old persisted component states remain readable.

## Acceptance and counterexamples

Synthetic model-free tests: 40 revisions of one event never reach 20 effective samples; replacing negative with positive flips its single pair; explicit 9 outranks subsequent implicit 3; explicit 5 removes prior implicit/explicit AG9 label; distinct event IDs count independently; keyed data survive restart; unkeyed legacy pairs remain intact and bounded. Existing Run546/549 and AG9 tests must pass, plus full source-wide CI on exact new head. Test new and old metadata lengths across WINDOW eviction and legacy component upgrades. Independent read-only diff/negative-gate review and privacy scan before promotion. Record raw Actions URL/sha and exact head; a failing CI stays RED.

Claim limit: quality signal bookkeeping only, no demonstrated accuracy improvement, no STEP2/B3/Body-JEPA/jepa_weight/Redmi promotion. Next functional work: grounded/JEF end-to-end tests and remaining blueprint path.
