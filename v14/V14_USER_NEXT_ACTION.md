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

## Research & Perception — 2026-11-20, PR #2122 (noch nicht integriert)

- Auf Branch `research-perception/v14-model-budget-audit-20261120` liegt ein **read-only** CLI für die bestehende Modellregistry mit deklarierter Dateigröße, Revision und Lizenz. Lokal unter Linux: `python -m unittest -v test_model_budget.py` **4/4 PASS**; `python -m py_compile model_budget.py` **PASS**. Dies sind keine Modell-/Native-/Redmi-Messungen.
- PR: https://github.com/RedMentos/Aii/pull/2122 ; Stand auf diesem Branch vor unabhängiger QA: `687cc7eb99238641808546436742c65651f1a813` (Board-Checkpoint). **NOT_RELEASED / REDMI_UNVERIFIED**. Die statische Größe beweist weder RAM-Eignung noch TTFT oder Qualität. Keine Gewichte, Modelle oder Gerätefreigaben verändert.
- **Nächster Entwickler-Schritt:** QA soll den exakten PR-SHA neu testen und danach tatsächliche PSS/TTFT/Qualitätsvergleiche auf autorisierter Hardware anstoßen; Boss prüft Integration. **Nutzeraktion: keine.**
