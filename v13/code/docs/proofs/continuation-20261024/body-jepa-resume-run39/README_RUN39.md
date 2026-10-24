# V13 Run39 — bitwise synthetic Body-JEPA training resume

Base PR #74 `bfc7e6e1a3c9f235333d75ac599242bde258a970`; preregistration committed **before testing** at `f06ea49202252ca118c24b2f29ca34d466c75fca`. Exact Run38 ObjectiveAdapter dependency copied unchanged, bound by SHA256 `af899ca76c615e1b0954a4c3727601ff58c24ab496268289170d5360aa5daa11`. File ownership only `v13/code/docs/proofs/continuation-20261024/body-jepa-resume-run39/`.

## Implementation

Full synthetic Adam training continuation now persists student, predictor and EMA target weights; Adam per-parameter `step`, `exp_avg`, `exp_avg_sq`; independent minibatch and shuffled-target RNG states; exact dataset hash, source revision, mode, step count, schema, and SHA256. Uses NPZ `allow_pickle=False`, closed manifest keys, finite tensor/shape/dtype checks, bounded compressed and uncompressed bytes, new-directory no-overwrite checkpoint, and no production writes. A checkpoint hash is an integrity fingerprint, not producer authentication. No native B1/B2 body or user data.

## Preregistered results

9/9 CPU software/synthetic tests PASS, compileall PASS. Normal arm uninterrupted 160 steps and 60+checkpoint+100 steps are bitwise equal across all model tensors, Adam moments/step and both RNG states; heldout MSE exactly equal `0.00030293711461126804`. Wrong-target arm also bitwise equal. Corruption, dataset mismatch, extra manifest fields, false native authority and invalid steps rejected. Initial 7/7 PASS was preserved; independent review added closed schema and ZIP expansion bounds without changing the cohort. This is **PASS_SYNTHETIC_ONLY**, not a native body learning proof, real JEPA source proof, retained user utility or V13 acceptance.

## Next

Independently review exact checkpoint restore on a fresh process, crash injection during checkpoint creation, and actual native BodyTrainPort binding on pinned real weights with retention/regression. Full original suite, official privacy scanner and Redmi remain NOT RUN. No Age rights, no production `jepa_weight` change. STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Z6a FAIL; Z8 FAIL; V13 INCOMPLETE.
