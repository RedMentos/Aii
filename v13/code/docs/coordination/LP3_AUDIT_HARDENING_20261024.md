# WP-LP3 independent cross-review — 2026-10-24 (Run 10)

**Base:** PR #45 `2dddeae10c153a4200629c1bff07bf106c0024ec`, based on PR #44 `3834d062a7ea9ba25bc1240e1407317d80587fc9`; upstream integration PR #42 `6c0ae186e0b612dc4118ef9fc60be90882bfe569` based on Claude PR #38 `cb959052433e01c29afc007e02b93aef373deb7f`. Latest GitHub heads/open PRs checked before editing. No newer Claude PR than #38 found in the open-PR listing at the time of inspection. Ownership: only `scripts/lp3_closed_evidence_audit.py`, `tests/test_lp3_closed_evidence_audit.py` and new run10 notes/proofs; no production runtime, Canon, preregistration, active cohort or other owner files changed.

## Independent review findings and fixes

1. **Confirmed audit false-positive (BUG):** PR #45 accepted a syntactically complete cohort manifest with only a pinned `model.safetensors` hash, omitting the six other mandatory HF asset hashes. This contradicts PR #44's seven-file preflight contract. It also accepted inconsistent `lp2_fixture_sha256` and nested LP2 dependency digest, arbitrary `master_scope`, and unsupported nonweight-upstream authenticity claims. Now fail-closed for missing/malformed seven-file digests, exact two fixture dependency hashes, source binding consistency, official repository/revision and honest upstream provenance status. These checks validate *manifest consistency*, not external HF authenticity.
2. **Confirmed attempt-mutation hazard (BUG):** `--make-receipt` accepted a path inside the supposedly immutable attempt directory. A receipt there changes the attempt and is not an independent location. Creation and verification now reject paths inside the attempt, including symlinked parents. Creation uses the resolved safe path.
3. **Confirmed incomplete-cohort gap (BUG):** stray `seed-99.json` and interrupted `.tmp-` evidence were ignored. They now invalidate closure. Failed seed markers remain hard failures.
4. **Negative gate review:** original STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, `jepa_weight=0`, Body-JEPA `UNAVAILABLE`, canonical/full scope incomplete. No runtime authority or phone claim changed. Receipt hash remains only a caller-supplied anchor unless independently published.

## Verification

- `python -m unittest discover -s tests -p 'test_lp3*py' -v`: **43/43 PASS**, 11 new adversarial tests, 32 inherited. `python -m compileall -q scripts/lp3_closed_evidence_audit.py tests/test_lp3_closed_evidence_audit.py`: PASS.
- First modified test run: **24 PASS / 1 ERROR** due to an intentionally strengthened LP2 dependency consistency check; existing synthetic fixture test was updated to bind both hashes. Preserved as a known failed attempt in this note; final run is separate.
- Rechecked actual local prerequisites: `/sys/fs/cgroup/memory.max=4294967296` (4 GiB), no local `model.safetensors`/`tokenizer.json` in inspected mounted/cache locations, `torch=2.10.0+cpu`, `transformers` unavailable, no LP3/native heavy job in local process list. This is a **local container check**, not proof about a separate native host.
- Full checkout/full repository suite and official privacy scanner NOT RUN: `git ls-remote` failed DNS (`Could not resolve host: github.com`). GitHub connector was used to inspect current refs, handoff, ROADMAP, AGENTS, Canon and source. The new source/test diff is restricted to auditor and its tests; no private inputs included.
- Native four-seed LP3 cohort NOT RUN. No Redmi measurements. No new license dependency incorporated.

## Research and provenance (2026-10-24)

Official model snapshot: https://huggingface.co/LiquidAI/LFM2.5-350M/tree/55e5a53e8637c4522a0577040fe68682db3fbbb6 — seven preregistered assets are present. The model page lists license `lfm1.0` (not asserted permissive). The `main` snapshot now has newer chat-template changes; using it would violate the pinned cohort. See https://huggingface.co/LiquidAI/LFM2.5-350M/blob/55e5a53e8637c4522a0577040fe68682db3fbbb6/chat_template.jinja and https://huggingface.co/docs/hub/api. No model bytes, third-party code, or new dependency were copied. Upstream identity of nonweight bytes remains `NOT_INDEPENDENTLY_VERIFIED` until independently checked.

## Next exact work

On a host with full checkout and verified exclusive native ownership: run full regression and public privacy scanner, verify the pinned seven-file HF master + exact revision + dependencies, memory and process ownership, then execute preregistered LP3 four seeds serially; audit and externally anchor the closed raw cohort. A memory-key success still cannot promote JEPA/STEP2/B3 or establish generated-answer benefit; preregister an equal-budget generated-answer causal comparison separately. No user decision required. The rejected anyone-writable Drive backup was not used.
