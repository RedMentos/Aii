# Boss integration handoff — 2026-11-11 12:45 Europe/Berlin

## Exact verified upstream state

- Parent #1767 commit `973cede629f8901d7725fede790e21067eabb191`: C5 shadow → fake Android Notes → persistent WorldJEPA replay → C3 speech intent (renderer OFF).
- GitHub CI on #1767 **FAILED**: speech + E2E `3 failed, 17 passed`; composite `1 failed, 31 passed`. Root causes in actual job logs: `SpeechCoordinator.configure()` cleared pending queue on initial trusted renderer attachment; replay ablation was invoked with only 4–5 note tasks and rejected insufficient disjoint old/new source support.
- Latest concurrent review branches at audit: #1769 (Core operator loop `55b24739`), #1768 (Perception RAW EAR A5 `fe74e7ff`), #1770 (JEPA chronological replay `653fd678`), #1766 (SQLite T8 `2de3c8f1`). They are NOT merged into this branch. #1668 team plan remains 5 active jobs, additional specialist domains assigned by ownership.
- Reviewed actual root `AGENTS.md`, `v13/AGENTS.md`, Canon v10.16.1, `v13/ROADMAP.md`, `v13/code/BUILD_STATE.json`, `v13/code/docs/HANDOFF_CURRENT.md`, `v13/NUTZER_ENTSCHEIDUNGEN.md`, current #1767 source and tests.

## This repair PR

- `v13/code/v13/speech_intent.py`: first trusted renderer configuration preserves queued text; reconfiguration still stops/cancels previous active renderer. This fixes the upstream speech queue test without enabling any native audio. Core owns eventual queue API; this is a scoped Boss integration repair only.
- `v13/code/v13/android_c5_goal_replay.py`: reject `count<18` before filesystem creation rather than making false replay-retention claims or weakening disjoint train/old holdout/new requirements.
- `tests/test_android_c5_goal_replay.py`, `tests/test_c5_goal_c3_speech_e2e.py`: run real synthetic 18-note cohorts, preserve expected task count, assert underpowered cohort rejected.
- `.github/workflows/v13-boss-c5-c3-speech-e2e.yml`: explicitly run repair branch on push.

**Evidence boundary:** These edits were committed via GitHub API. A completed CI result for the exact repair head was not available at initial check; no local full-suite or Redmi hardware result is claimed. The 18-note threshold is a fixture precondition, NOT proof that every possible 18-note state yields enough unique input-action cohorts; exact-head CI must decide. No model-generated permission approvals, network egress or live Android control.

## Completion ledger (CODE / WIRED / SYNTHETIC / ANDROID / ACTIVE)

| Scope | Code | Wired | Synthetic | Redmi | Active |
|---|---|---|---|---|---|
| A0-A5 visual/context | partial | staged | partial | NO | limited |
| RAW EAR / multimodal | #1768 candidate | A5 packet candidate | tests claimed by owner, independent review pending | NO | OFF |
| B1_DETAIL/B2_GIST/B3 | partial | exact/source paths | partial | NO | frozen inference |
| C2/JEF/C5 | partial | typed shadow + deterministic controller | partial | NO | shadow only |
| C3 language/speech | queue and OFF renderer | C5 completion→speech intent | CI repair pending | NO | text only |
| T8/world graph | SQLite source adapter candidate #1766 | staged to JEPA | owner tests, review pending | NO | partial |
| WorldJEPA/EMA/replay | trainable weights and checkpoints | fake Android replay + T8 candidate | previous proof; combined repair CI pending | NO | shadow |
| ANDROID_BACKGROUND_CONTROL | Core #1769 candidate | approval-bound fake companion | partial | NO | OFF |
| ANDROID_UI_CONTROL | typed broker + simulator | synthetic UI | partial | NO | OFF |
| VOICE_AUDIO | PCM + RAW EAR + queue separate | A5 #1768 candidate | partial | NO | renderer OFF |
| SELF_OPTIMIZATION | AG8 proposals, mini-risk-head | no full target optimizer | partial | NO | OFF |
| ACTUAL B1/B2/C3 PERMANENT WEIGHTS | design / separate trainer candidates | not deployed | unproven integrated | NO | OFF |
| CROSS_ORGAN_GRADIENTS | design #1741 | not runtime wired | NO | NO | OFF |
| TECHNICAL_OS_SANDBOX | broker contract | OS isolation absent | partial | NO | OFF |
| BEHAVIOR_JUDGE | trainable 10-feature adviser | fake Android | tested in #1757 | NO | advisory |
| REMOTE_MAINTENANCE | #1756 signed staging candidate | not native applied | partial | NO | OFF |

Canonical and full-scope completion flags remain **false**. STEP2 UTILITY_FAIL / B3 L1 FAIL remain unaltered.

## Concrete next non-overlapping owner deliverables

- **Core:** #1769 operator loop must become an actual approved-intent→fake companion→committed action-outcome integration used by the C5 demo, then separate Android Companion APK permissions and native API-first launch/observation path. Also actual trainable B1/B2 target adapter reader.
- **JEPA/Memory:** review #1770 chronology against #1766 committed SQLite T8, then implement source-admitted T8→persistent target adapter with before/after holdout and restart, not only shadow replay.
- **QA/Android:** instrument one-shot approval, revoke/stop, forged approval, hidden-memory/network attempt and Android permission lifecycle; no native success until Redmi proof.
- **Research/Perception:** wire #1768 RAW EAR A5 source packets to a zero-authority C3 perception consumer, with timestamp, PCM hash and nonverbal cue retention; no microphone claim.
- **Boss:** resolve this exact-head CI, integrate Core #1769 operator and JEPA #1770 after code review into ONE runnable C5/T8/World/C3 synthetic candidate, then verify source and speech provenance; don't blindly merge independent PRs.

Unfilled specialty roles (B1/B2 dedicated, JEF/C3 dedicated, Memory/Sleep dedicated, Android permission security, Voice decoder, independent adversarial audit) are *backlog ownership* spread across five active jobs, not additional running agents. Android Redmi Note 10 Pro is the primary product and acceptance platform; PC is optional and out of current delivery path.
