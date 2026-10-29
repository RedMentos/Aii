# JEFBridge operator current-session isolation — preregistration 2026-10-29

Parent JEF F1/F5 integration checkpoint
`59943da7b0d835988637f095f5ec671fdf4a6985`.
No model/weight, age, registered cohort or Canon change.

## Observed operator gap
`:jef last` currently retrieves the globally latest `JEFBridgeTurn`
packet, including packets belonging to other chat sessions. This can
expose another session's source-linked offer/decision metadata.
`:jef outcome <Event-ID> <score>` also accepts a foreign event ID
and may update the global JEF offer-utility prior from a different chat.
The explicit operator must be current-session bounded before either read
or feedback; the underlying JEF learning algorithm is unchanged.

## Frozen tests
- Two actual Store sessions with JEFBridgeTurn packets: `:jef last`
  shows the current session's packet even when the foreign one is newer.
- Foreign-only packet returns JSON null in current session.
- Foreign/unknown outcome IDs are refused **before** JEFBridge.outcome
  is invoked or learned policy state changes.
- Current-session outcome remains usable under existing explicit
  operator authority; no native C2/C3 calls.
- Existing JEFBridge offer learning, source admission, age and operator
  tests remain passing.
- Pinned software CI, Canon blob, privacy/diff/compile, closed original
  SHA256SUMS. No STEP2/B3/Body-JEPA/LP3/World-JEPA/Redmi promotion.
