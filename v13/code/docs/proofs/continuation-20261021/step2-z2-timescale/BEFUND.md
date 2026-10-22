# Befund WP-Z2: STEP2 mit Information, die nur B1 hat (2026-10-21)

Vorregistrierung `PREREG.md` (Commit `bdaafc2`, vor Inferenz gepusht). Linux-Cloud x86_64, 4 CPUs, **kein Redmi**.
Modelle/Runner byte-gleich mit 13.10./20.10.: B1 LFM2.5-1.2B `bb741ebb…`, B2 Qwen3.5-0.8B `57d19977…`, C3 LFM2.5-350M `3d10b6ab…`, llama.cpp b10964 `79e31218…`.
5 Arme × 70 Zeilen, alle RECORDED, 0 Strukturfehler; dazu Werkzeug-Replay je Arm (350 Zeilen).

## Ergebnis: `Z2_DIVERGENCE_NOT_SUPPORTED` (Gate FAIL, ehrlich)
| Kriterium (Werkzeug-Nutzen, 10 Episoden) | Wert | erfüllt |
|---|---|---|
| 1 C `both_exact` > bester Einzelkörper | .325 vs b1_only .333 | ✗ |
| 2 B1 und B2 gewinnen je eine Episode | ja | ✓ |
| 3 komplementäre Fehlerprofile (≥ .25 Abstand) | Optionsfelder b1 .57 / b2 .37 (.20), Regelfelder beide .10 | ✗ |
| 4a > gleiches Modell gleiche Policy (C same_policy_dual) | .325 > .308 | ✓ |
| 4b > gleiches Modell nur anderer Prompt (D prompt_only_dual) | .325 < .425 | ✗ |
| 5 Struktur | alles RECORDED | ✓ |
§99 „zwei Körper lohnen die Handy-Kosten“: **nein** (ein Körper + zwei Zustände D both_exact .367 ≥ zwei Körper .325) → billigere Form wäre erlaubt, aber auch sie besteht das Gate nicht.

## Was sich trotzdem bewegt hat (sekundär)
- **B1 hat jetzt eigene Information und liefert sie.** Ohne Schalter (Arme A, B) zitiert B1 die Optionswerte aus dem Datenblatt **nie** (nur bei RULE, wo sie in der Frage stehen). Mit `b1_recent_source_chars=600` (C) kommen sie in **27/70** Zeilen als verifiziertes Zitat bei C3 an, in D 24/70. Werkzeug-Nutzen C3+Werkzeug steigt von A .17–.19 auf C .31–.47.
- **Erstmals exakte SPLIT-Entscheidungen** (Regeln nur bei B2, Optionen nur bei B1 → beide nötig): im Arm D `both_none` 3/6 (Lumen, Meridian, Nimbus), `both_control` 1/6. Im Zwei-Körper-Arm C: **0/6**. In C liegt keine einzige SPLIT-Zeile vor, in der Regeln und Optionen gleichzeitig verifiziert ankommen; in D vier.
- **0 falsch festgelegte Entscheidungen** in allen 350 Werkzeug-Zeilen (Werkzeug sagt UNKNOWN statt zu raten). Ohne Werkzeug 0/350 exakt (C3 rechnet nicht, wie 20.10.).
- **Zitat-Kontext ist Voraussetzung:** Arm E (B1-Fenster an, Zitat-Kontext aus) liefert 0 verifizierte Options- oder Regelzitate — LFM/Qwen zitieren nie wörtlich genug für `offer_quote_min_chars=90`.

## Was das heißt
1. Der Engpass ist nicht mehr „B1 hat nichts“, sondern **Auswahl im Körper**: Qwen-B2 zitiert die alte Regel nur in 16/70 (C), B1 die Optionen in 27/70; beides in derselben Zeile kommt im Zwei-Körper-Arm nicht vor.
2. In dieser Messung war die gleiche LFM-1.2B als B2 (Arm D) bei SPLIT besser als Qwen-B2. Das ist **nicht vorregistriert** als Hauptfrage und nur ein Lauf mit einem Seed → Hinweis, kein Befund. Prüfbar mit Wiederholungen (Rauschband) vor jeder Modellentscheidung.
3. Bestehende Gate-Lage bleibt: STEP2 UTILITY_FAIL, G-B-TIMESCALE-DIVERGENCE-001 offen, `canonical_gate_pass=false`.

## Pannen, offen genannt
- Arm C lief 1× komplett, nur die Nachbearbeitung brach ab (`step2_wire_rebind.diagnose` erwartet altes Feld `prior`); Zeilen unverändert weiterverwendet, `diagnose` entfernt.
- Arm D Versuch 1: alle 10 Vorbereitungen `ArtifactChanged`, weil der eingefrorene Hash-Wächter `installed_artifacts` `b2_control` nicht kennt (B2 = B1-Gewichte). In der privaten Modulkopie korrigiert (gleiche Felder, B2-Datei über die eigene `b2_control`), D neu gelaufen. Versuch 1 als `armD-attempt1-failed.json` aufbewahrt.

## Empfehlung
- Schalter `b1_recent_source_chars` bleibt **aus** (keine Gate-Wirkung belegt). Er ist der erste Weg, auf dem B1 überhaupt eigene exakte Information hat; Einschalten nur nach Nutzerentscheidung und zusammen mit Zitat-Kontext 200.
- Nächster Schritt (neu vorregistrieren): (a) 3–5 Wiederholungen von C und D mit anderen Seeds für ein Rauschband; (b) Körper-Auswahl gezielt: JEF-Rückfrage (`jef_query`) „zitiere die Regel/die Optionswerte“ statt freier Offer; (c) Qwen- vs. LFM-B2 als eigene, gebundene Modellvergleichsfrage.

Daten: `code/bench-results/step2-z2-timescale-20261021/` (Zusammenfassungen, Werkzeug-Replays, Logs, SHA256SUMS);
volle STEP2-Berichte (je ~3,3 MB) im Projektordner `v13/bench-results/step2-z2-timescale-20261021/`.
