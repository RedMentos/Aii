# Run13A seed211 full-task runner — source-only verified checkpoint (2026-10-30)

Owner: GPT-6 automation, review-only. Parent preregistration PR #1277 at `ce7044efd4b214550814435dcc84af7ed434a1d8`. This package is PR #1278, branch `assistant/v13-run13a-fulltask-runner-review-20261030`. The production `main` and all original Run12N/Run12M cohorts are unchanged.

## Concrete source

- `scripts/c2_body_fulltask_run13a.py`: 8 frozen disjoint seed211 tasks × four counterbalanced arms = 32 isolated turns; actual Run12N Runtime/Store lifecycle, observer OFF, preclose/postclose and C2 strict records, exact frozen Run11V numeric scorer and Run12N explicit faster-claim lexical parser, per-turn component 0–3 and strict whole-task 0/1. No live JEF repair or learning.
- `scripts/c2_body_fulltask_verify_run13a.py`: independent read-only 32-row replay of source, release, native flags, frozen scores, strict C2 admission, full-task components, arm summaries and negative gates.
- `tests/test_run13a_fulltask_runner.py`: prospective 32-row threshold/arm-balance/negation/contradiction/invalid-native controls, plus real API fake-runtime preclose/postclose integration. No model download.
- Original seed211 fixture SHA256 `e6718093ccd83d556019223eca2d5317668d1ada25659519a699aee681a8b97f` unchanged. Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## Source-only proof (NOT native)

- GitHub Actions run `41064871481`, exact tested source HEAD `0b2fc1f9df254933a70cc2af298406e99602b164`, seven enforced stages PINS/VENV/DEPS/TEST/COMPILE/PRIVACY/DIFF all exit 0. **43/43 focused tests PASS**; privacy CLEAN; diff clean. Job logs show enforcement success; the API's top-level run conclusion was still lagging at initial audit, so check terminal before calling the whole run completed.
- Original artifact `12981932424`, ZIP 4,935 bytes, SHA256 `d848a34404ef885ca344fd1390349f7d302d5922c9c6a0bfc80ba3d51389e800`; CRC clean, **16/16 inner SHA256 manifest entries**, HEAD and all seven stage exits replayed.
- Private Library backup `/V13-Checkpoints/2026-10-30/Run13A/RAW_41064871481_shaD848A344.zip`; re-materialized and compared byte-exact with original. GitHub review branch and PR persist source. No anyone-writable Drive destination used.

## Binding negative gates and next work

Age0 `RECORD_ONLY`; STEP2 `UTILITY_FAIL`; B3 `NO_PROMOTION`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; Redmi `UNMEASURED`; `comparative_utility_proven=false`; whole V13 incomplete. Source-only tests are not model/native utility. Frozen prospective exploratory signal: native F numeric >= best A/B/C +3/16, strict full >= best +2/8, at least two F native non-simple route selections, 32/32 structurally valid and 8/8 strict C2 admissions; never promote STEP2 from this pilot.

Next exact source check: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_run13a_fulltask_prereg tests.test_run13a_fulltask_runner`. Then add an independent synthetic 32-row verifier replay/tamper suite; run pinned source-only CI and archive original raw. After source CI and heavy-owner check, launch one serialized Linux-native job via a new workflow using `v13-step2-budget-paired-native-20261030` concurrency group, bootstrap pinned public models, run `python v13/code/scripts/c2_body_fulltask_run13a.py --home "$V13_HOME" --out "$E/pilot" --fixture v13/code/docs/fixtures/c2_body_fulltask_run13a_seed211_20261030.json`, then independently replay original raw with `c2_body_fulltask_verify_run13a.py`. Preserve all failed rows and original ZIP; privately back up byte-exact before any claim. Real Redmi action still requires device access.
