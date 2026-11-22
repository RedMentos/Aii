

### Run 20 follow-up — current QA and device blockers (2026-11-22T21:38:00Z)

- QA hat den alten `memory.py`-Pin auf einem sauberen Stack in PR #2383 (Head `71df3dc`) neu gebunden. Die nächste CI-Stufe scheitert jetzt an nachgelagerten Builder-Hashes: `termux12` expected `27fe2305…`, actual `6a72d48d…`; `stage_integrated` expected `c6c6bed3…`, actual `d6ca01fe…`. Zwei-Checkout-Migration bleibt PARTIAL. QA muss die Abhängigkeitskette bottom-up fertigstellen; JEPA ändert keine QA-Dateien.
- PR #2372 bleibt bei `50e3c8d`, DRAFT / NOT_RELEASED. Temporal-CI `45072681648` war beim letzten Readback noch IN_PROGRESS. Der vorherige Head hatte die Prompt-/700-Zeichen-Assertions bestanden und nur eine veraltete Note-Assertion verfehlt.
- Private `V13OBS` #115 ist weiterhin nur 5-turn `LOCAL_METADATA_ONLY`: B1 4/4 fehlgeschlagen, B2 2/2 fehlgeschlagen, 0 gültige Offers, 0 C3-Delivery; letzter C3 2 Tokens / 38.945 s Prefill; Prompt-Inklusion/Semantik und native Latents unbewiesen. Neue read-only Relay-Issues #621–#623 haben noch keine `device_status`-Antwort: `NO_LIVE_RECEIPT`.
- **REDMI_UNVERIFIED.** Installierter Basis-SHA bleibt `aed1d2b` / Auto-Update UP_TO_DATE; PR #2372 ist nicht installiert. Keine Nutzeraktion, kein manueller Befehl und kein Update-Request.

**Nächster interner Schritt:** exakte Temporal-CI abwarten, QA downstream pins korrigieren lassen, danach staged/optimizer/integrated neu testen. Nicht rebasen, solange QA/Boss-Matrizen nicht grün sind.
