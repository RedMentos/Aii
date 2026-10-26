# Run428 — native seed20 negative-control source-identity audit

2026-10-26; owner GPT; review-only branch `codex/run428-native-negative-control-audit-20261026`, based on Run426 verified 126-row diagnostic. Separate from queued exclusive Run427 O_s21 native owner; **no model inference**.

## Observed counterexample
Run426 exact native seed20 P−O `both_exact` mean +0.1389, but P `b1_only` also differs from O (+0.1111; Delta +0.6667). Same-policy-dual utilities tie across all six fixtures, yet their underlying consumer message SHA256 may differ. If a supposedly B2-pointer-only intervention also changes B1-only input messages, the paired utility delta cannot be cleanly attributed to the pointer. This is a design/provenance diagnostic, not a claim that native output is wrong.

## Read-only audit
Use the exact independently verified Run418 safe no-model ZIP (artifact 12624815819; SHA256 `20ce321d29f04089a087421e16ddd5d854c103d36b7c958e4b0e11815f45cac4`), verify outer and all declared inner SHA256, exact frozen fixture/variant row coverage, source/tool row SHA256 and replay bindings. Compute O/P and P/S control equality for `b1_only`, `same_policy_dual`, `both_exact`: consumer input digest equality, B1/B2 offer digest equality, output equality, score delta and per-fixture differences. Publish only hashes, counts, utilities and short diagnostic verdict (no raw generated text). Keep all STEP2/B3/Body-JEPA/Redmi gates negative.

## Next
If B1-only input differs across pointer arms, treat seed20 pointer effect as confounded by changing native offers. Future preregistered experiment should use paired frozen offers (or explicitly quantify native variance), never retrofit Run394 cohort or claim causal pointer gain.
