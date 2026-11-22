# Run12B prereg — new 350M contrastive Body-JEPA trainer port and disjoint native NLL pilot (2026-10-30)

**Prerequisite:** Run12A contrastive loss software test (Actions 41043341335) must be terminal GREEN before native. Full unfiltered Run11Z Actions 41042932709 is independent; do not misreport it as Body-JEPA acceptance. This branch is a **new isolated experimental trainer**; original `v13/body_jepa.py` blob `b560d4e88fe457f381e89dfc5d6188a8ec3b306b`, Run11P runner blob `af685a22ddd4ff6412643a8849a1f00bf2112487`, original Run11P RED/HURT, model/seed/score hashes and Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7` are frozen.

## Disjoint seed239 heldout sources — precommitted before code

Four invented train triples (archive, color, key), none reused from Run11P:
1. Avelorn, copper, Kestrel
2. Brimora, jade, Nimbus
3. Caelith, indigo, Saffron
4. Dornwick, ivory, Talon

Use the same Run11P prompt templates for train, paraphrase and wrong-archive near-miss, with the same four external retention questions. Canonical `fixture()` JSON SHA256 `848021441551627c47107c7b1298d338ab674d8983ff10af4848cf33adf77748`. **Seeds 227, 229, 233**. Four arms: `CE` (weight0), `COS_EMA` (original cosine EMA, weight0.25), `CONTRAST_EMA` (new source-group-masked InfoNCE, weight0.25, temperature0.1), `CONTRAST_SHUFFLED` (deranged targets, same weight0.25). Train exactly eight steps, rank2 alpha4 lr0.0005, targets w1/w2/w3, threads2, no KL anchors, no export, no checkpoint import, EMA decay0.9, target eval mode true for both EMA arms. Same 350M LFM2.5 pinned master SHA/license/revision as Run11P; no new paid artifact.

**Pilot metrics:** teacher-forced NLL on train, paraphrase, near-miss and retention before/after, target effective rank, EMA delta, elapsed time, RSS, exact seed/source/model hashes, raw per-arm and failures, original process cleanup. Precommitted exploratory signal: contrastive beats both CE and cosine on paraphrase by >=0.05 mean NLL, in >=2/3 seeds, while not hurting retention vs CE by >0.05 or making near-miss leakage proxy improve spuriously >0.05. This is not a generalization, JEPA, production or STEP2 gate.

## Implementation sequence

1. Keep original BodyJepaTrainer untouched. Create a separate `ContrastiveBodyJepaTrainer` with an explicitly copied/isolated fit loop and new contrastive loss call; no monkeypatch of production module. Add tests proving source contract, loss invocation/target detach and no export.
2. Source-only preflight CI, privacy and exact pinned blobs. Save raw and private byte-identical backup even on RED.
3. **Only after preflight GREEN** and no active native/model heavy owner, create separate explicit native trigger branch, run serial CPU 350M model with fixed master SHA/license. Preserve original raw/negative arms and independent score replay. No native claim before original closed artifact.
4. After verified save, continue next canonical package, not stop at PR.

**Claims and gates:** alternative contrastive objective is *not* canonical noncontrastive I-JEPA. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi UNMEASURED, whole V13 incomplete. No production activation, no learning approval.