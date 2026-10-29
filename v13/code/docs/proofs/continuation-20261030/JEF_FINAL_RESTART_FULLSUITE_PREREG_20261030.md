# V13 full unfiltered software replay after FINAL and restart — preregistration 2026-10-30

Base: PR #1171, verified checkpoint `0a153ec51a1ca13e84eb54b27e7974b9899868ae`. Review-only CI child; no runtime/Canon/model/cohort changes. Ownership: new workflow, this prereg and result delta.

## Target
Re-run the **entire unfiltered** Python `test_*.py` corpus on the latest integrated JEF chain including current-session guard (#1167), identical feedback exact-once (#1168), FINAL-only explicit outcome (#1170), and delivered-turn/restart evidence (#1171). PR #1169's earlier full-suite replay is a sibling from before the FINAL/restart packages and cannot be silently used as evidence for this newer source.

## Frozen execution
- Ubuntu 24.04, isolated venv: NumPy 2.2.6, torch 2.5.1+cpu, Transformers 4.44.2, PEFT 0.13.2, psutil, PyYAML, Pillow, prompt-toolkit 3.0.52.
- `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py'` with **no exclusions or waivers**.
- Historical frozen Run34/Run37 native source-preflight checks may remain RED from `utility.py` source identity; preserve original failures. Distinguish any new regression from these inherited failures.
- Capture full stdout/stderr, source hashes, dependency freeze, all exit statuses, Canon SHA, privacy/diff, internal SHA256SUMS, upload artifact even on failure. Verify CRC and hashes after download.
- No native GGUF or Redmi, no STEP2/B3/Body-JEPA/LP3/World-JEPA gate promotion.

## Execution coordination
The earlier full-suite review PR #1169 was still running when this preregistration was written. Start this new expensive suite after that attempt completes or is otherwise explicitly accounted for; do not create unnecessary simultaneous heavy review jobs.
