# Run629 — pinned C3 master CPU LoRA actual native update (2026-10-27 UTC)

**Review branch:** `codex/automation12-run629-c3-native-lora-compat-20261027`; child PR #624 of Run628 PR #623. **Experiment checkout:** `14239e94bef21ad6a8be1de92e1e2fbf2ae505b5`. Run628 original cohort/model/trainer/script unchanged. Prereg committed `55340428fbe47783bdee99ae60c867479469c8e5` before dependency fix `14239e94...`.

## Original RED retained

Run628 Actions 40420000984 at `4eabc8c0...`: original ZIP artifact 12697866817 SHA256 `62663422b5fb1be210364a12121bd1342ccbc2cee35c3b1c41a9feb75bbbfe44`, all 14 inner hashes independently verified; four source tests, dependency install, pinned model download and privacy scan exited 0, TRAIN exited 1. The exact failure was Transformers 4.51.3 forwarding `dtype` into `LlamaForCausalLM.__init__` before any optimizer step. Failed raw backed up privately to `/V13-Checkpoints/2026-10-27/Run628/Run628-failed-raw-40420000984.zip` and byte-roundtrip PASS. This remains a failed native attempt, not a prior success.

## Prospective dependency-only retry GREEN

Pinned isolated CI changes: `transformers==4.56.2`, `huggingface_hub==0.35.3`; unchanged torch 2.5.1+cpu, peft 0.15.2, gguf 0.16.3, safetensors 0.5.3, numpy 2.2.6. GitHub Actions **40424448052 SUCCESS**, job 121926605004, checkout `14239e94...`. SOURCE_TEST=0 (**4/4**), DEPS=0, DOWNLOAD=0 (official model SHA256 `5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c`), TRAIN=0, PRIVACY=0 (CLEAN). Raw artifact 12698827815 ZIP SHA256 `27e3aa76ef58bcdfc1682aa0c0cb6da429048a0fa910eb90801dbe49204862f5`; **17/17 internal SHA256** verified. Privately saved at `/V13-Checkpoints/2026-10-27/Run629/Run629-native-success-raw-40424448052.zip` with byte-identical roundtrip PASS.

Real Linux CPU `LoraTrainer.fit` executed 2 optimizer steps on the pinned SmolLM2-135M-Instruct master (269,060,552 bytes), rank 2 q_proj/v_proj, `jepa_weight=0`. 115,200 trainable adapter parameters; **46,080 nonzero LoRA-B elements** independently counted by parsing 60 safetensors tensors (all finite), matching native proof. GGUF v3 header contains 120 adapter tensors; `adapter.gguf` 468,992 bytes SHA256 `e2f84ae657b0b90891d7c5c042a897b9bd30021f8a16e399a27fa2704b793f4b`; PEFT safetensors SHA256 `516177efae6ce05ca2121b1c106ecbcddbf257bf0bc5b925e86589ce241aa345`. CE history 2.03457 → 1.95274, heldout master KL 0.000532563, master learned recall **0.0** (NO semantic gain), measured training wall 5.33s, peak RSS 1086.9 MiB on GitHub Linux CPU. These numbers are not phone performance.

Independent local source-only check used **Run627 source ZIP**, 1,329/1,329 SHA256 workspace members PASS, matching frozen trainer Git blob `49a752879ae5d19391963742a0f042e740edb2cc`; related trainer/AG6/prompt-boundary/memory suites **39/39 PASS**. This is *not* a full Run629 checkout or a current Redmi run.

## Claim boundary and next package

**Positive proof:** real CPU LoRA-B weight update and valid GGUF/PEFT adapter artifacts on a public pinned **C3 reference master**. **Not proven:** deployed llama.cpp LoRA compatibility, output logit change, answer-level improvement (observed learned recall 0), current C3 GGUF parity, Redmi, B1/B2 trainability, Body-JEPA, autonomous learning or whole V13. STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Redmi `UNMEASURED`, V13 `INCOMPLETE`; all Age/approval gates unchanged. No model import/activation.

**Next exact step:** preregister a separately isolated native **llama.cpp b10964** test that SHA-verifies its original source archive, reconstructs GGUF from this exact master, loads the hash-pinned Run629 adapter and compares deterministic scale-0 vs scale-1 native logprob/output with negative controls; preserve no-gain if applicable. Then separate C3 output utility, and B1/B2 sparse active-weight + Body-JEPA paths. Independent cross-review and full exact-head privacy/suite remain necessary. Do not promote STEP2/B3/V13 on this partial proof.
