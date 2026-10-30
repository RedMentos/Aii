# Run12A prereg — bounded contrastive Body-JEPA candidate, software only (2026-10-30)

**Motivation:** frozen Run11P eight-step 350M EMA-vs-CE-vs-shuffled diagnostic reported `DIAGNOSTIC_HURT`; the original cosine two-view JEPA objective and source/model/seed pins remain unchanged. This is an **alternative loss experiment** to investigate whether in-batch target discrimination can distinguish aligned from shuffled context/answer pairs. It is **not** an I-JEPA replication: canonical I-JEPA uses latent prediction and an EMA target without contrastive negatives. Do not silently replace the canonical objective. Sources: Assran et al., I-JEPA (arXiv:2301.08243); PyTorch `torch.nn.functional.cross_entropy` documentation, accessed 2026-10-30.

**Parent:** Run11Z PR #1256 HEAD `235c579e808fed26392cd31a4ee7b70a142ab1cd`. New files only; no edits to `v13/body_jepa.py` blob `b560d4e88fe457f381e89dfc5d6188a8ec3b306b`, Run11P `bodyjepa_350m_eightstep_disjoint_run11p.py` blob `af685a22ddd4ff6412643a8849a1f00bf2112487`, Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, model or original cohorts.

## Frozen candidate specification before code

- New diagnostic seed **223**. Inputs `student: [N,D]`, `target: [N,D]` and optional source-group labels. N in 2..64, D in 2..4096, float32/float64 finite, each latent norm nonzero, noncollapsed target bank. `target.detach()` always. Optional `weights` finite nonnegative, sum positive. Temperature fixed **0.1** for the primary synthetic tests, API supports 0.01..1.0.
- Normalize student and target rows. Logits `S @ T.T / temperature`; diagonal indices are positives. Mask same-group off-diagonal false negatives, reject if any row has no genuine negative. Use per-row `torch.nn.functional.cross_entropy(..., reduction='none')` and eligibility-weighted mean. Never train a model, export weights or call a native runner in this package.
- Negative control: derange target bank before loss with unchanged diagonal labels; require valid permutation, no fixed points. No claimed equivalence to EMA-shuffled training unless tested on actual model/heldout.
- Primary synthetic fixture: four one-hot targets and slightly perturbed student vectors, fixed seed223. Expect correct assignment loss at least **0.5** below deranged assignment; nonzero finite student gradients and **no target gradients**.
- False-negative fixture: two same-source matching latents and one distinct latent. Group mask must remove the duplicate's negative competition and improve loss; all-same-group must refuse.
- Adversarial cases: N=1, D=1, overbound N/D, NaN/Inf, zero vectors, collapsed target, wrong shape, invalid temperature, zero/negative/NaN eligibility, wrong group count, invalid derangement, target mutation attempt; all fail closed or prove unchanged.
- Output: loss + typed read-only metrics; `authority=0`, `native_calls=0`, `jepa_weight_runtime=0`, `body_jepa_available=false`, `redmi_measured=false`, `utility_proven=false`, `whole_system_complete=false`.

**Acceptance:** isolated CPU torch software tests with actual autograd and finite differences PASS; source/Canon blobs pinned, privacy clean, original raw retained even on RED, no Runtime or Body trainer integration. This establishes **only** that the mathematical alternative is implemented and differentiable, not that it improves model quality or fulfills JEPA/Body-JEPA gates.

**Next after GREEN:** separately preregister a **new disjoint native 350M** cohort with CE, original cosine EMA, and contrastive-EMA candidate, plus shuffled target, heldout paraphrase/near-miss, retention and actual RAM/time. Preserve original Run11P `DIAGNOSTIC_HURT`. No model/phone run is authorized by this software test alone; decide next heavy owner after current software fullsuite terminal.

**Gates:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight0; Redmi UNMEASURED; whole V13 incomplete.