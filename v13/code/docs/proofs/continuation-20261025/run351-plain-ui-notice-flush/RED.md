# Run351 observed RED — pending plain-chat notices stranded (2026-10-25)

- Preregistered `78ace4eeaf6d213f0c89a9580ee5cbfa752a78f4` before tests/source. Exact RED head `383fb8926a4afdabf11b6a7ca7065d6dc703ab9b`.
- GitHub Actions `40225610825`, job `121266192642`: **7 real source-only tests, 5 PASS, 2 expected RED**. New render-thread tests prove a notice queued while typing remains absent after typing ends unless another notice arrives; FIFO queue similarly remains invisible. Immediate notice and Run214/Run89 persistent chat regressions PASS. No native/phone execution.
- Raw artifact `12611451279`, downloaded ZIP SHA256 `e56ebdf738a13d530cd0136c4530a8efa79299e6a1ca4c9dd6e705777dc1ba44`, CRC PASS, 3/3 internal manifest hashes verified, embedded HEAD matches. UI source SHA256 `7fe8913c709fe36ca8dc777b8a85fc90be9ed610cbed9924f120cb8413bdc097`. Privacy step skipped due expected RED, not claimed CLEAN.
- Private durable backup verified: `/V13/checkpoints/2026-10-25/V13_Run351_Plain_UI_RED_raw_shae56ebdf7.zip`.
- Next: synchronize the held queue and drain it on render ticks after typing ends; verify no output while actively typing, no duplicates, FIFO and persistent chat regressions. Preserve original gates.
