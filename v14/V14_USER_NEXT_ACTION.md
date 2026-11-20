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
