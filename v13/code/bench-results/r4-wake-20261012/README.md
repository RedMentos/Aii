# R4 C-native vs. Body-Wake (§31/§79) — 2026-10-12, Thread G

Skript `code/scripts/r4_wake_bench.py`, Rohdaten `r4.json`. Echte C3 LFM2.5-350M, B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B
(llama.cpp b10964, Cloud-CPU), dieselben 60 Aufgaben und derselbe Bench-Modus wie WP-T3b (Temperatur 0, C3 gierig,
Frist 600 s, Observer 180 s), frische Home je Arm. Runtime-Stand mit Cache-Begrenzung (`bbd710e`).

| Arm | bestanden | summary | long | notes | compare | geweckt | Angebote/Turn | Zeit/Turn |
|---|---|---|---|---|---|---|---|---|
| C3 allein | **0,683** | 0,47 | 1,0 | 0,93 | 0,33 | 0 % | 0 | **4,8 s** |
| C3 allein (Wiederholung) | 0,683 | gleich | | | | 0 % | 0 | 4,8 s |
| immer A+B (Effort max) | 0,583 | **0,67** | 1,0 | 0,67 | 0,00 | 100 % | 2,0 | 56,7 s |
| heuristisch (ausgeliefert, adaptiv) | 0,533 | 0,20 | 1,0 | 0,73 | 0,20 | 100 % | 1,08 | 24,5 s |
| gelerntes Wecken | – | | | | | | | |

Gepaart (Vorzeichentest): C3 allein vs. heuristisch 11:2, **p = 0,022**; C3 allein vs. immer A+B 13:7, p = 0,26;
immer A+B vs. heuristisch 11:8, p = 0,65.

## Befunde
1. **C3 allein ist auf diesen Aufgaben am besten und 5–12× schneller.** Das Wecken der Körper schadet hier im Mittel;
   gegen das ausgelieferte heuristische Wecken signifikant.
2. **Das heuristische Wecken eskaliert immer** (Weck-Rate 100 %, 0 von 41 C3-lösbaren Aufgaben verschont). Es weckt
   meist genau einen Körper (B2 bei summary/compare, B1 bei notes). Eskalations-Recall 7/7 auf den Aufgaben, die nur
   A+B löst, aber nur 1/7 davon wird bestanden, weil meist der falsche Einzelkörper geweckt wird.
3. **Nur summary profitiert von beiden Körpern** (0,47 → 0,67). compare bricht mit Körpern ein (0,33 → 0,00). In
   Ausgaben mit Körpern antwortet C3 teils mit Meta-Text über Systemregeln statt mit der Rechnung.
4. **C3 allein ist reproduzierbar** (60/60 identische Antworten). Der Nichtdeterminismus aus WP-T3b kommt also aus dem
   Körper-/Observer-Pfad, nicht aus C3 oder seinem Prompt-Cache.
5. **Gelerntes kalibriertes Wecken ist nicht messbar:** Es gibt keinen trainierten Wake-Kopf
   (`UNAVAILABLE_NO_TRAINED_HEAD`, Probelauf `r4-probe-limit4.json`: identisch zur Heuristik).

## Entscheidung laut Canon R4
C-native verdient breitere Autorität für diese Aufgabenarten. Die heuristische Weck-Politik erfüllt die Bedingung
„schwierige Fälle korrekt eskalieren“ nicht und verschont keine einfachen Fälle. Vorschlag (eigener Versuch,
nicht umgesetzt): Wecken nur bei Zusammenfassungs-/Summenprüfung und dann beide Körper; einen Wake-Kopf auf genau
diesen gepaarten Labels (C3 allein bestanden/nicht bestanden) trainieren und gegen C3 allein auf frischen Aufgaben prüfen.

## Grenzen
Generierte englische Aufgaben, Regex-Prüfung der Endantwort, eine Saat, gierige Bench-Dekodierung statt anti_echo,
keine Energie-/Nutzerkorrektur-Daten, Cloud-CPU-Zeiten (kein Redmi). Das `status`-Feld fehlt im Audit-Export
(alle Turns liefen bis zur Antwort, keine Fristschnitte beobachtet).
