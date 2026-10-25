# Run276 preregistration — operator :memory lists only live F5-authorized corrections

Base: PR275 head `d610ff461a4c211a28d4b5449ede029301195a2a`. Disjoint owner: Run276 owns `v13/code/v13/operator.py`, `v13/code/tests/test_operator_memory_authority_run276.py`, `v13/code/docs/proofs/continuation-20261025/operator-memory-authority-run276/*`, optional new CI. All PR270–275 are prerequisites, not integrated into old main.

RED hypothesis: operator `:memory` returns raw active SQLite rows without validating source or F5 HumanDecision/feedback, so revoked corrections remain displayed to the user even though ordinary recall, C1/JEF, ContextOS, B4 and Sleep now reject them. A deleted source can similarly leak stale value through this operator view.

Controls: actual Runtime+Operator+SQLite, synthetic user corrections. Valid local/global facts visible across restart, revoked HumanDecision/feedback/source kind and deleted source excluded, independent valid correction preserved, no cross-session leak, no memory mutation or training. Reuse Memory._verified_rows and retain exact existing operator JSON schema and command behavior. RED before code, focused operator/phone tests and official privacy scan. No native model/Redmi claims; STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE.
