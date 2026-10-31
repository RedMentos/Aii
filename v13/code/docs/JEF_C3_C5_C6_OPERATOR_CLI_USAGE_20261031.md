# JEF/C3 → C5/F3 DRAFT → C6 local operator CLI (SHADOW only)

This is a **standalone, opt-in diagnostic** for one bounded two-source A/B/NONE choice. It is **not** a general conversation interface, real approval flow, or proof of AGI. Source records and the uncommitted assistant message row persist in the local V13 SQLite Store, but no FINAL or user-visible answer is committed. On Runtime restart, canonical Store recovery changes any pending DRAFT to INTERRUPTED; it is not a resumable delivery authorization. The CLI prints only redacted status/hashes, not source text or raw C3 output. Do not put private input JSON in this public repository or GitHub Actions.

## Local input example

Save the following UTF-8 JSON to a file on your **own** device, e.g. `/tmp/jef-choice.json`. These are synthetic example values, not a user record:

```json
{
  "project": "GardenA",
  "domain": "community garden",
  "policy_source": "Project GardenA archived community garden policy. Maximum water allocation: 100 drops. Maximum setup window: 20 cycles. Required shaded: true.",
  "sheet_source": "Project GardenA latest community garden option sheet. Option A: water allocation 80 drops; setup window 12 cycles; shaded true. Option B: water allocation 120 drops; setup window 15 cycles; shaded true.",
  "current": "Project GardenA. Choose Option A or Option B using the archived community garden policy and latest option sheet. If neither qualifies, choose NONE."
}
```

All five keys are mandatory; no extras or duplicate keys. Project ID, domain, grammar, fields, units and flags must match across sources. Maximum 2048 characters per source, 16 KiB JSON file. This bounded typed source grammar is intentionally narrow.

Input must be a directly opened **regular local file**, not a FIFO, device node, directory, or symlink. The CLI uses a nonblocking, no-follow open and reads at most 16 KiB + 1 byte before rejecting oversized input. This prevents a writerless FIFO from indefinitely blocking input validation. It does not make an operator-owned path safe against a hostile same-user filesystem or prove Redmi behavior.

## Run

From repository root with a locally installed V13 Python environment and `PYTHONPATH=v13/code`:

```bash
# Test-only synthetic formatter: no model call.
PYTHONPATH=v13/code python v13/code/scripts/jef_c3_c5_c6_operator_cli.py \
  --home /path/to/local/V13_HOME --input-file /tmp/jef-choice.json \
  --mode synthetic_wrong --operator-opt-in --callback-opt-in

# Real local C3 model (only if the pinned GGUF and runner are already installed).
PYTHONPATH=v13/code python v13/code/scripts/jef_c3_c5_c6_operator_cli.py \
  --home /path/to/local/V13_HOME --input-file /tmp/jef-choice.json \
  --mode native --operator-opt-in --callback-opt-in
```

Without **both** explicit opt-ins, the command returns `OFF` before reading input or opening Runtime. `native` refuses if the installed C3 GGUF SHA256 is not `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d` or the runner SHA256 is not `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. It does not download models, change config, or claim a registered benchmark. `synthetic_exact` and `synthetic_wrong` are software tests only.

A successful `SHADOW_DRAFT_PREFLIGHT_READY` means an independently source-verified A/B/NONE DRAFT and C5/F3 packets existed during that invocation, and the read-only C6 challenge returned `NEEDS_REAL_TTY_APPROVAL`. Restart invalidates that DRAFT to INTERRUPTED; rerun with current human sources rather than trying to deliver a stale draft. That status **does not approve or deliver** anything. A C3 formatter mismatch remains `FORMATTER_MISMATCH_RED`; the source-only JEF fallback is separate. If a later source changes, a future preflight must recheck it before any authorized delivery. No model learning or Age promotion occurs.

The original Run63 native strict receiver pilot remains RED (RAW 2/3, TYPED 1/3); Run65's native 3/3 C5/C6 structural fallback PASS with strict C3 1/3 is independent. Linux software/native evidence is not Redmi evidence. Do not merge this CLI into the production Runtime command router without a separately authorized, tested age/TTY/output path.
