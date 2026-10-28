# Run11 paired bilingual native heldout — verified archive audit (2026-10-28)

**Review-only child of #855; no merge to main, no frozen scorer/model/runtime edits.** Preregistration: `RUN11_BILINGUAL_PAIRED_NATIVE_AUDIT_PREREG_20261028.md` at commit `9cb874b947c007a9d79986921d589a955abb316b`. The two native runs finished after their original preregistrations; this subsequent audit is **posthoc** and is not blinded.

## Exact evidence and verification

| Arm | Native run | Source | ZIP SHA256 | Frozen lexical numeric | Frozen unsupported marker |
| --- | --- | --- | --- | --- | --- |
| Candidate numeric-explicit prompt | 40637244491 | `1cd099d0aa856dbca3205460affa613bd3780813` | `b64235b1adf9d1cf90139123790c887b4308d7ea6538aafc99fceab690fbc173` | **12/12** | **1/4** |
| Baseline original prompt | 40637658538 | `f7eb46206bf2f80fe6c81008095d376021a34920` | `2efe9bd177f8366626873da452041bd15ffcdc71ee96eb9567fed6d93fdf42ce` | **10/12** | **1/4** |

Both ZIP archives were downloaded from the exact GitHub Actions run and verified locally: ZIP SHA256, ZIP CRC, **22/22 internal SHA256SUMS each**, eight native stage exit codes each, source/prompt/model/fixture/scorer/collector Git blob readbacks, all 16 ordered raw rows and matching answers/runner SHA/event IDs, CAPTURE_RESULT raw+manifest SHA, Age0 no-tool/no-weight/no-promotion metadata, and recomputation of the frozen lexical scorer. A separate local copy of the scorer's lexical routines was used only for initial sandbox verification; exact-source GitHub CI uses the original frozen scorer. The complete raw ZIPs were saved privately in `/V13-Checkpoints/2026-10-28/Run11-Bilingual-Paired-Native-Audit/` and read back byte-exact at the two ZIP hashes above. GitHub receives only aggregate report/code; raw remains unchanged in Actions and private Library.

## Paired findings (descriptive, not proof of causal/general utility)

Candidate gained numeric proxy matches at **a01 and a02**, lost none; the only runner-route change was **a11** (baseline B1_DETAIL, candidate C3_LANGUAGE), and both arms answered a11 numerically. Baseline a01 contains mutually inconsistent values (37 and 37.50); baseline a02 refuses calculation. Candidate outputs correct values on those two author-labelled prompts. These are 16 tasks in one seed and a single run per arm, with a shared brain per arm and fresh sessions rather than proven global-state isolation. The result supports a **narrow lexical numeric improvement on this cohort**, not general arithmetic reliability or a causal significance claim.

**Known scorer limitation:** all four unsupported-note answers in each arm are recognizable to a human reviewer as expressing uncertainty/no source answer, but the frozen lexical marker recognizes only one per arm. Examples: English `unclear` is absent from its regex, and German `gibt nicht an` is not covered. Candidate u04 also changes the project name from *Blau* to *Blue* while abstaining. These are posthoc observations; **do not rewrite the frozen scorer or retroactively call 4/4 a registered metric**. Future preregistered scoring should test multilingual abstention semantics and entity preservation separately. The lexical numeric proxy is also not a full explanation/grounding check.

## Exact reproducibility

With the two unchanged native ZIPs available:
```sh
cd v13/code
PYTHONPATH=. python3 -m scripts.age0_bilingual_native_pair_audit \
  --candidate /private/candidate-native-40637244491.zip \
  --baseline /private/baseline-native-40637658538.zip \
  --out /private/PAIRED_NATIVE_AUDIT.json
PYTHONPATH=. python3 -m unittest -v tests.test_age0_bilingual_native_pair_audit
```
Output `RUN11_BILINGUAL_PAIRED_NATIVE_AUDIT_20261028.json` contains **no raw answers**, only hashes, aggregate counts and changed IDs. The tests include resealed-archive tampering, source/runner/score and Age0 boundary failures. Software tests do not substitute for the already separately completed Linux-native runs.

## Negative gates and next work

`STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `LP3_heldout=FAIL`, `jepa_weight=0`, `Age0=RECORD_ONLY`; Redmi measurement **absent**, whole system **incomplete**. This audit does not promote any gate. Next independent package: preregister a new **disjoint** multilingual arithmetic+unknown cohort with a better calibrated abstention rubric and source/name fidelity, then run controlled native arms; in parallel pursue substantive Context OS/World-JEPA/STEP2 integration work without overwriting active owners. Original native failure attempts remain preserved.
