# Run32 original raw quote-coverage CI amendment (2026-10-28)

Read-only CI may fetch **only** original Run26 Actions artifact `12826794972` using scoped GitHub Actions read permission, validate exact ZIP SHA256 `989abb8ac7b8fcd91ec047f97b735c9c8f84342e49251855b3375f7b3519762b` through the frozen Run30 auditor, then compute Run32 per-role verified quotation coverage. It must upload only counts and booleans, not the original ZIP, source text, oracle, analyst quotations or model outputs.

**Expected non-causal observation:** `both_exact` B2 verified quote count 0, B2 earlier-rule coverage false, B1 option-figure coverage true. Do not infer that C3 is solely responsible for the action/remaining failures; no new model inference, no live F5 authority, no STEP2 gate promotion. Any failed fetch, source hash, malformed payload or quote coverage check is RED and retained.
