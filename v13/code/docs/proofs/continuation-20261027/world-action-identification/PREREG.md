# Pre-registration — World-JEPA action-consequence identification (2026-10-27)

Review-only child of PR #663 at exact base `21342a61188f79d7d76870b22b3b3a013fe02829`. The frozen 200-step checkpoint was selected after seeds313–315; independent seeds401–403 subsequently showed predictive latent-MSE improvement. Neither set is eligible for this new outcome metric. This new benchmark must be evaluated **once**, without choosing seeds or thresholds after inspecting results.

## Locked model, new data and task

Use exactly the original 200-step checkpoint SHA256 `7cb6158b3f39de2d9fa589906c5ed24ce92869709ce18fc09a70f3804e8b20c0` from Actions 40456356170 ZIP SHA256 `8413b6abcdd2651c0e3346f348f0372b13dc4a407199e29a7e24cb9c1f23979a`, original training source `bff9efa8995b82152c2de853581572991e1bfb8852af792cb02544f584f4b770`, and original Actions 40453512115 ZIP SHA256 `f3f5eef1d0257c60438d80bf79508494a802f98d94e965f96fac4cf92c909be8`. No fitting, calibration, checkpoint changes or runtime authority.

Collect **160 new real Linux synthetic-content file-world transitions each** for seeds **501, 502, 503**, using unchanged independent `z12b.collect_train` process. Preserve raw before/after features, true action index, independent process schedule/log, SHA-bound action intervals and world-overlap labels. No recollection, filtering, tuning or retries based on scores. Verify original and budget input bytes/receipts before new file actions.

**Task:** infer which of 31 possible file actions (5 operations × 6 slots + noop) actually occurred, given the before and after observations. For each row, withhold the true action label from prediction, generate all 31 hypothetical actions, run the frozen World-JEPA first predictor on each, and rank by normalized squared distance to the *observed* target-encoder after-state. Only then compare predicted index/rank with the true action. This tests action-conditioned consequence discrimination, not planning or future action success. Use fixed ascending-index tie-breaking. Evaluate top-1, top-5, mean true rank, per-seed and pooled; also separate world-overlapping vs clean rows.

## Controls and preregistered interpretation

1. **Prior-only:** always guess the most frequent action in the original seed212 training rows, tie-break lowest index. No fresh labels used to choose it.
2. **Raw change-slot heuristic:** choose the slot with maximum raw 10-feature Euclidean before/after change; predict the fixed first operation (`write_short`) on that slot; if every slot is unchanged within 1e-12, predict noop. This strong-ish deterministic observation baseline has no learned JEPA.
3. **Rotated-label control:** score the same model rankings after circularly shifting the predicted action label by +1 modulo 31 (fixed before results). This tests whether ranking reflects actual action identity.
4. Chance reference top1 1/31, top5 5/31; these are **not** empirical baselines or proof of utility.

An exploratory positive signal requires **model top-1 strictly above prior, change-slot heuristic and rotated-label control on each of 3 seeds**, plus model top5 above 5/31 on each. If any seed fails, report failure; never rescue by posthoc slicing or threshold. Show all raw per-seed negatives and world-overlap counts. Even if positive, it does not demonstrate causal/semantic real-world utility, native Body-JEPA, Redmi, AGI or STEP2/B3 promotion; an actual intervention/outcome task with external rewards remains necessary.

Run independent NumPy-only reference after raw evidence closes. Preserve original failed attempts, source/model/seed hashes, negative gates, and no automatic runtime/default change. Age-0 approval and all safety controls remain. Private Library backup allowed; rejected anyone-writable Drive destination forbidden.
