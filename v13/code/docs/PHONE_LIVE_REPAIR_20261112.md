# Phone update, live-health and diagnostic repair — 2026-11-12

The phone release channel remains `gpt6/v13-private-remote-bridge-20261111`.
Review started at `1d9a431d38c56eab541c5346e36b5df405aafb1d` and preserves
the concurrent active-source update-check work through `e17d4e2`.

## Repaired behavior

- Old exact-file sparse installs now materialize the complete committed
  `v13/code/v13/` package. This includes missing `common`, `runtime_deploy`
  and `diagnostic_push` dependencies and future package additions. Both
  relay startup and current/fast-forward dashboard update paths repair it.
- Update all can create or complete the fixed runtime source checkout for
  older installs. Its source/branch/local-edit checks, exact-commit CI and
  graceful stop remain prerequisites to switching the actual launcher.
- Runtime preparation, CI and deployment failures produce terminal error
  states and allow the independent dashboard to repair itself. Partial
  updates remain PARTIAL. A dashboard-only check retains the prior runtime
  state. Stopped managed chat is resumed on success or failure.
- An assistant-role `SOURCE_SYSTEM_REPORT` is a model failure. Pending,
  empty and old answers do not recover a previous incident. Automatic
  incidents contain technical enums, without the source report's text.
- Remote sends receive their session and byte offset atomically from the
  managed console. Rejected, interrupted or uncorrelated sends cannot pick
  up another local turn's response. Overlapping input is explicitly ambiguous.
  Plain console text still has no runtime turn ID or final event: visible
  text remains incomplete evidence, never a verified completed answer.
- Diagnostic attachments retain valid bounded native-probe summary JSON.
  Per-file and aggregate truncation/omission are explicit, and escaped
  Unicode fits the private relay's page bound. User-initiated sharing and
  existing local permissions are unchanged.
- All required workflows run for each phone release commit independently
  of an open pull request; a documentation checkpoint cannot strand an
  exact-SHA CI gate merely because no runtime file changed.

## Verification and limits

Focused phone/bridge/deployment regressions and the existing staged recovery
suites are run before publication. The real checked-out V13 CLI startup and
Store roundtrips for `Hi`, `Test` and `...` pass independently of mocked
deployment fixtures. Real headless Chromium at 390×844 verifies UI start,
send, live output, page reload, TXT history, four tabs and shutdown using a
disposable echo process, with zero page errors.

Synthetic tests do not prove native model quality or Android background
survival. A regular owner update request was acknowledged by the live phone
on the concurrent `e17d4e2` release; installation of this additional repair
must be verified separately after its exact-commit CI passes. Automatic
updates remain OFF if the local switch is OFF. No setting is silently enabled.

The existing B1 native TIME_BUDGET evidence remains unresolved until a new
on-device probe demonstrates success. SourceHandoff originals and the
STEP2/B3 negative gates and whole-system incomplete flags remain unchanged.
No model downloads, weight training, database deletion or arbitrary remote
shell are part of this repair.

Coordinator owned pipeline/deployment/bootstrap/workflow integration; separate
agents owned sparse migration, diagnostic bounds, and live-health/remote
correlation. A read-only reviewer reproduced two additional pipeline defects
(one CI failure blocking both targets and partial success reported UPDATED),
which are covered by new regression cases.
