# Current-chain JEF source receipt + connected native full software suite prereg — 2026-10-30

## Exact input
Parent `cee5af7064ec81f6eff27eb00b20a3f3aa7596f7`, review-only combined merge of #1192 current-chain Age0 native evidence and #1193 JEF report-source SQL repair. Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, JEF source blob `132b307270c1c27166a69cefdff7eaf75cfea8ad`. No changes to registered models, seeds, source cohorts, scoring thresholds or historical test fixtures.

## Frozen plan before execution
Run the entire unfiltered `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py'` on Ubuntu 24.04 in a fresh isolated venv with CPU `torch==2.5.1+cpu`, `numpy==2.2.6`, `transformers==4.44.2`, `peft==0.13.2` and prior required lightweight packages. Confirm actual imports, pip check, compile, privacy and diff; retain all original stdout/stderr, exit statuses, package freeze, source/Canon blobs and SHA256SUMS.

Expected discovery: approximately **3,399** tests (3,395 previous #1188 plus four new JEF source-receipt tests). Previous exact parent baseline on #1188 was 3,395 tests, **2 frozen Run34/Run37 source-pin errors**, 11 skips, no other failures. The original Run34/Run37 source pin is historical and intentionally does not match the current source; **do not edit, skip, filter, waive, or relabel it**. Any new failure/error must be diagnosed as a new regression and repaired in a separate review package.

No native inference or Redmi. No STEP2/B3/Body-JEPA/age/JEPA gate promotion. A GREEN full suite is not expected and must not be claimed unless the full unfiltered command truly returns zero.
