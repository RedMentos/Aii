# BP1 pinned b10964 LFM2 LoRA GGUF export preflight — software RED/GREEN (2026-10-27)

Owner: GPT-6 independent, review-only branch `codex/gpt6-bp1-gguf-b10964-export-preflight-20261027`, exact parent `f6d6812a493cc7d2235e97bf16e0324242d1ecd6`. **Synthetic adapter only; no real model weights, training or inference in this package.**

**Cause addressed:** genuine native train Actions `40476209086` failed at `LoraTrainer._export` because the isolated `gguf==0.16.3` writer lacked architecture `lfm2`. Original failed native artifact `12720663578` was downloaded and independently CRC/HEAD/exit checked: dataset0, deps0, master0, train exit1. Original ZIP SHA256 `2177331d444a1deb5706e8a95c8f8543f590cc035b93d40bf7ee7b7a43d98040`; privately backed up byte-identical under `/V13-Checkpoints/2026-10-27/BP1-QAD-Native-Train-RED/`.

**Pinned upstream source:** official ggml-org/llama.cpp b10964 tag resolves to immutable commit `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`; MIT License. `gguf-py` installed from exact checkout in isolated venv as editable package (declares `gguf==0.19.0`), `numpy==2.2.6`. Observed original source git blobs: `constants.py` `e54ee5a0fd41416f191130cdf1efd08507f63894`, `tensor_mapping.py` `d2dfeece59522ffb417f70939cf94ee157591eee`. Source/model/seed/cohort unchanged.

**Functional synthetic result:** exact source checkout and imported package path verified; LFM2 architecture resolved, both HF attention modules (`v_proj`, `out_proj`) mapped to GGUF tensor names; GGUFWriter emitted a four-tensor GGUF v3 LoRA adapter with `general.type=adapter`, `adapter.type=lora`, alpha4, and GGUFReader read back all four names. The synthetic tensor arrays are not trained weights, and no native runner loaded the artifact.

**Preserved software RED:** Actions `40478739329` source `908b439e558ef74e9aab0199cebd816e660ed74a` artifact `12722110243`, ZIP SHA256 `21585ef3dfec1ce1afb1519aa8959d1792172797c7391f4a3093ee04995878f9`. Four tests PASS including actual synthetic export; one wrong-checkout negative test errored due untyped `git` exception. Compile0, privacy CLEAN. Raw ZIP CRC/HEAD/exits audited, private byte-identical backup.

**Verified GREEN:** Actions `40478870140` source `dbb97cc17e3edaf85f292cd9efea331f27a306d6`, artifact `12721429876`, ZIP SHA256 `a427bd7e2edb305e35813b41d17464da251b523978cb516d952a182f2d52b5e1`: **5/5 PASS**, upstream0, compile0, privacy CLEAN. Raw ZIP CRC/HEAD/exits audited, private byte-identical backup. Private folder `/V13-Checkpoints/2026-10-27/BP1-QAD-Export-Preflight/`. **Final exact-source GREEN:** Actions `40478879090`, source `14729d5413bed41f976a8a12a35c3d838c10429f`, artifact `12722345729`, ZIP SHA256 `e250a29564c8316857ab86142ceafac5f44a0dcceabfbdd504f63746000f72cd`: **5/5 PASS**, upstream0, compile0, privacy CLEAN. Original ZIP CRC/HEAD/exits independently audited; private Library re-download byte-identical. This final commit tightens only the negative checkout test assertion.

**Next package:** preserve original RED, change only isolated native train dependency to this source-pinned GGUF writer, rerun the same 25-row QAD FP32 train with seed13/rank2/alpha4/1024 tokens and exact original source hashes. Serialize heavy owner; no adapter weights in public artifacts. Only a real successful export and independent raw audit can close native training. Then secure private adapter and evaluate source-disjoint 44 responses with retention/near-miss.

**Negative gates unchanged:** STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi unmeasured, whole V13 incomplete.

Software command (isolated pinned checkout): `cd v13/code && BP1_GGUF_CHECKOUT=/path/to/llama-b10964 PYTHONPATH="$PWD:$PWD/scripts" python -m unittest discover -s tests -p 'test_bp1_qad_export_preflight.py' -v`.
