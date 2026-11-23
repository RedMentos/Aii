# Run70 preregistered C3 source-only decision vs typed-answer JSON-schema control (2026-10-31)

**Owner:** GPT-6 automation continuation, independent review-only child of Run68 #1428 exact `4b14ca3bea9b4ddf717aefb7d04408d4b59921b5`. No Run68/69 cohort or model changes. The user wants functional utility, not merely a formatter-copy success.

## Research question
Run68 native constrained schema achieved 6/6 strict formatting, **but the correct typed JEF action was already present in its prompt**. Does the pinned C3 model compute the correct A/B/NONE from two actual source-verified human policy/option texts **without** seeing that typed action? This is a source-reasoning *diagnostic*, not a new safety decision-maker or STEP2/AGI gate.

## Frozen cohort and input generation (before code)
Seed **743**, six **new disjoint** synthetic projects. Same source grammar, SourceRef/real Store admission and deterministic JEF oracle as Run68, distinct project identifiers and source texts; validate disjointness against Run68 and P2X original calibration. Fixed table rows, format `domain; first attribute/unit; second attribute/unit; required flag; policy(max1,max2,flag); A(v1,v2,flag); B(v1,v2,flag); oracle`:

1. river ferry; fare/credits; boarding window/slots; insured; (190,25,true); (150,22,true); (140,28,true); **A**
2. planetarium tours; seat quota/places; entry window/ticks; accessible; (160,20,false); (175,18,true); (150,19,false); **B**
3. forest cameras; power quota/units; startup window/beats; weatherproof; (110,12,true); (100,13,true); (120,11,true); **NONE**
4. school robotics; kit quota/kits; setup window/steps; reusable; (200,18,false); (180,17,true); (150,21,false); **A**
5. island water; volume quota/litres; delivery window/intervals; filtered; (280,22,true); (250,21,false); (260,20,true); **B**
6. archive boxes; load quota/points; transit window/cycles; sealed; (90,10,true); (95,8,true); (80,12,false); **NONE**

## Prospective arms and controls
For each source, construct an authenticated current USER and two human-source records in real SQLite, use original JEF typed envelope only as the **frozen oracle/source verifier**. Two C3 arms in balanced alternating order, both llama.cpp `json_schema` constrained exactly `{"type":"object","properties":{"action":{"type":"string","enum":["A","B","NONE"]}},"required":["action"],"additionalProperties":false}`:
- **TYPED_SCHEMA:** Run68-style formatter-copy prompt with typed JEF action present. Positive interface control.
- **SOURCE_SCHEMA:** same exact current/policy/sheet source texts and SourceRef hashes but **remove** `typed_jef_action` from model-visible payload; system prompt explicitly asks to select A/B/NONE by comparing numeric maxima and required boolean. No hidden oracle or answer leak. Compare payload/source hashes and inspect for leakage.

Pinned Linux-native C3 model SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, llama-server SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`, temperature **0**, max tokens **32**, seed **743**, exact six rows, 12 calls, alternating arm order. No retries that retune results.

## Prospective scoring and claims
Strict `decode_schema` only (unique JSON keys, no extra fields, valid A/B/NONE, <=1024 bytes). Count exact action vs deterministic JEF oracle. Registered **diagnostic** threshold: SOURCE_SCHEMA >=4/6 and TYPED_SCHEMA >=4/6; also report delta and all per-case confusion. A failure is `SOURCE_REASONING_DIAGNOSTIC_RED` retained; success is `SOURCE_REASONING_SMALL_SYNTHETIC_PASS` and **not** proof of robust reasoning, safety, multi-turn transfer, or system utility. No posthoc scorer adjustment, no promotion of STEP2/B3/Body-JEPA/World-JEPA/age/jepa_weight or whole V13. Retain original failed runs, hashes and raw.

## Evidence and operational safety
Software prereg/fixture tests and privacy first; native under existing serialized `v13-native-c3-ag12-20261030` group, pinned installed model and runner, actual FINAL/process reaped, no output/tool/learning, closed Store, bounded raw. Workflow records original HEAD, PINS, stage exits, native raw JSON reports with synthetic source only, SHA256SUMS and original ZIP. Independently verify original raw before any claim. The original Run68 6/6 formatting result remains immutable and separate. Native run may not start until source fixture/tests software GREEN and exact prereg SHA remote verified.
