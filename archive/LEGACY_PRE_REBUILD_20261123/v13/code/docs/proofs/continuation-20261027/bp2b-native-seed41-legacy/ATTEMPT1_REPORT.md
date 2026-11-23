# BP2b seed41 legacy native attempt 1 — preserved negative evidence, 2026-10-27

GitHub Actions run `40505978531`, exact HEAD `32dbc942ce9c6736aeef57e190174bb647aeea4f`. Registered source/model/cohort unchanged. Original raw artifact ID `12735285952`, ZIP SHA256 `90f1318c1b33ffb07f0b9e9adefcc325331a7b463446eccaff8c80ccb5f6005e`, ZIP CRC PASS. Original ZIP privately backed up to ChatGPT Library `/V13-Checkpoints/2026-10-27/BP2b-Native-Seed41-Legacy/attempt1-ENV_IMPORT_FAIL-40505978531.zip` and byte-exact readback verified.

- SOURCE_EXIT=0: exact 2,340,697,936-byte public model plus seven metadata files passed `FULL_FILE_HASH_PASS`.
- ENV_EXIT=1: pinned CPU PyTorch 2.14.1, Transformers 5.20.2, PEFT 0.21.2, GGUF 0.19.0 installed and `pip check` passed, but inline import `from v13.body_jepa import BodyJepaTrainer` raised `ModuleNotFoundError` because workflow did not set `PYTHONPATH=v13/code`. This is a CI harness path error, **not** a native training failure or model incompatibility.
- NATIVE_EXIT=99: intentionally skipped; no model loaded, no adapter, no utility measurement. PRIVACY_EXIT=0 CLEAN.
- Fix isolated to workflow environment path and pre-model HF/GGUF API smoke in commit `7243d71f51ff53587b5062953a7d79f786648e87`. Retry Actions `40506115941` was started, **result pending at this checkpoint**. Never replace or erase attempt 1.

Next: inspect retry's exact original artifact and distinguish ENV/API failure, resource failure, real native train failure, or valid single-arm result. Preserve STEP2/B3/BJ1/jepa/Q4/Redmi/full-scope negative gates regardless.
