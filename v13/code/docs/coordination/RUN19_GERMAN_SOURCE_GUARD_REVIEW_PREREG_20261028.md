# Run19 independent German source-reader adversarial review — preregistration, 2026-10-28

**Parent:** Run17 draft PR #928 exact metadata head `23756d35c02bb4d2742b524ca97f0ddaf0372887`; source-proven Run17 `9f115579d584e30899e12eeec7df71fa30fa4504`, Actions `40702568275` SUCCESS, 17 focused/2466 full OK (1 skip), raw ZIP SHA256 `a68034c923197b7275e70f0e3ea6a5d78a3c71582e05df15721aa0ebd52fd2d1` privately byte-verified. Run18 balanced controls and Run16 native pilot are separate owners.

**Independent counterexamples (not native):**
1. A German `Projekt Nerava` source can additionally mention English `Project Quasar` and the Run17 German-only project cue misses the cross-project contamination.
2. A current RULE request can contain exact `Option A:/B:` values, yet Run17 can be instructed to read a stale historical supplier sheet instead; current values must win or refuse.
3. A historical rule or sheet record may be newer than the current request, or sheet older than the rule note; Run17 does not bind source order. Missing or malformed source sequence must fail closed.
4. A malformed partial current `Option A:` must not be bypassed by reading historical options.

**Registered fix:** on an isolated review branch only, update the Run17 SHADOW parser to recognize `Projekt|Project` project cues, require exact current option-source precedence, and require integer monotonic event `seq` from the authoritative source reader (old < sheet < current; RULE option source=current). Update original Run17 synthetic source fixture helper with explicit event sequences; add a new independent Run19 adversarial test module and source-only CI. Keep Runtime, frozen English eligibility, TP/s27 and Run15/Run18 fixtures, model/source/seed hashes untouched. No F1/F5 adapter is authorized by a self-asserted `verified=True`; live integration needs actual Store.read_source plus revocation revalidation.

**Proof:** RED-first adversarial tests must fail before guard patch, then pass; full pinned-dependency suite, compile, privacy/diff, raw artifact with SHA256SUMS, private readback. No native model call, no gate promotion. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; whole V13 incomplete. Owner Run19, budget UNKNOWN.
