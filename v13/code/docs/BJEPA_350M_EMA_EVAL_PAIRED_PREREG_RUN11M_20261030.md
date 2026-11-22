# Body-JEPA opt-in EMA eval target: pinned 350M paired heldout follow-up — prereg 2026-10-30

Owner GPT-6, independent review-only child of #1240 exact `645c70e8c28fb9e016eaa5d068c2d3977075184d`. This is a **new** 12-arm Linux FP32 native follow-up, not a rerun, edit or promotion of the pre-existing negative three-seed study (#1182). No automatic merge, no runtime activation, no adapter export, no paid provisioning. Do not launch while another heavy model/full-suite owner is active.

## Scientific question
The independent tiny-torch donor experiment showed `jepa_target_eval=True` removes stochastic dropout from the EMA target pass while preserving student gradients and flags (32/32 donor, 121/121 integrated cross-organ). It did **not** show better heldout language learning. Meta I-JEPA and V-JEPA use separate no-grad EMA target encoders; they do not establish that forcing eval improves this LLM-LoRA Body-JEPA variant. The only new variable is target eval mode in the EMA arm.

## Frozen model/source/fixture/cohort
Public pinned master `LiquidAI/LFM2.5-350M`, revision `120bf032c36dd1273de754669da040dba7ad4982`, FP32 master SHA256 **`1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`**; license and pinned revision must be fetched/verified. Body-JEPA exact source Git blob **`b560d4e88fe457f381e89dfc5d6188a8ec3b306b`**, LoRA source **`49a752879ae5d19391963742a0f042e740edb2cc`**, Canon **`218464b12a2d27d92524c751922fa8e1c3fb0ea7`**. Reuse the *unchanged* existing source fixture through importing `scripts.bodyjepa_350m_heldout_ablation_20261030.fixture`, SHA256 **`be4925666ef6ffc2206dc450f775dee8ac7a6eb21fbc67082a0f49f1e3804e95`**: 4 invented training facts, 4 disjoint paraphrases, 4 near-miss leakage proxies, 4 retention questions. Seeds **73/79/83**; 2 training steps, rank2, alpha4, lr5e-4, no anchors, no locality swaps, original configuration otherwise unchanged. Frozen previous source/model/seed hashes and failed attempts are immutable.

## New paired arms and hypotheses
Run **four** arms per seed, each from the exact same verified master, fresh RAM-only LoRA and same seed:
- `CE`: jepa_weight=0, unchanged CE control.
- `EMA_TRAIN`: jepa_weight=.5, jepa_target='ema', `jepa_target_eval` absent (original behavior).
- `EMA_EVAL`: same EMA configuration except `jepa_target_eval=True`.
- `SHUFFLED`: jepa_weight=.5, jepa_target='shuffled', `jepa_target_eval` absent (negative target control).

Measure teacher-forced heldout answer NLL (lower better) on all four fixed groups, plus per-arm frozen-base NLL and elapsed time. Primary paired per-seed contrast: `EMA_EVAL.paraphrase - EMA_TRAIN.paraphrase`. A **bounded diagnostic signal, never utility gate PASS**, requires at least 2/3 seed wins <=−0.05, mean primary <=−0.05, mean EMA_EVAL−CE <=−0.05, mean EMA_EVAL−SHUFFLED <=−0.05, near-miss EMA_EVAL−EMA_TRAIN >=−0.05 (no spurious near-miss gain), and retention EMA_EVAL−EMA_TRAIN <=+0.05. `DIAGNOSTIC_HURT` if primary mean >=+0.05 or retention mean >+0.05; otherwise `DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN`. Report **all 12 arms** including failures, never cherry-pick seeds. No report or result may set utility_gate_pass=True, runtime_jepa_weight>0, age authority, production activation or whole-system completion.

## Execution and evidence
Preregister this before script/tests/workflow. Add model-free tests for exact fixture, 12-arm completeness, threshold logic, opt-in-only eval flag, no-export behavior and explicit `--execute-native`. Run pinned isolated software first; then, only after heavy full-suite owner terminal, a single GitHub Actions Ubuntu 24.04 native CPU job with pinned torch/transformers/peft and original master download SHA/license verification, no model files in artifacts, timeout and bounded resource settings. Preserve every raw log/exit, SHA256SUMS, incomplete attempt and source SHA; privately back up and byte-reverify. Do not claim Redmi or 350M native success without raw verified completion.

Historical three-seed (#1182) status **DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN** remains unchanged; Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi UNMEASURED, V13 INCOMPLETE.
