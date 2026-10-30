# Run14T pre-native preregistration addendum — isolate decoder settings

2026-10-30 UTC, committed **before any native Run14T calls**. The original Run14T preregistration and fixture remain unchanged. Source review of the actual pinned `v13/code/v13/runners.py` uncovered a confound: when `C3_LANGUAGE` is called **without** `schema` and config `c3_sampling='anti_echo'`, the runner adds `C3_DECODER` bias; with `schema`, it does not. Also schema requests can request token logprobs if `offer_logprobs=True`. Therefore, a comparison using default settings would not isolate grammar constraints.

Before native execution, set **both arms** `c3_sampling='legacy'` (the validated config alternative to anti_echo) and `offer_logprobs=False`. Keep all other frozen settings, same prompt and model/seed/fixture. Record both config values in each raw row and independently verify them. The only intended generation payload difference then is `json_schema` on the constrained arm. This is a prospective method correction, not a posthoc outcome retune; the original seed311 fixture hash `a46ca596386fc2ea75d2779c2a08982cc50fb5e119b4b9990168dfed26450d5a`, arms, thresholds and native call count are unchanged.

No native Run14T proof yet; preflight may have source-only RED attempts. No model weights, output authority, age, STEP2/B3/JEPA/Redmi gates change.
