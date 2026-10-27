# BP1 QAD native train with pinned b10964 GGUF writer — prospective rerun (2026-10-27)

Owner: GPT-6 independent; review-only child of pinned export-preflight branch `7b21031d97cfac22d5dfc4b25d7e63641fb1e96d`. Do not launch any heavy native job until that branch's isolated LFM2 writer roundtrip passes, its original raw ZIP is audited, and no other heavy owner is running.

Prior genuine native Actions `40476209086` failed after 13 minutes at `LoraTrainer._export` with `Unavailable: Unbekannte GGUF-Architektur: lfm2`. The frozen 25-row train, source QAD FP32 master SHA `1d90518482c4ec204bebb4820bbaee4f8a38c5a6df72256f86bcd21fe52ad079`, immutable train SHA `9f356917911983e887f80aaadd8b58365fe43ecbf6632bb5e9e0a1aa8628ff86`, seed13, rank2 alpha4, 2 CPU optimizer steps, 1024 tokens, jepa0, anchors0 and no heldout optimizer inputs are unchanged. Original native RED remains preserved.

Change only the isolated training workflow's GGUF writer dependency from incompatible `gguf==0.16.3` to the exact `gguf-py` source at pinned llama.cpp b10964 Git commit `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`, with verified git HEAD, source path, writer mapping preflight and full raw exit logs. The canonical runtime trainer file is frozen and must remain byte-identical. No model/seed/cohort substitution.

After software proof GREEN and owner serialization, run genuine Linux CPU training on all original 25 rows. Record source/license/dependency hashes, exact train optimizer exits, adapter LoRA-B nonzero, GGUF/PEFT SHA, peak memory, and original raw ZIP. Adapter weight files must not enter public artifacts; no inference/utility/Redmi claim. Native training may still fail due shape/ABI/runtime and must remain RED if so.

STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi unmeasured, full V13 incomplete. Next after native proof: secure adapter bytes in a permitted private checkpoint, then separate preregistered base+LoRA 44-response source-disjoint heldout evaluation with retention/near-miss.
