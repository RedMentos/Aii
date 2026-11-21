# Immutable pre-v2 V14 T8 source backup

Created on 2026-11-21 before integrating the paginated, full-SourceRef T8 authority into V14's source-of-truth modules.

Original branch: `gpt6/v13-private-remote-bridge-20261111`
The files below are byte-for-byte copies read from that branch before any update. Do not edit these backup files.

| Original path | Original Git blob SHA |
|---|---|
| `v14/learning/t8_store_authority.py` | `07df849bc5e14377dd994ad86fc54aed4e77b810` |
| `v14/learning/t8_temporal_bridge.py` | `ef1cc211fd41bc04932112374e04e448d7508526` |
| `v14/learning/temporal_outcomes.py` | `53d009018f7461aab049727f27d54ceb9aa1429b` |
| `v14/learning/temporal_receiver.py` | `49dcc2c8dc70cfc446d4599d73f236a73f985249` |
| `v14/learning/test_t8_store_authority.py` | `bd861e9e1cc23ffae7df3d9622153804147f6a1b` |
| `.github/workflows/v14-t8-temporal-bridge.yml` | `b6b5755d2f5ed4c133bd230b38036cd4dca962c9` |

The next implementation keeps V14 as the full source of truth; V13 receives a package-relative deployable copy. V14 modules are not replaced by compatibility shims.
