# V13 Run32 — Context OS exact-recent-pin budget invariant (SHADOW guard)

Base PR67 `f33b031714e43788a662dd2ca98ceeb93a5e6081`. Owner Codex Run32 isolated Context OS candidate. Current canonical `v13/code/v13/context_os.py` declares recent history pinned verbatim, but its budget loop at lines ~244–250 includes pinned older turns in compression/pointer candidates (`[s for s in state[:-1] if s[3]]`); this is a static source-path concern, not yet a full Runtime reproduced bug. The existing test asserts newest is never dropped but not all pinned recent turns.

New pure guard validates ContextPlan items before any future ACTIVE application: pinned must be RAW_HISTORY/RAW; restored must be RAW; planned bytes must fit budget; duplicate items reject. A reference budget selector only compresses/pointers unpinned, non-restored turns and returns `NO_PLAN_PINNED_BUDGET` when immutable context cannot fit rather than silently compressing pins. It does not mutate sources, turn on ContextOS ACTIVE, change user rules or infer that a no-error plan is correct.

10/10 software tests PASS, compileall PASS. Tests include pinned compressed/pointer violations, restored pointer, duplicate, over-budget, pinned pressure and no authority. Synthetic/reference only, no real model/KV or full Runtime. No original §8.4 Exact Recall gate promoted.

Next: independently reproduce actual `ContextOS.plan` budget path with full checkout and real Store, add regression for *every* pinned recent turn and restored turn; integrate a fail-closed overflow path with explicit operator-safe abstention or resource budget escalation under existing gates. Do not silently drop pinned sources. Run full context/cache tests and Redmi after integration.

Original gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE.
