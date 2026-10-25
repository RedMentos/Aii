# Intermediate GREEN candidate CI failed due test harness error — preserved

- Head `718cd072b4bf0ed9a2371b08af83570e2d0e642b`, run https://github.com/RedMentos/Aii/actions/runs/40184472149, job `121142227685`.
- Actual-source 3 tests: two PASS, one ERROR. Error `TypeError: _baseline() missing 1 required positional argument: 'root'` in the new test itself; not a production transform mismatch.
- Raw artifact `12595144354`, ZIP SHA256 `55b0620672958f68ba87760c0b15e65f0c5f9e62dab8c5e64d9d124d3780161e`.
- Corrected test invocation in commit `1b4adbbfd600b26d787671278e3f3aaade6b6568`, rerun pending.
- Original RED source drift remains preserved separately. No native proof or gate promotion.
