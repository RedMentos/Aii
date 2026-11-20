# V14 – letzte verifizierte Entwicklung / nächstes sinnvolles Nutzer-Update

**Stand:** 20. November 2026, 23:xx CET. **Zuständig:** V14 Boss & Integration (QA verifiziert technische und lokale Angaben).  
**Zweck:** Bei der nächsten V14-Frage in ChatGPT **zuerst diese Datei plus neuesten GitHub-HEAD und Work Board prüfen**, dann konkrete Ergebnisse und nur erforderliche Entscheidungen nennen. Datei ist kein automatischer Push an das Handy.


## Neuester verifizierter Checkpoint — 20.11.2026

- **Release-Branch:** `gpt6/v13-private-remote-bridge-20261111` steht aktuell auf `14d7386484dfce6728aa404d89eae98403b4dba0`. Dieser Stand liegt nach dem vom Nutzer genannten `d3ac638b...` und enthält den Integrations-Commit zu PR #2120.
- **CI:** Für `14d7386484...` liegt in diesem Readback kein vollständiger exakter Push-Workflow-Satz vor. Für `d3ac638b...` war im API-Readback mindestens ein Push-Run `V13 private owner-read Termux bootstrap` fehlgeschlagen (Dashboard-Child resumed, Heartbeat blieb leer). Daher weder den aktuellen Branch als vollständig release-geprüft noch als installiert bezeichnen.
- **Neuer Codekandidat:** Draft PR #2130, Branch `boss/v14-temporal-outcome-semantics-20261120`, Head `605427de38784334e664f576017588cd2e7f806b`. Er konsolidiert den gestapelten temporalen V14-Kandidaten direkt auf dem aktuellen Release-Basisstand und korrigiert positive/negative Outcome-Semantik.
- **Lokaler Test:** Python 3.13.5, Linux x86_64, isolierte exakt ausgelesene Quell-/Testdateien: `py_compile` PASS und 18/18 Unit-Tests PASS. Kein Full-Repo-Test, keine CI-Bestätigung, kein Termux- oder Redmi-Test.
- **Echte Produktwirkung:** temporale Readout-Logik kann korrekte, falsche, frühe, späte und ausgelassene Outcomes getrennt bewerten. Der Readout ist ein kleiner persistenter Skalar-Head, kein JEPA-Encoder und kein produktiver B1/B2-Weight-Update. Es gibt weiterhin keinen authentifizierten T8-Store/World-Produzenten und keinen Runtime-Consumer.
- **Redmi:** `REDMI_UNVERIFIED`. Die aktuellen privaten Owner-Read-Anfragen lieferten bis zum Checkpoint keine Antwort. Die letzte verfügbare Gerätebeobachtung ist veraltet; kein aktueller installierter SHA oder Runtime-PASS ist belegt.
- **Audio/Perception:** Der aktuelle Branch enthält einen PCM16-RAW-EAR-Produzenten, aber der offene A4-Adapter erwartet ein anderes Packet-Schema. Kein belegter A5→A4→Runtime-Durchlauf.
- **Keine Geräteänderung:** kein Modell-/Weight-Download, kein produktiver Modellswap, keine Änderung von Age, Berechtigungen, Updater oder Handy-Daten.

**Nutzeraktion:** keine. Kein neuer Termux-Befehl und kein Modelldownload nötig. Erst bei einem nachweislich nötigen Geräte-Test eine konkrete, minimale Aktion nennen.

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
| source_HEAD | `14d7386484dfce6728aa404d89eae98403b4dba0` auf `gpt6/v13-private-remote-bridge-20261111` |
| last_integrated_functional_change | PR #2120 im Branch-HEAD enthalten; RAW-EAR-Producer-Code vorhanden, A4/Runtime-Consumer nicht belegt |
| local_test_result | PR #2130 isoliert: py_compile PASS, 18/18 Unit-Tests PASS; kein Full-Repo-Test |
| ci_test_result | PR #2130 pending; aktueller Release-HEAD ohne vollständigen exakten Push-CI-Beleg |
| phone_installed_sha | UNKNOWN — kein aktueller privater Owner-Read-Beleg |
| phone_auto_update_verified | NO CURRENT RECEIPT |
| device_model_comparison | NOT_RUN |
| proposed_model_change | NONE – erst anhand echter Tests |
| requires_user_action | NO – derzeit keine neue Aktion zur Fortsetzung der Repositoryarbeit |
| next_developer_action | PR #2130 CI prüfen; authentifizierten Store/World-T8-Produzenten und echten Runtime-Consumer bauen; offene Runtime-Freeze-/Audio-Schema-Konflikte beheben |

**Bei jedem nachprüfbaren Ergebnis:** Stand, Branch/Commit, exakte Commands, Plattform, Messwerte und Rollback dokumentieren; Nutzerbedarf höchstens als konkrete Entscheidung. Bei Konflikten die neuesten tatsächlichen Messungen vor altem Text bevorzugen.
