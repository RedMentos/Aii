# Run13J — independent original Linux-native raw review (2026-10-30)

Owner: GPT-6. Review-only child of PR #1299, source HEAD `e79ca481df1258b65a2abc9b9292775f81f09d46`. This is **not** a change to the registered seed227 cohort or scorer.

## Original bytes and execution

- GitHub Actions run **41084466744** completed SUCCESS; actual job `c3-native` and its PINS/VENV/DEPS/TEST/BOOTSTRAP/NATIVE/REPORT_CHECK/COMPILE/PRIVACY/DIFF stages all exited **0**. Preflight tests **11/11**, privacy scan **CLEAN**.
- Original artifact **12990857199**, ZIP SHA256 **`ceb154c61440ac73f911b58317704f030b551aaae0784a96ad73c6d69dc3e906`**, size **28,163 bytes**. ZIP CRC `testzip() == None`; independently checked **35/35** entries in the original `SHA256SUMS` against unmodified ZIP member bytes. **12/12** raw arm JSON rows and the original report present.
- Byte-identical backup: private user Library `/V13-Checkpoints/2026-10-30/Run13J-C3-Native/run13j-native-original-41084466744-e79ca481.zip`; after upload, materialized again, SHA256 identical and `cmp` exit 0. Original Actions artifact and private Library backup are separate durable copies.
- Model SHA256 **`3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`**, revision `657e078c94084481950a2d555a941481f715536b`, synthetic fixture SHA256 `d43a65572d85a3f3c1b2ef81d2903c19de880e643887c9bae96f0facbc1b6712`. All twelve raw rows report pinned model, native C3 `FINAL`, reaped processes and **12 distinct PIDs**.

## Independent direct raw readout

| Frozen outcome | RAW_C3 | JEF_C3 |
| --- | ---: | ---: |
| Real Linux-native calls, final + reaped | 6/6 | 6/6 |
| Numeric components correct (2 per case) | 0/12 | 0/12 |
| Explicit faster-option correct | 1/6 | 0/6 |
| Strict full case | 0/6 | 0/6 |
| Literal `ABSTAIN.` alone | 0/6 | **6/6** |
| Output begins `ABSTAIN` | **6/6** | **6/6** |
| Exact JEF fact-copy | n/a | **0/6** |

Raw output was read directly from each `pilot/raw/NN_ARM.json`, not inferred from workflow SUCCESS. Independent registered verifier `REPORT_CHECK_RAW.log` says `RAW_REPLAY_VALID` and matches these totals. All six JEF outputs were the eight-character string `ABSTAIN.`; RAW outputs had additional unsupported text and one correct lexical faster choice, not full correctness.

**Interpretation:** Native execution/integrity GREEN, **measured C3 fidelity/utility RED** on this frozen exploratory cohort. The fixed Run13I prompt begins `SHADOW EVALUATION ONLY` and explicitly permits `ABSTAIN`; the system prompt also permits abstention. These are plausible hypotheses for the repeated abstention, **not causal proof**. Do not silently change this registered prompt, source, seed, model, scorer or reported outcome.

## Negative gates, scope and next work

Age0 `RECORD_ONLY`, STEP2 `UTILITY_FAIL`, B3 `NO_PROMOTION`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Redmi unmeasured, `canonical_architecture_complete=false`, `user_full_scope_complete=false`. This was Linux-native C3 prompt fidelity, not learned semantics, full-task utility, live C3 delivery, or whole-system acceptance. Original Run13A full-task and G14 full-suite RED remain.

Next substantive package: preregister a **new disjoint** source cohort for a controlled, source-bound native C3 instruction/copy intervention (or investigate direct deterministic JEF answer-form delivery as an explicit, user-authorized operator-only path); retain original Run13J raw and failures. Do not start another heavy native job until current runner owner/concurrency is checked.

Reproduction commands after obtaining original ZIP and pinned repo branch:

```bash
sha256sum run13j-native-original-41084466744-e79ca481.zip
python -m zipfile -t run13j-native-original-41084466744-e79ca481.zip
# Extract in an isolated temporary directory, then:
cd v13/code
PYTHONPATH=.:tests:scripts python scripts/run13j_c3_jef_native_verify.py --pilot /path/to/extracted/pilot --fixture docs/fixtures/run13j_c3_jef_native_seed227_20261030.json
```

Original evidence link: https://github.com/RedMentos/Aii/actions/runs/41084466744 ; PR: https://github.com/RedMentos/Aii/pull/1299 . Platform remaining budget: UNKNOWN.
