# Context OS exact revision/hash pinning — preregistration (2026-10-29)

Parent review-only PR #1145 head `71fe7978d5dca6a134ced0c645346b291b97d92c`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## Problem
`context_os.exact_spans` preserves bare numbers, URLs, quotes and code but does not necessarily pin a version token embedded in an identifier (e.g. `model-v1.2.3`) or a source digest `sha256:<64 hex>` if unquoted. In a long older turn, `compress()` may discard those source-critical identifiers while claiming exact source was kept. This violates the Context OS exact-span contract.

## Frozen tests before code
1. Long source with `model-v1.2.3` and a 64-hex `sha256:` digest late in the turn compresses only if both identifiers are preserved verbatim in output and exact_spans.
2. Standalone `v1.2.3` is an exact span; an explicit query containing it triggers exact-need restoration.
3. A long plain prose source without identifiers remains compressible; existing numeric/URL/quoted/code spans and oversized/unbalanced fallback remain unchanged.
4. All existing `tests.test_context_os`, `tests.test_context_os_append_invalidation`, `tests.test_context_os_source_invalidation` (if present) stay green.

Implement bounded explicit version and SHA256-like identifier recognition before generic numeric regex; overlong/many spans fall back to RAW using existing caps. No learned policy/age/cache authority, no model calls, no native/Redmi proof, no registered model/seed/cohort/source pin changes. This is software-only Context OS integrity.
