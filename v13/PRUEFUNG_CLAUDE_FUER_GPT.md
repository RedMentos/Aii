# Gegenseitige Prüfung Claude ↔ GPT — Protokoll 1 (Claude prüft GPT), 2026-10-21

Nutzerwunsch 2026-10-21: Claude und GPT/Codex prüfen sich gegenseitig. Dieses Protokoll ist die erste Runde: Claude hat
GPTs Arbeit geprüft. Unten steht die Checkliste, mit der GPT jetzt Claudes Arbeit gegenprüft. Danach gilt die feste
Regel in `AGENTS.md`, Abschnitt „Gegenseitige Prüfung“: jede Seite prüft die letzte Arbeit der anderen, bevor sie
darauf weiterbaut, und schreibt ein kurzes Protokoll in diese Datei (neue Runde oben anhängen).

Branch dieser Runde: `claude/project-thread-g2f277` (Basis `claude/project-thread-0zelvf` @ `cc527f0`).

## 1. Was geprüft wurde

| GPT-Stand | Inhalt | Ergebnis |
| --- | --- | --- |
| `codex/continuation-20261016` @ `a1973d4` (PR #4) | Laufzeitcode `listarith`, `toolstep`, `tools`, `transaction`, `broker`, `toolforecast`; Lernkohorte 610 Zeilen; privater STEP2-Adapter + Pilot-Registrierung | Code korrekt bis auf 1 Lücke (unten, behoben); Gate-Angaben ehrlich; privat-sauber |
| `codex/continuation-review-20261013` @ `5a69538` (PR #3) | Review, gebundene Handy-Prüfkandidaten | Code-Kandidaten sind in `a1973d4` enthalten (byte-gleich); die 51 Review-Belegdateien von PR #3 liegen nur auf dem PR-#3-Branch (nicht verloren, aber nicht im gemeinsamen Stand) |
| `assistant/evidence-streaming-20261012` @ `718c301` (PR #2), `codex/authority-live-comparisons` @ `c1663f8` | Evidence-Streaming, atomare Action-JEPA-Wiederherstellung | in `a1973d4` enthalten; nur Privatsphäre geprüft (sauber) |
| Drive-Kandidat 19.10. (privater Pilot-Auditor) | schon von Claude in PR #6 integriert | dort mit 11 Tests geprüft |

## 2. Prüfpunkte und Befund

**Testsuite.** Volle Suite auf GPTs exaktem Stand `a1973d4` und auf dem gemeinsamen Stand nach dieser Runde, siehe Abschnitt 5.

**Korrektheit des Laufzeitcodes (`git diff 1941d07 a1973d4 -- v13/code/v13/`).**
- `transaction.py`: neuer Argumenttyp `text` überspringt den Shell-Zeichen-Filter. Sicher, weil `tools.py` `text` nur für
  `READ_LOCAL`-Werkzeuge erlaubt (ValueError sonst) und die 4000-Zeichen-Grenze bleibt. OK.
- `tools.py` `_turn_ended`: Effekt nach beendetem Zug geht nicht mehr in einen verwaisten Provisional-Puffer. Die
  Statusliste (FINAL, CANCELLED, DEADLINE, ERROR, INTERRUPTED) passt zu den Zuständen in `runtime.py`. OK.
- `toolstep.py` `_propose_list`: ruft C3 nur, wenn `list_arith` vom Nutzer eingeschaltet ist (Standard aus, also keine
  Modellkosten und kein Werkzeug ohne Erlaubnis). Fehler werden geloggt und ergeben keinen Vorschlag. OK.
- `toolforecast.py` `observe`: Quell-Schnappschuss vor/nach dem Prefill, schließt bei Änderung mit
  `SOURCE_CHANGED_DURING_OBSERVE`. Fail-closed, ehrlich als begrenzter Änderungsdetektor dokumentiert. OK.
- `listarith.py` Vorzeichen-Wächter (GPT-Fund vom 16.10.): echter Fehler in Claudes K-Code (`-5` wurde als `5`
  akzeptiert), sauber belegt, Gegenbeispiele erhalten. Guter Fund.

**Gefundene Lücke (in Claude-K-Code, von beiden Seiten übersehen), behoben in dieser Runde.**
Der Zahlen-Wächter in `listarith.compute` prüfte nur, *ob* eine Zahl im Text vorkommt, nicht *wie oft*. Liest C3 einen
Posten doppelt (`Rent 300, food 120, travel 80` → 300 zweimal), kam `800` statt `500` durch. Fix: Mehrfachmengen-Vergleich
(`collections.Counter`), ein Wert darf nicht öfter gelesen werden, als er im Text steht. Gleiche Werte bei verschiedenen
Posten (`a 7, b 7`) bleiben erlaubt. Test: `tests/test_listarith_signed_source.py::RepeatedValue`.
Bewusst *nicht* geändert, offen für GPT: (a) ein ausgelassener Posten wird nicht erkannt (der Wächter kennt die
Postenliste nicht); (b) eine Zusammenfassung mit Zusatzwort („Total cost: 65“) zählt als Posten, weil der bestehende Test
`total hours` absichtlich als Posten behandelt. Beides braucht eine vorregistrierte Messung, keinen schnellen Regex.

**Ehrliche Gate-Angaben.** Kein FAIL wurde schöngeredet.
- Lernkohorte `recovery-evening/native-final/analysis.json`: `canonical_gate_pass=false`, `phone_measured=false`,
  `claim_scope` „Row integrity and original numerical analysis only“. README nennt SHADOW, keine Entscheidungsbefugnis,
  keine Redmi-/Canon-Beförderung. Korrekt.
- Hinweis an beide Seiten: Der Urteilsname `CONTINUAL_LEARNING_CONFIRMED` stammt aus Claudes Thread M (13.10.) und klingt
  größer als das Gemessene (geschlossene Residual-Anpassung in zwei kleinen Werkzeugwelten; In-Welt bleibt per Design
  exakt der gemessene Wert, Verhältnis 1.00). Nicht umbenennen (vorregistriert), aber in Texten immer mit
  „SHADOW, zwei Werkzeugwelten“ nennen.
- GPT hat außerdem einen echten Fehler in Claudes M-Analyse gefunden: Teil-Eingaben (4 von 21 Zeilen) ergaben
  „CONFIRMED“. Der Integritätsprüfer ist inzwischen in `scripts/tool_forecast_learning_check.py` eingebunden. Guter Fund.
- STEP2 `UTILITY_FAIL` und B3 L1 `FAIL` stehen in GPTs Texten weiter als FAIL. Korrekt.

**Selbstbefund Claude (gehört eigentlich in GPTs Runde, aber gefunden ist gefunden).** Der reine Git-Stand war nicht
grün (siehe Abschnitt 5): Claude hatte Belege nur im Projektordner. Behoben. Lehre für beide Seiten: Suite immer auf
einem frischen Checkout des Branches laufen lassen, nicht im Arbeitsordner.

**Privatsphäre (Repo ist öffentlich).** Neues Werkzeug `scripts/public_repo_privacy_scan.py` (Tokens, Schlüssel,
Passwörter, private E-Mail-Adressen, Telefonnummern, Geräte-IDs, Drive-Links mit Schlüssel; nur hinzugefügte Zeilen).
Ergebnis über alle GPT-Branches ab dem ersten Commit: **CLEAN**. Gefundene Pfade sind nur Container-Pfade
(`/workspace/scratch`, `/root/native`, `/home/user`). Die „privaten“ STEP2-Fixtures sind synthetisch erzeugt
(`generate_fixtures.py`, Projektnamen wie `BFZWZWWW`), keine Nutzerdaten.

**Abgleich mit dem Ziel (wissenschaftlich, psychologisch-moralisch, schadet keinem Menschen, Module nur mit bewusster
Erlaubnis).** Neue Werkzeuge sind standardmäßig aus und brauchen Nutzer-Erlaubnis pro Werkzeug (`ToolRegistry.enable`);
`text`-Argumente nur für lesende Werkzeuge; Vorhersage bleibt SHADOW ohne Einfluss auf Antworten. Vorregistrierung vor
jedem Lauf, Rohbelege gehasht. Kein GPT-Code holt Module oder Netzwerkinhalte. Passt zum Ziel.

## 3. Offene Punkte für GPT

1. Bitte künftig auf dem gemeinsamen Stand aufsetzen (`claude/project-thread-0zelvf` bzw. dessen Nachfolger, siehe
   `UEBERGABE_FUER_ANDERE_KI.md`), nicht auf alten `codex/*`-Branches.
2. PR #2, #3, #4 wurden am 2026-10-22 auf Wunsch des Nutzers geschlossen (Branches bleiben erhalten). Inhalt von #2 und #4
   steckt vollständig im gemeinsamen Stand (keine Datei seither gelöscht). Die 51 Dateien, die nur in #3 lagen, sind jetzt
   byte-gleich im gemeinsamen Stand; die zwei an `673e3fb` gebundenen Kandidaten mit Tests liegen unter
   `code/docs/proofs/continuation-20261013/pr3-candidates-archived/` (README erklärt, warum nicht unter `tests/`).
   Offen: Restart-Bindungs-Kandidat für `toolforecast.py` neu gebunden portieren oder verwerfen.
3. Die zwei bewusst offenen `list_arith`-Lücken aus Abschnitt 2.
4. Deine Pilot-Registrierung bindet deinen Container (Pfade, Gerät) und ist woanders nicht ausführbar; Claude hat in PR #6
   eine zweite Registrierung *vor* dem Lauf veröffentlicht. Bitte prüfen, ob das methodisch sauber ist.

## 4. Checkliste: So prüft GPT Claudes Arbeit

Prüfziel ist jeweils die letzte Claude-Arbeit seit deiner letzten Runde. Stand 2026-10-21:

| Branch / PR | Commits | Prüffrage |
| --- | --- | --- |
| `claude/project-thread-0zelvf` (PR #5) | `13acfc3`..`cc527f0` | Übernahme ohne Überschreiben deiner Dateien? B3-L1-Diagnose: Hypothesen vor der Auswertung registriert? |
| `claude/project-thread-s7943o` (PR #6) | `abc5dc4`, `5ae02fd` | zweite Pilot-Registrierung vor dem Lauf? 0/18 exakt ehrlich berichtet? |
| `claude/project-thread-dq33gk` (PR #7) | `3d9e767`, `7109977` | Schalter standardmäßig aus? Ergebnis „CONTEXT_SUPPORTED“ durch die Vorregistrierung gedeckt? |
| `claude/project-thread-uvi2sq` | `8036f62`..`ec3a551` | WP-G2: Runde 2 „hybrid FAIL“ korrekt als FAIL geführt? |
| `claude/project-thread-8hlx74` | `eaf49b7`, `f2f6976` | B3 L1 Versuch 4 und Fast-Trace v3 vor Training/Inferenz registriert? |
| `claude/project-thread-g2f277` (diese Runde) | siehe `git log` | `listarith`-Fix korrekt? Privatsphäre-Scan sinnvoll und vollständig genug? |

Befehle (in `v13/code`, Python 3.11+, numpy):

```sh
git fetch origin
git log --format='%h %an %ad %s' --date=short a1973d4..origin/<branch>      # was ist neu
git diff a1973d4 origin/<branch> -- v13/code/v13/                              # Laufzeitcode-Änderungen
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -m unittest discover -s tests     # volle Suite
PYTHONPATH=.:tests python -m unittest tests.test_listarith tests.test_listarith_signed_source tests.test_public_repo_privacy_scan
python scripts/public_repo_privacy_scan.py --base a1973d4 --head origin/<branch>   # muss CLEAN sein
sha256sum v13/agi/listarith.py scripts/public_repo_privacy_scan.py              # mit Tabelle unten vergleichen
```

Hashes nach dieser Runde (Pfade relativ zu `v13/code`):

| Datei | SHA-256 |
| --- | --- |
| `v13/agi/listarith.py` | `42edf240f7fa7ca66e118a5c00117024431a19936739fc9cc09218e7c86a3a1d` (bei `a1973d4`: `d52aece804186cb86c796c571815a7ceeb1156573f6358bf4ca3bf984e5fc408`) |
| `scripts/public_repo_privacy_scan.py` | `8db109340cb3570e9f323a56e855ea5ca28d2ddfc737a4f44b6d57a34f43d856` |
| `v13/toolstep.py` | `62386f39165a82d4c34c775861a7c538a5be5dd96fa40eff76c5d709f7879ddd` |
| `v13/toolforecast.py` | `2fb07f2797190179d9cd395c4a6cdda5974f20ee1a79194e4640b98a7296f29f` |
| `v13/agi/tools.py` | `aaec7fb801392d7bc3084760985ebc57f79506c87175cbaad1864ff691a403da` |
| `v13/transaction.py` | `7edd8e349cfc449a1123c660d35cfc337261754b138cd6cf8ba62c0b5b6530b0` |
| `v13/broker.py` | `3a073278e6bf043f7d26fe245b87e52a2be90eb21a67569890ef2d5f1b40211a` |

Prüfpunkte, die jede Runde abdeckt (gilt für beide Seiten):
1. **Tests**: volle Suite grün (Fehler mit Ausgabe nennen, nichts überspringen oder deaktivieren).
2. **Ehrlichkeit**: jedes FAIL bleibt FAIL; SHADOW/synthetisch/Linux/Redmi als Evidenzstufen getrennt; Vorregistrierung
   liegt zeitlich (Commit) vor dem Lauf.
3. **Korrektheit**: Laufzeitcode-Diff lesen, mindestens ein Gegenbeispiel pro neuer Prüfung/Wächter versuchen.
4. **Privatsphäre**: `public_repo_privacy_scan.py` CLEAN; nichts Privates ins öffentliche Git, Privates nur auf Drive.
5. **Ziel**: kein Schaden für Menschen; neue Werkzeuge/Module standardmäßig aus und nur mit bewusster, unmanipulierter
   Erlaubnis des Nutzers; keine Entscheidungsbefugnis für ungemessene SHADOW-Teile.
6. **Nichts überschreiben**: vor jedem Push `git fetch`, fremde Commits mergen statt überschreiben, kein Force-Push.

Ergebnis bitte als neue Runde **oben** in dieser Datei (oder als `PRUEFUNG_GPT_FUER_CLAUDE.md`) mit: geprüfte Commits,
Befehle + Ausgabe, Befunde (Fehler / Hinweis / OK), was du geändert hast.

## 5. Testlauf dieser Runde

Befehl jeweils in `v13/code`: `PYTHONPATH=.:tests python -m unittest discover -s tests` (Linux-Container, Python 3.13, numpy 2.5).

| Stand | Ergebnis |
| --- | --- |
| GPT `a1973d4` (unverändert) | **1439 Tests OK, 5 Skips** (die `usage:`-Zeilen im Log sind gewollte argparse-Tests, keine Fehler) |
| gemeinsamer Stand `cc527f0` vor dieser Runde | **1582 Tests, 1 FAIL**: `test_neuro_ledger.test_evidence_files_exist_in_repository`. Ursache auf Claude-Seite: 19 kleine Belegordner `v13/bench-results/*-20261012` (u. a. `homeo-meta`, `corollary`, `latewatch`, zusammen ~0,5 MB), die der §102-Neuro-Ledger zitiert, lagen nur im Projektordner, nicht im Git. Die frühere Angabe „1571 OK“ galt für den Projektordner, nicht für den reinen Git-Baum. |
| nach dieser Runde | **1585 Tests OK, 5 Skips** (19 Belegordner ergänzt, Privatsphäre-Scan CLEAN; +3 Scan-Tests, +1 `list_arith`-Test) |
