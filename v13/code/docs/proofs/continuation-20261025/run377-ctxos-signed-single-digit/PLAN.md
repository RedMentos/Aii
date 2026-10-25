# Run377 — Context OS exact compression preserves signed one-digit numbers (preregistered)

Parent: Run376/PR371 verified checkpoint `29669bbe05049199feb7cda2be233d11f08e3362` (review chain, not main). Independent of Run375 B3 Callosum and Run373 native C3 owners.

Owned: `v13/code/v13/context_os.py`, new `v13/code/tests/test_ctxos_signed_single_digit_run377.py`, isolated `.github/workflows/run377-ctxos-signed-single-digit.yml`, this proof directory. No change to Context OS mode, Age, user approvals, model/seed/source hashes, history persistence or exact-pinning thresholds.

Observed source bug: `NUMBER` regex protects a sign only in its multi-digit alternative. The single-digit alternative recognizes `-4`, `+5`, `-4%`, `+5kg` as `4`, `5`, `4%`, `5kg`. `compress()` can then drop the sign while still reporting exact-span recall as complete, turning negative evidence positive. This is an actual Context OS information-integrity issue, not a formatting preference.

RED-first: direct `exact_spans` tests require signed one-digit tokens to be preserved verbatim; `compress` must preserve them in derived text when shorter; an actual Runtime/SQLite Context OS SHADOW plan with 10 historical turns must keep `-4` and `+5kg` in its oldest compressed turn without altering source or legacy messages. Existing dates, multi-digit signed decimals, URLs, code/quote spans and inherited Context OS tests must remain green.

GREEN: add optional sign to the existing single-digit NUMBER alternative only. No redesign, no new compression policy, no active-mode promotion. Preserve raw history and source links; this patch protects literal sign in compressed *views*, not semantic numeric interpretation.

Evidence: source-bound RED/GREEN Actions with inherited Context OS and exact-quote tests, compileall/privacy, closed raw receipts with SHA and private Library byte comparison. STEP2/B3/Body-JEPA/jepa_weight/Redmi/whole V13 remain NOT_PROMOTED.
