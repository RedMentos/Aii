# V13 full unfiltered JEF + Body-JEPA integrated software review — preregistration 2026-10-30

Base: PR #1173 verified checkpoint `4b3ebeec764a494597b3349c6e59f0404ae2ba97`. Review-only CI child; no runtime/Canon/model/cohort changes. Own only new workflow, prereg and result delta.

## Scope
Replay the **entire** Python `test_*.py` corpus on the combined branch containing the verified JEF operator current-session, duplicate receipt, FINAL barrier and restart chain (#1167/#1168/#1170/#1171) **plus** Body-JEPA exact integer shuffled-target guard (#1173). Previous unfiltered reviews #1169 and #1172 are branch-specific and cannot prove this additional Body-JEPA source edit.

## Frozen execution
- Ubuntu 24.04, isolated venv: NumPy 2.2.6, torch 2.5.1+cpu, Transformers 4.44.2, PEFT 0.13.2, psutil, PyYAML, Pillow, prompt-toolkit 3.0.52.
- `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py'` without exclusions or waivers.
- Historical frozen Run34/Run37 `native_source_or_catalog_changed` preflight errors remain expected RED; never rewrite original preregistered source. Any additional errors are regressions to investigate.
- Capture exact source and Canon blob hashes, dependency freeze, complete raw, exit statuses, privacy/diff, SHA256SUMS, artifact CRC/hash verification. No native model downloads or Redmi.
- Keep jepa_weight=0, Body-JEPA utility NO_SIGNAL, STEP2/B3/LP3/World-JEPA and whole-system gates unchanged.

## Coordination
The prior JEF-only unfiltered full suite #1172 was still in progress when preregistered. Launch this expensive combined review only after that run completes and is audited.
