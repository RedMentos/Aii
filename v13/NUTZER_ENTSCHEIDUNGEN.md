# Nutzerentscheidungen (RedMentos)

Dauerhafte Ablage, weil `code/docs/USER_DECISIONS_AND_OPEN_QUESTIONS.md` von `v13/verification.py:122` neu erzeugt werden kann.
Gilt vor abweichenden Stellen im Blueprint, bis der Nutzer etwas anderes sagt.

## 2026-10-09 (Thread „Übergabe komplett sichten“, Antwort auf SICHTUNG §5)
Wortlaut: „es sin viele modelle in einem des is eig alles definiert worden.. Sogar mehr als 2.. Au english zuerst das mans mit deutsch lernen au sehen kann später.. Worldmodel und so war au definiert. Es soll konstant lernen als end ziel.. Es soll basically eine runtergebrochene simulation eines hirns werden..“

1. **Viele Modelle, wie im Blueprint definiert** (B1, B2, C1–C5, World-Model usw., mehr als zwei). B1 und B2 sollen echt verschiedene Bodies sein, nicht dasselbe LFM2.5-1.2B. Der Ist-Stand B1 = B2 ist nur ein Harness-Zwischenschritt.
2. **Englisch zuerst.** Deutsch wird später gelernt, damit man das Lernen daran sehen kann. Folge: C3-Benchmark und System-Prompts (heute „Antworte auf Deutsch“ in `runtime.py:317,458`, `__main__.py:61`, `verification.py:138`, `proofs.py:200`) auf Englisch umstellen; Deutsch wird ein Lern-/Transfertest.
3. **World-Model gehört dazu** (Blueprint §7.2, §92.2, G-SELF-WORLD-005), braucht ein eigenes Arbeitspaket.
4. **Konstantes Lernen ist das Endziel.** Age-0-Shadow mit Freigabe bleibt der Startzustand, die Age-Hülle soll schrittweise dorthin führen, nicht dauerhaft blockieren.
5. **Ziel: eine heruntergebrochene Simulation eines Gehirns**, kein Chatbot.

## 2026-10-11: dauerhafte GitHub-Freigabe für dieses Projekt

Im Projektthread wurde konkret um Freigabe gebeten, den geprüften Stand auf den neuen Arbeitsbranch `codex/authority-live-comparisons` in `RedMentos/Aii` zu pushen. Auf die Erläuterung der Zustimmung antwortete der Nutzer um 04:35:02 Europe/Berlin: „Man so das du immer kannst“.

Dies ist die dauerhafte Freigabe, im Rahmen der beauftragten V13-Entwicklung Änderungen und nachvollziehbare Zwischenstände auf Arbeitsbranches in `RedMentos/Aii` zu veröffentlichen. Routine-Pushes dieser Projektarbeit brauchen keine erneute Nachfrage. Die Freigabe bleibt bestehen, bis der Nutzer sie ändert. Der Remote-Stand muss nach jeder Veröffentlichung geprüft werden; lokale Commits allein gelten nicht als erfolgreiche GitHub-Sicherung.
