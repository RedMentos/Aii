# Vorregistrierung WP-Z2b: STEP2 Rauschband (mehrere Seeds) + gezielte Fragen an die Körper (2026-10-21)

Vor jeder Inferenz committet und gepusht. Skript `code/scripts/step2_z2b_seeds.py`, Tests `code/tests/test_step2_z2b.py`.
Folgepaket zu WP-Z2 (`../step2-z2-timescale/`, Ergebnis `Z2_DIVERGENCE_NOT_SUPPORTED`, ein Seed).

## Warum
Z2 hatte einen Seed. Die entscheidenden Abstände waren winzig (zwei Körper .325 vs. b1_only .333; ein Körper + zwei Zustände .367).
Ob das Rauschen oder echt ist, war offen. Zweitens zeigte Z2 als Engpass die **Auswahl im Körper**: B2 zitierte die alte Regel nur 16/70,
Regeln und Optionen kamen im Zwei-Körper-Arm nie in derselben Zeile bei C3 an.

## Fund vorab im Code (offen genannt)
`cognition.offer` ruft `LlamaRunner.generate` **ohne** Seed auf → alle Körper-Angebote liefen immer mit Seed 13, egal was `cfg['seed']` sagt.
Ein Seed-Wechsel in den Einstellungen hätte also nur C3 verändert, nicht die Körper. Für Z2b folgt im Skript (nicht im Live-Code) der
Standard-Seed von Aufrufen ohne Seed `cfg['seed']`; Seed 13 = Z2-Bytes. Vorab geprüft: Qwen3.5-0.8B bei temperature 0.1/top_k 50 erzeugt
mit Seeds 13–16 unterschiedliche Texte, das Rauschband ist also nicht trivial null. Live-Code bleibt unverändert.

## Was gleich bleibt
10 eingefrorene Z2-Episoden (6 SPLIT, 2 RULE, 2 DETAIL), private Kopie des eingefrorenen STEP2-Harness (7 Varianten), echte Modelle
B1 LFM2.5-1.2B `bb741ebb…`, B2 Qwen3.5-0.8B `57d19977…`, C3 LFM2.5-350M `3d10b6ab…`, llama.cpp b10964 `79e31218…` (frisch installiert,
Hashes geprüft), Werkzeug-Replay (`scripts/step2_tool_replay.py`, C3-Extraktion fester Seed 13). Arm-Einstellungen von Z2 C und D.

## Arme × Seeds (12 Läufe × 70 Zeilen)
| Arm | Körper | Gezielte Frage |
|---|---|---|
| C | zwei Körper (B2 Qwen), Zitat-Kontext 200, B1-Fenster 600 | nein |
| D | ein Körper + zwei Zustände (B2 = LFM-Gewichte) | nein |
| **CQ (primär)** | wie C | ja |
| DQ (Kontrolle) | wie D | ja |
Seeds **14, 15, 16** (neu). Seed 13 (Z2) nur als Referenz, zählt nicht.

**Gezielte Frage** = vorhandener QUERY_PACKET-Pfad (`jef_query`, kind `FILL_GAP`) von `cognition.offer`, nur in der aktuellen Runde
(nie in den Vorbereitungsrunden), feste Texte, für alle Episoden gleich, ohne Werte oder Projektnamen:
- B2: „Which earlier project rules apply here: budget, deadline and local-only requirement? Quote the exact earlier source sentence that states them, or say they are not in the source.“
- B1: „Which option figures apply here: cost, duration and locality of Option A and Option B? Quote the exact source sentences that state them, or say they are not in the source.“
Rollenbezogen, weil §85.1 die Zeitskalen-Teilung vorsieht (B2 lange Regeln, B1 kurze Details). `same_policy_dual` bekommt zweimal die B1-Frage.

## Primäre Entscheidung — `Z2B_DIVERGENCE_SUPPORTED` nur wenn alles gilt
Werkzeug-Nutzen, Mittel über Seeds 14–16; Unsicherheit per Cluster-Bootstrap über die 10 Episoden (alle Seeds einer Episode bleiben zusammen),
10 000 Ziehungen, RNG-Seed 20261021, 95-%-Perzentil-Intervall (CI).
1. CQ `both_exact` > bester Einzelkörper (nach Mittel), **CI-Untergrenze der Differenz > 0** und in **jedem** Seed einzeln größer
2. B1 und B2 gewinnen je mindestens eine Episode gegeneinander in ≥ 2 von 3 Seeds
3. Komplementäre Fehlerprofile (Mittel): b1_only − b2_only Optionsfelder ≥ .25 und b2_only − b1_only Regelfelder ≥ .25
4. CQ `both_exact` − CQ `same_policy_dual` CI-Untergrenze > 0, und CQ `both_exact` − DQ `prompt_only_dual` CI-Untergrenze > 0
5. Struktur: kein STRUCTURAL_FAIL/INCOMPLETE; Arme taten, was sie sagen (CQ/DQ: alle aktuellen Angebote mit Frage; C/D: keines)
§99 „zwei Körper lohnen die Handy-Kosten“ nur, wenn 1–5 gelten **und** CQ − DQ `both_exact` CI-Untergrenze > 0. Sonst darf das Redmi die billigere Form nutzen.

## Sekundär (je mit CI, Urteil nur wenn das CI 0 ausschließt, sonst „keine klare Wirkung“)
- Wirkung der Frage: CQ − C und DQ − D (`both_exact`) → QUERY_HELPS / QUERY_HURTS / QUERY_NO_CLEAR_EFFECT
- B2-Modellfrage Qwen vs. LFM: D − C bei `both_exact` und `b2_only` → LFM_B2_BETTER / QWEN_B2_BETTER / NO_CLEAR_DIFFERENCE
- Rauschband je Arm und Variante (min/max/Spanne über Seeds); liegt Z2 (Seed 13) im Band? Sind die Z2-Abstände größer als die Spanne?
- Zeilen, in denen Regeln **und** Optionen gemeinsam verifiziert bei C3 ankommen (`joint_access`); exakte SPLIT-Entscheidungen je Arm; falsch festgelegte Entscheidungen.

## Erwartung vor dem Lauf
- Das Rauschband ist vermutlich in der Größenordnung von ±.05 → der Z2-Abstand .325/.333 ist dann Rauschen, nicht Befund.
- Die gezielte Frage könnte B2 öfter die alte Regel zitieren lassen; ob B2 (Qwen, 0.8B) das kann, ist offen. Kein Ergebnis wird vorweg angenommen.
- Ohne neue Fähigkeit im Modell ist ein Gate-PASS unwahrscheinlich; ein FAIL wird so berichtet.

## Grenzen
Linux x86 Cloud, 4 CPUs, kein Redmi; 10 Episoden × 3 Seeds, dieselben Episoden → das CI misst Episoden- und Sampling-Streuung, nicht neue Aufgaben.
Diagnose, kein Kanon-PASS (`canonical_gate_pass` bleibt false). Schalter `b1_recent_source_chars` bleibt im Code aus. STEP2 UTILITY_FAIL bleibt.
