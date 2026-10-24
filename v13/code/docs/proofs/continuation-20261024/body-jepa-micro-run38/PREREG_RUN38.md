# Run38 preregistration — Body-JEPA ObjectiveAdapter synthetic micro-port

Committed BEFORE any Run38 training/evaluation. This is a synthetic CPU-only reference experiment, **not** native B1/B2 training, not a body JEPA gate and not a user Age learning right.

Source mapping: V13 Canon §13.1–13.4 and IH-H25. Implement the full ObjectiveAdapter field contract for a bounded B1 active-adapter synthetic path. Teacher/target must be stop-gradient EMA; only student adapter and predictor are trainable. No router/base weights, native model, runtime, or user memory writes. One CPU training job at a time, no overlapping native jobs.

Fixed synthetic generator: latent dimension 8; action dimension 2 one-hot; x Gaussian; next latent = 0.65*x + 0.25*roll(x,1) + 0.15*action @ fixed 2x8 coefficient matrix + N(0,0.01). Train 128 pairs, held-out 64 fresh pairs, seed 20261024. Use PyTorch CPU, one thread. Student and EMA target projectors start identity; predictor linear on [student(x),action]. Adam learning rate 0.02; 160 updates; EMA decay 0.95; loss = per-sample MSE to detached target(next latent) plus variance-floor regularizer (coefficient 0.01). No global backward graph. Eligibility weight in [0,1] per sample.

Controls: untrained predictor at same initialization; wrong-target control with shuffled target within train set; zero-eligibility update; stop-gradient target. Test holdout using the frozen heldout next latent through the EMA target projector. Do not tune after results: failure remains a failure.

Synthetic PASS criterion: heldout MSE of trained model <= 0.5 * untrained baseline, and wrong-target MSE >= 1.25 * trained MSE; target has no gradients; student and predictor update; EMA target moves; zero eligibility causes no weight update; exact checkpoint save/reload and corrupted hash rejection. Any unmet condition = FAIL_SYNTHETIC. Even PASS remains PASS_SYNTHETIC_ONLY, never STEP2/B3/Body-JEPA/jepa_weight/full V13 promotion.

Retain complete raw metrics and failure logs. No external model downloads, no Redmi, no source changes outside isolated Run38 package.
