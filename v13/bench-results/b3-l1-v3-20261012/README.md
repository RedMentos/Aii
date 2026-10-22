# B3-H3 L1 attempt 3: tasks without a short exact/symbolic form (cloud, 2026-10-12)

Script `code/scripts/b3_l1_v3_bench.py` (preregistered before the run: `code/docs/proofs/b3-l1-v3-20261012/preregistration.json`, commit `bc301e1`). Gate `b3bridge.l1_gate` and bridge `b3bridge.Bridge` unchanged (K=4, r=8, 64 B BF16 message). Sender B1 LFM2.5-1.2B per-token states (≤111 tokens), receiver B2 Qwen3.5-0.8B, both pinned GGUF (hash-checked), runner llama.cpp b10964 Linux x86_64. 600 synthetic hand-over notes, 5 paired seeds, fit/select/test 60/20/20.

**Design.** Each sender note has 4 sentences mixing a graded urgency cue and a graded frustration cue (levels 0–4), so the relevant state is spread over the whole note: the minimal oracle EXACT span is all cue text (mean 429 B). `escalate` and `apologize` also depend on receiver-private facts (team capacity, client status) the sender never sees. `action` is sender-computable (control). Target view = `private` (receiver sees only area, capacity, client); `shared` (receiver also sees the note) is a control.

**Test accuracy, private view (mean of 5 seeds)**

| Task | NO_MSG | EXACT (429 B) | SYMBOLIC label | SYMBOLIC attr words | SCALAR 2×fp16 | CONTROL | L1 mean-pool | **LATENT 64 B** | shuffled / random |
|---|---|---|---|---|---|---|---|---|---|
| escalate | 67.8 % | 76.8 % | 77.3 % | 83.7 % | 90.8 % | 69.8 % | 77.8 % | **77.0 %** | 51.8 / 52.3 % |
| apologize | 52.7 % | 85.7 % | 79.7 % | 84.7 % | 93.5 % | 60.7 % | 82.8 % | **80.5 %** | 51.5 / 50.7 % |
| action | 47.7 % | 65.5 % | 81.3 % | 79.8 % | 83.8 % | 51.0 % | 67.5 % | **78.2 %** | 35.2 / 37.8 % |

**Gate G-CALLOSUM-UTILITY-002 (L1): FAIL on all 3 target tasks** (and on all 3 shared-view controls). Prereg rule: PASS needs the gate with SYMBOLIC = label word and with SYMBOLIC = attribute words; neither passes anywhere. What LATENT does pass: beats NO_MESSAGE (+9 / +28 / +31 points), shuffled and random controls, CONTROL, role retention (drop ≤ 0.3 pt), receiver OOD (1.0–1.2 %), bit-identical reload. On `action` it beats oracle EXACT in utility significantly (78.2 % vs 65.5 % at 1/7 of the bytes); on `escalate` it is ahead of EXACT but not significant; on `apologize` EXACT is better. It loses to bounded SYMBOLIC on every task (utility difference −0.02 to −0.07).

**Reading.** Making the exact form long and distributed did remove EXACT's advantage, but the sender's own readout can still compress the graded state into a few words or two numbers; with privileged attribute labels (SCALAR, 4 B) that is clearly better than the learned 64 B message (91/94/84 %). The learned selector also adds nothing over the attempt-1 mean-pool message here (escalate −0.8, apologize −2.3, action +10.7 points). Latency still favours the bridge strongly: 3.1 ms per item (numpy CPU) vs 0.78 s receiver re-prefill of the EXACT span.

**Consequence.** `B3_LATENT` stays `unavailable`, L2 stays locked, LATENT authority 0, no runtime change. A further L1 attempt needs content that a sender-side readout cannot name or regress (no fixed attribute schema exists, e.g. open-ended style/state transfer evaluated by the receiver's own downstream task) or a receiver whose consumer is not a linear readout on pooled state; otherwise SYMBOLIC/CONTROL remain the right B3 channels.

**Claim limits.** L1 receiver-adapter read only (no backbone injection); synthetic templates and labels; EXACT spans oracle-selected; mean-pooled receiver state; SYMBOLIC_ATTR/SCALAR trained on privileged attribute labels (stronger than the bridge's supervision); Linux CPU cloud, not Redmi. Cached model states (`states.npz`, 239.6 MB, sha256 `df80c17b7eaaa01adf0c8690b8a343f65818d67e55e71644cd68f6208dc587d2`) are reproducible from the pinned models and data hash and are kept in the project folder only (`/mnt/project-files/v13/bench-results/b3-l1-v3-20261012/`), not in git.
