# Latest Core & Harness checkpoint — 2026-11-26

**User action: none.** No model download/swap, weight change, permission change, device action, UPDATE_REQUEST or manual Termux command was made. The release-development branch remains `gpt6/v13-private-remote-bridge-20261111 @ 8d93236c753f0194224c19edc7411d8d7082b1d6`. Core work below is a draft PR branch, **NOT_RELEASED**.

## Core Run 29 — Android companion action privacy and request integrity

- **Parent PR:** [#2528](https://github.com/RedMentos/Aii/pull/2528), based on #2513's explicit-consent `launch_app` / HTTPS `open_url` companion API.
- **Terminal retention fix:** the Android companion now redacts an `open_url` action's path/query/fragment from durable `request_json` and the legacy `package_name` column on `EXPIRED` or `CANCELLED`, retaining the public host and digest. A still-pending approval retains the target only for its visible local approval lifecycle. Malformed stored JSON falls back to a minimal redacted terminal envelope.
- **Additional integrity/privacy fix:** the companion previously accepted unknown top-level JSON fields even though the request digest covers only `capability + args`; such an unbound field could retain a duplicate private URL outside `args`. Commit `96e8c54f06c04aec4262a0751f2ee8f90184f6c9` now requires the exact 11-field request envelope before persistence. A regression test verifies the valid envelope and rejects an extra `unbound_private_url` field.
- **Tests added:** direct expiry, bulk expiry through `:pending`, cancellation, still-live pending non-redaction, malformed-JSON fallback with a fragment, helper-level exact-field validation, and a provider `submitLocked` negative-path test proving an unbound private URL is rejected before any durable row is inserted.
- **Workflow trigger repair:** commit `4df2dcaa67f5a8a1ce652af8c4ad965f07ffbffd` adds the #2528 head branch to the Android companion push workflow and its #2513 base branch to the pull-request filter. The branch had previously run only `offline-bridge-security`, not the Android Gradle/Robolectric workflow.
- **Exact CI evidence:** commit `63b05800ca08167b894f2a48e2a7e9ec73d0ee12` (including malformed-envelope/fragment test) has Android Gradle/Robolectric **SUCCESS** in run 45769108967; `offline-bridge-security` **SUCCESS** in run 45769108891. The emulator process-restart job from run 45769108967 was still **IN_PROGRESS** at last read. Follow-up commit `96e8c54f06c04aec4262a0751f2ee8f90184f6c9` has Android Gradle/Robolectric **SUCCESS** on exact PR-head run 45769580810; emulator process-restart remains **IN_PROGRESS**. Latest code commit `2526e24c8521707d7065fed28d495dde856245c6` adds a provider `submitLocked` negative-path test proving rejection before persistence. Its Android Gradle/Robolectric job is **SUCCESS** (run 45770231218), including that test; offline bridge security is **SUCCESS** (run 45770226583). Emulator process-restart remains **IN_PROGRESS** on run 45770231218. No emulator PASS is claimed yet.
- **LOCAL_LINUX:** Java 21 present. `gradle --version` is BLOCKED because Gradle is not installed; `ANDROID_HOME` and `ANDROID_SDK_ROOT` are unset. Local Android Gradle/Robolectric is therefore BLOCKED. `git ls-remote` also failed because this environment cannot resolve `github.com`; no full local Aii checkout/pytest ran.
- **TERMUX/REDMI:** REDMI_UNVERIFIED. Read-only private relay requests HEALTH #959 and PIPELINE_STATUS #960 were submitted; both remain open with zero `device_status` comments (**NO_LIVE_RECEIPT**). No phone action was attempted. Current installed SHA/updater state is therefore UNKNOWN; this candidate is not deployed.

## Other current Core integration risks

- **PR #2529** exact head `af8a00d5cc4edc85a769da3925c3d1ed3accec3b`: Python 3.13/3.14 focused jobs pass, but exact staged-runtime fails (**33 failed, 253 passed, 10 skipped, 2 errors**) and integrated-regression fails (**1 failed**). This is not a greeting assertion failure: multiple frozen candidate builders reject the changed `v13/runtime.py` SHA (expected `1a0f36bc…`; CI observed `6f4e023c…`), with dependent arithmetic/observer pins and two migration expectations also failing. A coordination comment with exact evidence was posted on #2529. Do not merge or claim the greeting is integrated until the source-pin chain is re-bound and the full staged suite passes.
- **PR #2525** exact head `9fdf321c9c14ab3b27d0d5947eaca443d5796df3`: Core Runtime/Callosum K/V-aware native receiver matrix checks **14/14 SUCCESS**. This proves the CI consumer path only. Its Perception base #2524 still has Python/staged/integrated failures; no real GGUF pair, trained latent utility, production B3 or Redmi proof is established.
- **PR #2512** tokenwise receiver consumer checks are green on its exact head, but its bounded lab cohort and native diagnostic are not production B3 or trained latent acceptance.

## Relevant research notes from the current ledger

- **R-090 — deadline-aware prefill:** SLOWeave/Sarathi-style chunked prefill is a scheduling design reference, not Android evidence. The next Core experiment should predict role cost from measured prompt tokens, warm/cold state and observed prefill rate, preserving a hard C3 reserve and both B1/B2 opportunities. Do not change installed cache flags or relax deadlines without a separate device trial and explicit approval.
- **R-091 — cross-architecture activation transfer:** the current native input-embedding ingress can prove a numerical receiver reaction only; it does not prove semantic transfer or a useful latent channel. Acceptance needs same-model prefill parity, source-disjoint task success, NO_MESSAGE/SOURCE_EXACT/zero/shuffle/row-shuffle/bidirectional controls and only then a trained low-rank bridge with retention/restart/rollback. Keep production B3 OFF.
- **R-107 — Future-Aware Recall:** potentially useful later for query-conditioned memory-cue utility trained from future outcomes, but the reviewed sony/far implementation is CC BY-NC 4.0 and its CUDA/H100 resource profile is unsuitable for this Android target. Conceptual reference only; no code, weights or dependencies reused.
- **Model alternative:** none proposed this run. No comparable native Redmi latency/quality/RSS measurements or fresh device receipt justify a model download or swap.

## Next internal actions

1. Verify the exact-head Android Gradle/Robolectric, emulator process-restart and offline-security jobs on #2528 commit `96e8c54f06c04aec4262a0751f2ee8f90184f6c9`; repair failures before QA review.
2. Coordinate with Boss/QA/JEPA on #2529's `runtime.py` source-pin cascade without editing another owner's files blindly.
3. Wait for Perception's exact #2524 repair, then rerun the full #2525 composed matrix. Keep B3 OFF until held-out task utility and negative controls pass.
4. Continue the P0 nontrivial B1/B2 → C4 → C3 correct-answer path; the greeting reflex is only a bounded trivial-input reflex.

**Deployment:** GitHub push is not deployment. No verified current Redmi installation receipt is available for these draft changes. **NOT_RELEASED / REDMI_UNVERIFIED.**


---

# Latest verified QA & Android checkpoint — 2026-11-23

**No user action is required.** The existing updater already reports the release-development head `aed1d2b826290c95c70356b5d8b864b5ef382be4` installed on Redmi. Do not rerun Termux, send another UPDATE_REQUEST, download models, or change permissions/weights.

The last private read-only device receipt (#115, 2026-11-22 23:19 UTC) reports Runtime/Dashboard RUNNING and UP_TO_DATE, but the last stored turn was 57.739 s / 41.627 s TTFT with 2 generated tokens; correctness is UNKNOWN. B1/B2 produced zero valid offers (4/4 and 2/2 native attempts failed with TIME_BUDGET); native latent exchange and model residency are not proven.

Current QA code, CI boundaries, pending checks, privacy limits and next steps are recorded in [QA_ANDROID_RUN10_20261123.md](QA_ANDROID_RUN10_20261123.md). Candidate PRs are not deployed. The installed app and user data were not changed.

---

# V14 – letzte verifizierte Entwicklung / nächstes sinnvolles Nutzer-Update

**Stand:** 20. November 2026. **Zuständig:** V14 Boss & Integration (QA verifiziert technische und lokale Angaben).  
**Zweck:** Bei der nächsten V14-Frage in ChatGPT **zuerst diese Datei plus neuesten GitHub-HEAD und Work Board prüfen**, dann konkrete Ergebnisse und nur erforderliche Entscheidungen nennen. Datei ist kein automatischer Push an das Handy.

## Letzter gesicherter Gesamtstand

- Aktiver V14-Master: `v14/V14_MASTER_BLUEPRINT_AND_RESEARCH_20261119.md`; ursprüngliche komplette V13-Anhänge aus Teil III wurden bei der letzten Editor-Runde bytegleich erhalten.
- Company-style Arbeitsauftrag, Live Workplan, Forschungsjournal und Canon-Überschriftenindex auf dem autorisierten V14-GitHub-Arbeitsbranch vorhanden. Das ist **Dokumentations-/Organisationsfortschritt, keine verifizierte laufende V14-App**.
- Bestehende Termux-Kommandos können weiter `v13` heißen. In der gelesenen aktuellen `v13/code/v13/operator.py` ist `:models` eine Read-only-Liste, `:import model ROLLE PATH` ist **ein mutierender Eingriff**. Safe isolierte Modellprobe / Angebot / UX wird erst entwickelt.
- Modell-Registry aus `v13/code/specs/models.json`: C3 LFM2.5-350M; B1 LFM2.5-1.2B; B2 Qwen3.5-0.8B. C3 230M ist als ältere Referenz in der Registry vermerkt. Die historischen Kandidaten und Lizenzen sind **kein aktueller Redmi-Vergleich**.
- Auto-Update-Push bis zum Gerät, native multimodale V14-/Latent-/MoE-Integration und reales kontinuierliches Gewichtslernen sind **NICHT durch diese Dokumentenrunde nachgewiesen**. Insbesondere GitHub-Push ≠ Android-Deployment.
- Die aktiven fünf stündlichen Aufgaben sollen in ihren Arbeitsfenstern selbst Code+Tests liefern und Boss/QA zur Integration übergeben; über tatsächlich erfolgte nächste Runs erst nach deren Ergebnissen berichten.

## Nutzeraktion aktuell

**Keine Aktion nötig, nur um die GitHub-Arbeitsaufträge fortsetzen zu können.** Keine neuen Termux-Befehle und kein Download auf Verdacht. Vor einer Empfehlung erneut tatsächliche Commit-/CI-/native Test-/Gerätestatus abgleichen.

Wenn QA den Auto-Updater auf dem Redmi unabhängig überprüft hat, darf ein freigegebenes, rücksetzbares Update künftig ohne neue manuelle Terminalbefehle erfolgen. Wenn die Geräteverbindung/Updater fehlt, **genau das** mitteilen und nur den kleinsten tatsächlichen notwendigen Schritt nennen.

## Wie eine nützliche Meldung aussehen muss

**Beispiel – nur als Format, nicht als echter Testbericht:** „Seit unserem letzten Gespräch hat das Team den B1/B2→C3-Consumer in Commit ABC integriert. Test X lief lokal (12/12), Redmi ist noch ungetestet. Eine Alternative zu C3 spart in echten Messungen Y MB, verliert aber auf Z Testfällen; willst du sie versuchsweise in einem getrennten Slot testen? Ich habe noch nichts an deiner Installation geändert.“

In der tatsächlichen Meldung niemals Beispielzahlen, Modell-Sieger, fehlende Testbelege oder imaginäre Befehle als Fakten ausgeben.

## Pflegepflicht bei jedem Checkpoint

| Feld | Aktueller Wert |
|---|---|
| source_HEAD | Nur nach aktuellem Remote-Readback einsetzen; Branch `gpt6/v13-private-remote-bridge-20261111` ist ein bekannter Anker |
| last_integrated_functional_change | UNVERIFIED |
| local_test_result | NOT_RUN in dieser Übergaberunde |
| ci_test_result | NOT_VERIFIED |
| phone_installed_sha | UNKNOWN |
| phone_auto_update_verified | NO |
| device_model_comparison | NOT_RUN |
| proposed_model_change | NONE – erst anhand echter Tests |
| requires_user_action | NO – derzeit keine neue Aktion zur Fortsetzung der Repositoryarbeit |
| next_developer_action | Board-Tickets V14-001/002/003/004 parallel umsetzen und testen; Boss integriert den ersten nachgewiesenen E2E-Pfad |

**Bei jedem nachprüfbaren Ergebnis:** Stand, Branch/Commit, exakte Commands, Plattform, Messwerte und Rollback dokumentieren; Nutzerbedarf höchstens als konkrete Entscheidung. Bei Konflikten die neuesten tatsächlichen Messungen vor altem Text bevorzugen.

## Core-Checkpoint 20.11.2026, 09:02 UTC — PR #2119 (noch nicht integriert)

- Basis-HEAD `d3ac638b04d166c4fe7611f3d314b1633b7036f8`; eigener PR-HEAD `6622218640c6859a628d96d7b63e3625ac46ba28`, Draft https://github.com/RedMentos/Aii/pull/2119. Signierte, aktionsgebundene Android-Companion-Receipts werden mit Ablaufzeit, STOP, Consent-Feld und SQLite-Nonce-Replay-Schutz geprüft. **Noch kein echter Android-Transport, keine unabhängige OS-Consent-Implementierung, keine T8-Lernpromotion.**
- LOCAL_LINUX: 1/1 PASS auf lokalem semantisch gleichartigen Kandidaten; exakt gepushte Bytes lokal **NOT_RUN**, weil GitHub-DNS im Container nicht erreichbar. Exakt-Branch CI-Workflow hinzugefügt, Ergebnis bei Checkpoint **PENDING**. Native Tokens/Redmi **NOT_RUN**. GitHub-Dateien nach Push readback bestätigt.
- **NOT_RELEASED**; installierter Redmi-SHA und aktueller Updater-Status nicht neu verifiziert. Keine Nutzeraktion nötig. Nächster Core-Schritt: CI prüfen; Android-seitig authentifizierte lokale Zustimmung und echte Companion-Verbindung implementieren, dann C5/Outcome-Konsument mit Replay-/Restart-/Negativtests, separat auf Redmi messen. Keine neue Modellinstallation oder Freigabe.
