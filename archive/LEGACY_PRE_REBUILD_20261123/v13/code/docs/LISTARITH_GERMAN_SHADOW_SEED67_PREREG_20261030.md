# WP-R4 German list_arith SHADOW seed67 — preregistration (2026-10-30)

**PRE-IMPLEMENTATION FREEZE.** Independent branch `assistant/v13-listarith-german-shadow-seed67-20261030`, child of review-only #1215 at `01e4ee82b86a42afec7d76c3f2766270364e1c41`. This is an independent software-only language-coverage package while seed61 native has the serialized heavy-model owner. No native model inference, no production runtime/ToolStep change and **no tool authority**.

## Frozen synthetic protocol

- Exactly **48 German text prompts**, with labels `total` (16), `difference_max_min` (16), `none` (16), and a predeclared **24 dev / 24 holdout** alternating split, eight per label per split. Immutable fixture file `v13/code/specs/listarith_de_shadow_seed67_fixtures.json`. Canonical SHA256 of `json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()` is **`468b231fd196f28e773fba1d541f4ed7c7436d180d78b835e0ad3eb3f85a3d05`**. Pretty JSON file SHA256 `09fb99e521f5b02e409f089467bbb9caa49a91203166c9fe3141ebfe57e0d791`.
- Inputs contain three integer values plus a final German question. Some `none` data lines deliberately contain the word `Gesamtsumme` and a stated sum, but their **question** asks about counts/selection; source data must not cause a false tool proposal.
- New isolated `v13/agi/listarith_de_shadow.py` must expose `propose(text)` returning `{'proposal': 'total'|'difference_max_min'|None, 'authority': 'SHADOW_ONLY', 'reason': str}`; no runner, model, store, tool execution or live hook. Existing `v13/agi/listarith.py` and its English `operation()`, `compute()`, typed value guard, ToolStep, C5, approvals, age rules, source and model hashes must remain unchanged.
- Strict question-scoped German matching. Difference recipe only for explicit **max-minus-min** semantics; specific A-versus-B comparisons, means, medians, percentages, counts, selection and unclear wording must return None. More than 2000 characters, non-string input and multiple conflicting operations fail closed to None. Do not parse data lines as instructions.
- Implementation may use only the **dev** split; evaluate holdout once, without retuning afterward. Success criterion `SHADOW_DE_SUPPORTED` if **at least 20/24** holdout labels exact, **0/8** false-positive proposals on holdout `none`, and all 8 English regression examples keep the original `listarith.operation` result. Otherwise `SHADOW_DE_NOT_SUPPORTED`. This is **not** a model utility gain, C2/JEPA/STEP2 gate or authorization to enable a tool.
- Preserve every failed example and a SHA256-closed software report. Separate further German morphology, multilingual model extraction and live tool-path efficacy require new cohorts and explicit approvals.

**Gates:** Age0 RECORD_ONLY; `jepa_weight=0`; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; Redmi UNMEASURED; whole system incomplete.

**Next exact action:** commit immutable fixture file, then implement shadow-only detector and adversarial software tests, run frozen dev/holdout once with all rows retained, CI/independent review and private backup. No heavy native while seed61 owns the concurrency group.
