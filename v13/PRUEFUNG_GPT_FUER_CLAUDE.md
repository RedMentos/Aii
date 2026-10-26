# GPT/Codex review of Claude V13 work — append new rounds at top

## 2026-10-26 — Context OS post-planner exact count (Run417 / PR413)

Reviewed Claude WP-Z5d PR407 (`claude/project-thread-jrdawq`, source parent `c983845aba6b42f2156a8051999d4bb782077ff1`) and the subsequent Run414 exact-count candidate PR410 at `94be24431d447ad146ad5fb5f107fbc28f6134c0`. This review is branch-scoped; no merge into main or Claude's live branch.

**Findings (confirmed by source and adversarial tests):**
- BUG: pre-plan exact `ctxfit.fit` counted a volatile/history view, but `ctxos.plan` could replace the final messages; the actual generated view was not recounted. A high-density post-plan view can exceed the budget despite `fits=True`.
- BUG: strict tokenizer failure was logged and swallowed; runtime proceeded to generation without a verified count.
- NOTE: C3 same-causal uses a distinct 512-token/template ABI, so server `prompt_tokens` is not proven exact for that consumer. The new strict opt-in must reject this mode until parity is demonstrated.

**Fix on isolated Run417 branch:** `require_final_exact` after planning and before generation; strict failures now produce the existing safe `Unavailable` system report; C3 causal mode explicitly unavailable for exact opt-in. Legacy `context_fit_exact_count=0` and Claude's historical 300-row benchmark are unchanged. Synthetic counterexamples include pre-plan fit versus final overflow, invalid/failed native count and causal decoder incompatibility.

**Executed proof:** GitHub Actions 40259968458 at exact head `04b8ee21905f37c8ffe836ccb79557531a0a9625`: `python3 -m unittest -v tests.test_context_fit tests.test_context_os tests.test_runtime_queue tests.test_runtime_queue_audit` -> **41/41 PASS**; `public_repo_privacy_scan.py --base 94be24431 --head HEAD --no-worktree` -> **CLEAN**; compileall PASS. Raw artifact 12624625920 SHA256 `00e87bd2c3bae85914db23ee57612a429e226b1e81da5758e2f06d6f87dd9634`. Exact-head full suite **NOT RUN**; native/Redmi latency and utility **NOT RUN**. Independent actual native model proof remains required before changing the default.

**Negative gates unchanged:** STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Age/Redmi/whole V13 not promoted.

Next: compare actual post-planner native token counts and latency on a disjoint long-session cohort, and prove C3 causal template parity or keep strict opt-in unavailable there.
