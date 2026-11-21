# V14 – letzte verifizierte Entwicklung / nächstes sinnvolles Nutzer-Update

**Stand:** 21. November 2026. **Zuständig:** V14 Boss & Integration (QA verifiziert technische und lokale Angaben).  
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
| source_HEAD | `16f75fcaea9c83eb0e4b8136c0a2efdad70c1d19` (Release-Branch-Readback 2026-11-21) |
| last_integrated_functional_change | PR #2136 merged in `16f75fca`: PCM16 RAW-EAR → PerceptPacket → A4/C3-admission adapter; not yet called by normal Runtime/chat input, synthetic only |
| local_test_result | NOT_RUN — no full local repository checkout in this worker |
| ci_test_result | PR #2138 head `eb038f7e`: owner-read PASS, Python 3.14 staged startup PASS, offline bridge PASS; staged-runtime + integrated-regression IN_PROGRESS at readback; additive-only validator is not applicable to this modifying QA PR |
| phone_installed_sha | UNKNOWN — private HEALTH request #348 returned no device comment |
| phone_auto_update_verified | NO — no native receipt; no update attempted |
| device_model_comparison | NOT_RUN |
| proposed_model_change | NONE – erst anhand echter Tests |
| requires_user_action | NO – derzeit keine neue Aktion zur Fortsetzung der Repositoryarbeit |
| next_developer_action | Finish exact PR #2138 staged/integrated CI; Boss review/merge only after green; then obtain a fresh authorized PIPELINE_STATUS receipt and continue the actual Runtime audio/C3 consumer + B1/B2→C4→C3 path |

**Bei jedem nachprüfbaren Ergebnis:** Stand, Branch/Commit, exakte Commands, Plattform, Messwerte und Rollback dokumentieren; Nutzerbedarf höchstens als konkrete Entscheidung. Bei Konflikten die neuesten tatsächlichen Messungen vor altem Text bevorzugen.


## QA & Android Checkpoint 2026-11-21 — review/reproduction only; NOT_RELEASED

- Latest observed release integration base: `14d7386484dfce6728aa404d89eae98403b4dba0`, three commits ahead of the previously reported `d3ac638b`; merged PR #2120 added the PCM16 RAW-EAR producer. This is the latest observed base from merged/open PR metadata, not a claim that a new V14 runtime is installed.
- Device proof: a consented private `PIPELINE_STATUS` owner-read request was created as [RedMentos/Aiiii issue #343](https://github.com/RedMentos/Aiiii/issues/343). At this checkpoint it remained OPEN with zero device comments. Therefore `phone_installed_sha=UNKNOWN`, `phone_auto_update_verified=NO`, `REDMI_UNVERIFIED`. No repeat installer request, shell access, or device mutation was attempted.
- Updater source review: `termux_one_command.sh`, `source_updater.py`, `pipeline_agent.py`, and `runtime_deploy.py` were read back from the release branch. This was a source audit, not a full-repository update/rollback test. Existing code keeps exact-commit CI gating, bounded graceful stop, launcher backup, staged self-test and old launcher restoration; actual Redmi restart/rollback remains unproved.
- Exact PR CI findings:
  - PR #2123 head `0e9e96dc59fd6d8953c42df3635c0bc6e1b65d04`, run [44749530090](https://github.com/RedMentos/Aii/actions/runs/44749530090): integrated regression FAIL (30 failed, 208 passed, 10 skipped, 2 errors); staged-runtime FAIL. Root: changed `v13/runtime.py` not re-pinned through the integrated online-world and observer/postcommit builder chain; downstream migration reports PARTIAL.
  - PR #2129 head `9d9dcedad91e4be079d0556e07f6b10c9499523c`, run [44826449224](https://github.com/RedMentos/Aii/actions/runs/44826449224): integrated regression FAIL (16 failed, 222 passed, 10 skipped, 2 errors); staged-runtime FAIL. Root: changed `v13/fastforward.py` not re-pinned through the record-only controller guard/stage chain.
  - PR #2124 and #2126 staged-context runs completed SUCCESS ([44759061178](https://github.com/RedMentos/Aii/actions/runs/44759061178), [44769496804](https://github.com/RedMentos/Aii/actions/runs/44769496804)); their safe-additive workflow is not green, and this does not prove a live A4/Android audio path. PR #2130 head `3c2f6b2c...` had no workflow runs visible at readback; CI remains UNVERIFIED.
- LOCAL_LINUX isolated reproductions from source readback (reconstructed exact function/persistence order; not a full repository checkout):
  1. PR #2130 `TemporalOutcomes`: two instances load the same empty file; left then right writes; final JSON retains only right. Deterministic stale-instance lost update.
  2. PR #2130 `TemporalReadout`: same pattern loses the first event ID and parameter delta; final `seen=['right']`, WORLD weight `-0.1` instead of net `0.0`.
  3. PR #2123 consumer `OnlineWorld.update`: crash after model checkpoint but before cursor commit; restart replays the same action. Reproduction: `model_seen=1, cursor absent` after crash, then `model_seen=2, processed=['act_1']`; duplicate_learning=True.
  4. PR #2124 PCM16 producer → PR #2126 A4 adapter: producer packet is rejected with `ValueError: not an A5 acoustic observation`. The A4 adapter also accepted a forged packet without a receipt or current-consent argument and invoked `Attention.modulate` once.
- QA findings were posted to PRs #2123, #2124, #2126, #2129, #2130 and summarized on [whole-system issue #1984](https://github.com/RedMentos/Aii/issues/1984). Owners need to repair hash pins, exactly-once learning persistence, shared A5 packet/consent validation, and concurrency-safe temporal persistence before those candidates are integrated.
- No production model, GGUF, learned weights, Age/permissions, Termux app, launcher, SQLite, chat history, or phone state was changed. No full-repository LOCAL_LINUX suite was run in this environment; the container could not resolve GitHub for a checkout. No native Android, microphone, or Redmi benchmark is claimed.

**Next developer action:** re-run the exact staged-runtime/integrated-regression jobs after the owning branches repair their immutable pins; require transactional/idempotent learning and one canonical consent-checked A5 PerceptPacket before merging the audio/temporal candidates. Then obtain a fresh authorized private phone receipt before any release claim. **User action: none.**


## QA & Android checkpoint 2026-11-21 — latest-run CI gate; NOT_RELEASED

- Release integration HEAD read back from `gpt6/v13-private-remote-bridge-20261111`: `16f75fcaea9c83eb0e4b8136c0a2efdad70c1d19`. No release-branch mutation was made by this QA lane.
- A real release-gate weakness was found in `v13/code/v13/source_updater.py`: `ci_passed()` accepted any successful exact-SHA run for a workflow, so an older success could mask a newer failed/in-progress run. `pipeline_agent.run_cycle()` also reused the pre-stop CI result after a graceful chat stop.
- QA candidate PR #2138: [https://github.com/RedMentos/Aii/pull/2138](https://github.com/RedMentos/Aii/pull/2138), latest SHA `eb038f7e90ce5370547e338fad01bad40741c059`. It selects latest run_number/run_attempt per workflow identity, distinguishes recreated workflow IDs, fails closed on missing ordering metadata, and rechecks exact-SHA CI after graceful stop immediately before source mutation. It adds 9 run-order cases plus the stop-window regression.
- CI evidence on prior candidate `39f190e7666e41d69d2c5c6665da4a3ef24f0444`: owner-read PASS and Python 3.14 staged startup PASS; the exact logs show 27 source-updater tests and 32 pipeline-agent tests passing after fixture correction. On latest `eb038f7e`, owner-read PASS, Python 3.14 staged startup PASS, offline bridge security PASS, integrate-same-repo PASS; staged-runtime and integrated-regression still IN_PROGRESS at last readback. The safe-additive workflow fails by design because this PR modifies existing updater files; it is not the phone release gate.
- LOCAL_LINUX full repository suite: NOT_RUN (no checkout available). CI is the only execution evidence. This is not Linux-native runtime or Android proof.
- Private owner-read HEALTH request [RedMentos/Aiiii issue #348](https://github.com/RedMentos/Aiiii/issues/348) expired with zero device comments: `NO_LIVE_RECEIPT`. `phone_installed_sha=UNKNOWN`, `phone_auto_update_verified=NO`, `REDMI_UNVERIFIED`. No new installer command, remote shell, update, restart, rollback, model/weight, SQLite or chat-history mutation was attempted.
- PR #2136 is merged into the repo, but source readback shows `runtime.py` does not yet call `audio_perception_bridge`; this is a synthetic PCM adapter to A4/C3 admission, not Android microphone capture or a normal C3 prompt consumer. The full V14 audio/voice Canon path remains open.
- Next: finish exact PR #2138 staged/integrated CI; review with Boss before merge; then request a new private read-only device receipt only if the relay responds. Continue actual Runtime/consumer integration across the Canon. **User action: none.**
