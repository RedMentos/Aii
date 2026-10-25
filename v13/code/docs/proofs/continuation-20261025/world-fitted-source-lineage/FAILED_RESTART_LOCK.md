# Intermediate GREEN candidate test restart lock error — preserved

- Head `9dadbacc7656af5bb878134727733bc3462ddc94`; CI run https://github.com/RedMentos/Aii/actions/runs/40184910612, job `121143554642`.
- 34 tests: 33 PASS, 1 ERROR. All source-revocation, action-tamper, model-tamper and synthetic compatibility tests passed; the new restart test attempted a second `Store(home)` while the original Runtime still held the exclusive owner lock, correctly raising `RuntimeError("V13 läuft bereits mit diesem Speicher")`.
- Raw artifact `12595224916`, ZIP SHA256 `fe164aa69ab0f795eea3aa140f40a425ce5ba85850b52f5fc5470b6fc1fba8d8`.
- Test-only fix `0005a96a276ca7eb88d9ea32ac4df220bbf71f4b`: close the original Runtime before opening the same home. No production Store lock weakening.
- This is not native inference, Redmi or whole-system proof.
