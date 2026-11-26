# Research & Perception Run 42 — predictive-closure probe and integration status (2026-11-26)

## Verified code and tests

- Branch: research-perception/v14-audio-temporal-window-order-20261126-run41b; parent Perception PR #2524; audio chronology PR #2527.
- Added v14/experiments/predictive_closure_probe.py and test_predictive_closure_probe.py. The probe is pure Python, dependency-free and analytically computes the cross-predictive information in the paper's two-position traffic-light process. It also runs a seeded 200,000-sample finite-sample check.
- LOCAL_LINUX CPython 3.13.5: python3 -m unittest -v — 11/11 PASS; CLI sweep completed and produced finite empirical MI estimates. At q = 0, .25, .5, .75, 1, exact partner-information values were 0, 0.045566, 0.188722, 0.456436, 1.0 bits. Empirical q=.75 estimate was 0.459417 bits; light self-MI estimate was 0.000001 bits.
- Evidence class is SYNTHETIC_ANALYTIC_INFORMATION_THEORY_ONLY. This is not a trained JEPA, not a V14 runtime consumer, not a salience decision and not proof of model learning.

## Research reviewed

Mosh Levy, Aly Lidayan & Yoav Goldberg, Predictive Closure: A Set-Level Characterization of JEPA's Feature Selection, arXiv:2610.27364, submitted 2026-10-19, preprint. Full paper review covered the formal set-level objective, traffic-light cross-subsidization, set switching, feasibility dependence, steering interventions, side-information experiment and appendices.

- Under the paper's stated Gaussian prediction-error / fixed-latent-marginal assumptions, the idealized objective is set-level predictive information, not independent per-feature ranking.
- In the controlled traffic-light setup, the light is sampled independently each frame, but its current value predicts which image position is replaced. The paper reports the light becomes more decodable as q increases while its own future remains unpredictable.
- Experiments use synthetic CIFAR-10 collages, a 3-D latent, 0.9 prediction + 0.1 SIGReg, three seeds for the main sweeps, 25 epochs × 100,000 eight-frame sequences and batch 512. Auxiliary reconstruction uses one seed; side-information adds encoder capacity. The authors explicitly leave effect size in large JEPA systems on natural data for future work.
- Official code repo Mosh0110/predictive-closure is MIT-licensed. Its README lists PyTorch 2.11.0, NumPy 2.4.3 and matplotlib 3.10.8. No checkpoint-weight or dataset license was verified; no code, weights or datasets were downloaded or reused.

## V14 implication and next experiment

Do not rank a perceptual feature solely by its own next-step predictability. Preserve a separate cross-feature predictive-partner term alongside novelty, uncertainty and externally grounded goal/action/reward value. The paper's steering result is indirect and can weaken other features, so no feature should be discarded on this metric alone.

Next executable step: build a source-bound feature-set probe over actual A4/A5 packet sequences; compare scalar novelty against pair/set predictive gain, shuffled-time controls and goal/action-conditioned controls. Keep it shadow-only until it demonstrates stable held-out utility and does not suppress non-predictive but goal-relevant cues. No raw user conversations should be used without separate local consent.

## Audio chronology PR / integration blocker

- PR #2527 branch current code at run start: 18ededfbe84a46b0a1a396f2f07e485cd6b0e860. The exact RAW EAR comparison workflow 45760743601 passed on Python 3.13 and 3.14; runtime deployment integrity 45760743586 passed.
- Exact staged/integrated workflow 45760743615 failed both jobs because Core's recovery wrapper still pins the previous integrated_audio_context_candidate_20261121.py blob 831080bceec90711bd42e0fa4eba47c669975c98, while the Perception child branch's current builder blob is f9a0ed7d1a4312361c4c6c6c397744b0e13ef4f0. Failure: pinned audio composition input changed. No Perception-owned pin was weakened.
- Cross-lane comment 7184640703 was posted on Core PR #2525 with the exact hash and bottom-up rebind requirement. #2525 itself has 7/7 workflows SUCCESS at 9fdf321c9c14ab3b27d0d5947eaca443d5796df3, but it is a sibling branch based on #2524, not yet composed with #2527.
- Do not claim the audio chronology PR is integrated or release-ready until Core composes both sibling branches and exact staged/integrated CI passes.

## Device, updater and release boundary

- Latest historical private V13OBS #115 receipt remains 2026-11-24T09:28:11Z; it reported AI STOPPED_BY_USER and is not a current installation proof. New read-only owner-status requests were created for HEALTH and PIPELINE_STATUS; only an authenticated device reply counts. No LOG_PAGE, UPDATE_REQUEST, shell, chat send, APK install or permission action was performed.
- Redmi/Termux: REDMI_UNVERIFIED; no microphone provider, no Android AudioRecord instance, no new install or device benchmark. Current audio path remains caller-supplied PCM only.
- Release: NOT_RELEASED; no release SHA or deployment claim. No model/weight download, swap, training, permission change or user-data mutation.
