# AGE0d local arithmetic answer audit — experimental

This is a **manual, read-only diagnostic** for a narrow subset of English/German arithmetic. It is not wired into V13's live answers, does not send corrections and does not change Age rights. The original AGE0c false-alarm result still requires staying in SHADOW.

From `v13/code`:

```sh
python scripts/age0d_cli.py --demo
python scripts/age0d_cli.py --stdin-json
```

For `--stdin-json`, paste exactly one JSON object such as `{"question":"What is 2 + 2?","answer":"5"}`, then signal end-of-input (Ctrl-D on a terminal). You can also redirect a local private JSON file. The CLI reads at most 4097 characters, writes no files and prints only the structured diagnostic (status, numerical expected/observed values and non-delivery metadata), never the question or full answer. Avoid putting private prompts directly in shell arguments.

Supported: strictly anchored `What is`/`Calculate`/`Compute`/`Wie viel ist`/`Berechne` with +, -, *, x, ×, /, ÷; half-of and the explicit `Budget ... Euro. Berechne die Hälfte.` form. Unambiguous numeric answers only; recurring decimals, free-form prose, unsupported syntax and ambiguous outputs return `ABSTAIN`, not a correction. A `MISMATCH` is a **diagnostic finding**, not authorization to interrupt the user.

Next: heldout genuine answer traces, false-alarm analysis, privacy/permission review, and Redmi resource measurements before considering any opt-in runtime hook. No live authority is implied by synthetic tests.
