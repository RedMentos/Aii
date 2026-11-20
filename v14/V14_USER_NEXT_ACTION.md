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
| source_HEAD | Release-base `14d7386484dfce6728aa404d89eae98403b4dba0`; candidate branch HEAD `d9d6e736a1191e3e8a12fc87b0c22b2b49defd57` (PR #2135, not release) |
| last_integrated_functional_change | PR #2135 candidate only: existing OnlineWorld consumer has atomic exactly-once checkpoint; NOT MERGED |
| local_test_result | LOCAL_LINUX reconstructed CPython 3.13: 8/8 PASS; exact PR-head GitHub Actions focused suite: 13 passed |
| ci_test_result | Focused 13 PASS; continuous-local-plasticity 49 PASS; combined online JEPA PASS; staged-runtime FAIL (20 failed, 218 passed, 10 skipped, 2 errors); staged integrated regression FAIL (1 test); safe-additive scope policy FAIL |
| phone_installed_sha | UNKNOWN — private owner-read issue #344 has no device receipt |
| phone_auto_update_verified | UNKNOWN_NO_LIVE_RECEIPT |
| device_model_comparison | NOT_RUN |
| proposed_model_change | NONE – erst anhand echter Tests |
| requires_user_action | NO – derzeit keine neue Aktion zur Fortsetzung der Repositoryarbeit |
| next_developer_action | Rebuild/review the complete hash-bound online-world candidate chain against current source; rerun staged runtime and integrated regression; continue P0 arithmetic/B1-B2 and whole-Canon integration |

**Bei jedem nachprüfbaren Ergebnis:** Stand, Branch/Commit, exakte Commands, Plattform, Messwerte und Rollback dokumentieren; Nutzerbedarf höchstens als konkrete Entscheidung. Bei Konflikten die neuesten tatsächlichen Messungen vor altem Text bevorzugen.


## Boss integration checkpoint — 2026-11-21 00:00 CET

- Verified release-base HEAD: `14d7386484dfce6728aa404d89eae98403b4dba0`. Candidate branch: `boss/v14-online-world-atomic-consumer-20261121`; exact PR head `e729a8c51df24fd6b60ea5d46115096f05630e27`, PR [#2135](https://github.com/RedMentos/Aii/pull/2135), DRAFT / NOT MERGED / NOT RELEASED.
- Implemented in the existing live consumer path `Runtime.online_world_update() -> OnlineWorld.update()`: predictor parameters, replay, counters, RNG state and processed T8 action IDs now share one atomic NPZ checkpoint; a per-home `flock` reloads the newest generation inside the lock. Failure before replace restores the previous checkpoint; an exception after replace reconciles from the committed action ID. Legacy v1 `cursor.json` is read-only migrated; old NPZ files without metadata remain readable. No frozen `runtime.py` edit, no GGUF/model swap, no Age or learning-permission change.
- Exact PR-head GitHub Actions: focused online-world + existing tests **13 passed**; existing continuous-local-plasticity workflow **49 passed**; combined online JEPA integration workflow **PASS**. Local reconstructed CPython 3.13 Linux reproduction: `py_compile` PASS, **8/8** crash/restart/concurrency tests PASS (two fork deprecation warnings).
- Full staged runtime is **FAIL**, not a pass: 20 failed, 218 passed, 10 skipped, 2 errors. The first common failure is the existing hash-bound `integrated_online_world_candidate_20261110.py` rejecting the changed `v13/online_world.py` SHA; downstream source-pinned candidates and phone migration then fail closed (`PARTIAL`). Do not relax source pins or refresh them blindly. The safe-additive workflow also fails its strict scope policy because this PR intentionally changes existing live modules; that is a policy gate, not a failed focused assertion.
- The old two-file crash window may already have caused historical duplicate updates; there is no reliable evidence to reverse them automatically. The new checkpoint protocol prevents new duplicates after migration.
- Private owner-read PIPELINE_STATUS issue #344 has no device comment/receipt. Installed SHA, updater state and Redmi runtime remain **UNKNOWN / REDMI_UNVERIFIED**. GitHub push is not deployment.

### Next developer action
Rebuild/review the complete hash-bound online-world candidate composition against the current source without modifying frozen Runtime or weakening pins; then rerun staged-runtime + integrated-regression and review PR #2135. Separately continue P0 C3 arithmetic/B1-B2 delivery and whole-Canon coverage. No user action or model swap is needed now.
