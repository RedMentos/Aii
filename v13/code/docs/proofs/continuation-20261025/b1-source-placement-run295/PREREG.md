# Run295 preregistration — frozen native B1 source-placement probe

Date 2026-10-25 UTC, before any Run295 native execution. Base verified Run294 checkpoint `75637b76b3520c444f79a1c8bae88ef69c1b6816` (branch-scoped, not main). Independent owner: only new `scripts/run295_b1_source_placement.py`, `tests/test_run295_b1_source_placement.py`, dedicated serialized native workflow and this proof. PR284 Runtime, PR293 output adapter, PR294 eligibility, `v13/prompts.py`, registered source/model/seed/cohort, native runner, original acceptance thresholds and Canon unchanged.

## Observed prerequisite

Run288 full 20-stage actual Linux-native raw artifact `12600061321` SHA256 `940a7a066521318137fb10a230bcd65969aeb3e440865fbd889efd59946026ca`: 16 PASS, four FAIL (readouts, memory-retrieval, output-adapter, cancel-restart). Memory retrieval had exact source delivery to B1, but B1 emitted a generic explanation without `400 Euro`; C3 did mention the saved value. Run291 genuine native source-first **system suffix** A/B remained NOT_SUPPORTED. Avoid repeating that same suffix.

## Frozen probe and primary source

Use the exact Run288 B1 native `messages` for synthetic `Projekt Kelmo16: Finanzrahmen?`, including `400 Euro` correction, reconstructed from unchanged canonical `v13.prompts.TEXT` and `v13.common.dumps`. The canonical compact JSON SHA256 of the full original two-message array MUST equal `54f859ca3667028b4ea83fbd91b46b4c5c85627868f795d1da3ed0e4c70d333c` before native inference; otherwise refuse. Original Run288 prompt bytes came from the registered native evidence, not a fabricated model response. Native role pinned `B1_DETAIL`, original answer cap 64, seed 13. Source, model and runner hashes must be reported.

## Diagnostic arms (sequential; no production integration)

- `baseline`: frozen exact original messages.
- `user_source`: same system and final question, but an additional explicit user-sourced correction message immediately before the question: `Earlier you corrected the financial framework of Projekt Kelmo16 to 400 Euro. This is your statement, not independently verified. Apply it only to that exact project and financial topic.`
- `system_plain`: same system and final question, with an explicit plain-language source summary appended to the system: `For Projekt Kelmo16's financial framework only, the saved operator correction says 400 Euro; this is not independently verified. Do not use it for other topics or projects.`

Run each arm on matching question, same-entity wrong topic `Projekt Kelmo16: Wer leitet das Team?`, and different-entity same topic `Projekt Kelmo17: Finanzrahmen?`. The system's `task_context.exact_request` is updated only for negative queries, while the original correction and its matched query remain fixed. All nine actual native generations are serialized with process unload between calls. Capture full outputs, exact prompt hashes, model/source hashes, runner metrics, failures and negative controls. No automatic approval or user-facing change.

Primary diagnostic: matching answer contains `400 Euro`; negative controls do NOT contain `400 Euro`. A passing arm is **PROMPT_INTERFACE_SIGNAL_ONLY** (not memory-retrieval gate PASS) because source presentation is changed. Native execution failure, missing source/model hash, changed baseline hash or leaked value => invalid or unsafe; preserve failed attempts. No native result may promote STEP2, B3, Body-JEPA, jepa_weight or whole V13. Redmi unmeasured.

## Sources and open question

Actual Run288 native raw artifact and Run291 negative paired native experiment (PR291), inspected 2026-10-25. The experiment distinguishes a small B1's inability to use structured source from a memory-selection failure. If a new arm passes, next preregister fresh held-out entities and integrate only behind an opt-in with exact source binding and original gate recheck; otherwise investigate constrained decoding/receiver rather than repeatedly changing prompt prose.
