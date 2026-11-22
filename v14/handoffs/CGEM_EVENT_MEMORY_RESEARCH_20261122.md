# CGEM event-memory research handoff — 2026-11-22

## Primary source reviewed

Xuanzhuo Liu, Chuankang Li, Maoqing Yao, Guanghui Ren, “Remember What Changes the Odds: Critic-Gated Event Memory for Long-Horizon Manipulation,” arXiv:2611.16386v1, submitted 2026-11-12.

- Primary full-text HTML: https://arxiv.org/abs/2611.16386
- Evidence: FULLTEXT_REVIEWED, including theory, ASC diagnostic, ablations, proposed VLA integration, and real bimanual critic event-detection appendix.
- Repository/code search: no author-linked implementation found in the arXiv record or GitHub search. No source, model weights, dataset or dependencies imported. No software/weight license available to adopt.
- Paper status: arXiv preprint; its full VLA integration is explicitly proposed, not evaluated.

## Findings that transfer to V14

1. **Remember decision-relevant outcomes, not just visually salient changes.** The paper's decision-aliasing example has the same observation before an attempt, after a recoverable failure, and after success; the next action differs because the attempt history differs.
2. **Separate event selection, event content and event deletion.** CGEM writes signed progress/failure records, attaches subtask/strategy identity, retains failures while they affect retries, and removes them only after that subtask is confirmed complete. The memory bank is bounded.
3. **Sparse selection can be principled.** Under a fixed reference policy, exact conditional success probability is a bounded martingale; the expected sum of squared changes is bounded by 1/4. This bounds the expected count of events whose change exceeds a fixed threshold, independent of horizon.
4. **The sufficiency claim is conditional.** The theorem assumes every task-register update is detected by a sufficiently large value change, each event record encodes the required update, event order is retained, and all necessary records fit in capacity. A learned critic does not automatically satisfy these conditions.
5. **The exact-value diagnostic is strong but narrow.** In the ten-subtask Aliased Stage Chain, CGEM reports 88.0% success versus 0% for a 36-step observation window, kinematic memory and uniform memory. Removing failure records drops success to 1.7%; removing consolidation drops success to 47.7%. These are controlled diagnostic results, not a real VLA memory-policy evaluation.
6. **Real-data critic evidence is not yet proof of the write signal.** On 87 held-out AgiBot bimanual episodes (42 recoverable failure windows), IQL Mode 7 reports AUROC 0.86, 76% recall and 0.12 false alarms/min using the full chunk TD residual. The value-only residual has a negative detection margin (-0.079). Mode 9 reaches 100% recall but includes the annotated failure penalty in its reward, so it is not an unbiased validation of the event gate. The paper does not test the complete memory policy on the robot.
7. **Force/torque and gripper state can expose outcomes hidden from images.** The paper combines critic-score peaks with BOCPD force/torque changepoints and gripper transitions; without force, sign accuracy falls from 99.3% to 68.3% in its diagnostic.

## V14 mapping / concrete experiment

This is an additive Memory/World/Self event-record proposal, not a replacement for JEPA, replay, temporal memory, or existing T8 authority.

- Candidate source: a committed, trusted T8 ActionSelection/ActionOutcome, plus source-bound perception/audio/UI event evidence. Preserve observed, censored, omitted, unknown and explicit failure as distinct states. Missing/censored outcome is **not** a negative outcome.
- Candidate score arms (kept separate for ablation): (a) signed full TD residual / outcome prediction error, (b) value-only delta-V, (c) sensory changepoint / force-proxy / completion cue, (d) explicit trusted outcome, and (e) a calibrated combination. Do not silently collapse them into one opaque score.
- Event record: stable event ID, event order, action/strategy ID, subtask/goal ID, sign/state, source refs and digests, evidence kind, critic checkpoint, pre/post prediction, score, confidence/calibration and creation/confirmation timestamps. No raw user conversation in the record.
- Retention: keep a trusted failure/negative record while it can change a retry or planning decision; clear only after a source-bound success/completion event for the same subtask/strategy. Bounded eviction must preserve required records or emit an explicit incompleteness/tombstone state.
- Consumer: expose the event memory to World/Self and B1_DETAIL/B2_GIST receiver readouts in SHADOW first; do not grant action or optimizer authority from the critic score alone.

### Required ablations / acceptance

1. Full TD residual vs value-only delta-V vs explicit-outcome-only vs combined score, at matched write budget.
2. Failure records ON/OFF; consolidation ON/OFF; force/sensory cue ON/OFF.
3. Negative controls: shuffled outcome labels, wrong-action binding, missing/censored outcome mislabeled as failure, no critic/no update, duplicate event, stale source digest, and success event for a different subtask.
4. Disjoint train/test episodes and sessions; delayed outcomes; A→B→A return; calibration and false writes per unit time; action/receiver utility; memory capacity/eviction audit.
5. Parameter/checkpoint diffs, optimizer/EMA persistence, restart, rollback and CPU/RSS budget. Keep the complete policy in SHADOW until independent utility and retention pass.

**Decision:** RESEARCH_ONLY / NO_CODE_IMPORTED / NO_LICENSE_ADOPTED / NO_ANDROID_PROOF. The strongest immediate V14 use is an outcome-bound event-memory ablation after the current Store A→B→A CI is stable. Do not change active learning permissions, production replay policy, weights or phone state based on this paper alone.
