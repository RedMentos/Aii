# Isolated native firing and approval reader review

The live runtime remains frozen. Approval reader transformation is applied first, then the request-scoped firing transformation. The resulting four-module patch compiles and passes the standalone and merged firing regressions.

Review reproduced a real file truncation between the initial inventory check and native header read. The prior candidate raised `struct.error`. Its isolated helper now imports struct before parsing and catches that exception as `INVALID_REQUEST_ROW_MAP`; the regression actually truncates the fixture file and requires no observed fact claim. The old patch, reports and initial registration remain preserved.

43 tests passed: 17 standalone firing, 20 merged/preparation and 6 packaging checks. The packaging checks create, CRC/hash verify, extract and execute the reader and merged tests. Three minimal approval-reader baseline fixtures were added to the phone installation manifest. This does not change the earlier 1125-test phone snapshot result.

The new diagnostic CLI is registered against the installed C3, launcher, shared libraries, all 121 live runtime sources, both isolated helper bytes and the merged module hashes. It will produce 18 paired Exact/Trace/Combined observations with audit off/on, including a near-miss and repeated prompt. Its one slot is an explicitly authored, always-threshold-eligible nonzero row with entity guard disabled. It is a protocol/source-binding test; neither useful learned recall nor a selective omission or mobile quality test. No native inference has run.

The valid registration is `../night-firing-native-diagnostic-v2-20261011/registration.json`. The original registration was superseded before inference; its bytes and SHA are retained in `superseded-registration.json`. Live module changes must wait until the frozen SourceHandoff cohort ends. Parent controls the serialized native queue and GitHub/ZIP publication.
