# Age noise estimate (`age_plasticity_policy=noise_aware`), 2026-10-10

Follow-up to the §99 ablation finding “label noise → demotion → more plasticity”. Same synthetic stream and real `AgeControl` as `ablation99-20261010` (learn → 10 % label noise → target shift), 5 seeds.

**Mechanism** (`code/v13/age.py`): per capability, a mean absolute deviation of competence around its EMA (winsorized, so a real change does not inflate it). In `noise_aware`, a non-severe gate failure whose drop lies inside 2× that noise neither counts toward demotion nor resets the stage. Plasticity is scaled by `0.5 + 0.5/(1 + noise/0.05)`, and error reopening is damped by the same factor. A severe or out-of-band drop still demotes normally.

| Arm | learn | noisy | shift | final |
|---|---|---|---|---|
| age (boot) | .024 | .175 | **.053** | .0008 |
| age_stable (stable_reopen) | .024 | .129 | .069 | .0008 |
| **age_noise (noise_aware)** | .024 | **.073** | .079 | **.0005** |
| fixed conservative .45 | .049 | .086 | .092 | .0006 |
| fixed permissive 1.0 | .025 | .211 | .050 | .0019 |

- **Noisy phase:** `noise_aware` beats every other arm in 5 of 5 seeds; error is 59 % below boot and 44 % below stable_reopen.
- **Shift (a real change):** it is slower than boot or stable_reopen, because the noise estimate from the noisy phase decays only slowly. It still beats fixed conservative in 5 of 5 seeds.

The flag stays off: the default remains `boot`, pending the user's choice between `boot`, `stable_reopen` and `noise_aware`.

**Claim limits:** synthetic open-loop stream, linear NLMS learner, no language model. The noise constants (K=2, REF=.05, EMA=.2) are BOOT values and have not been fitted.
