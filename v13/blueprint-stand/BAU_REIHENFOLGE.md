# Blueprint-Gesamtabgleich 2026-10-27

## Blueprint-Gesamtabgleich und Bau-Reihenfolge (2026-10-27, Thread „Blueprint ganz lesen, Stand zeigen“, Branch `claude/project-thread-hq9olw`) — Pakete WP-BP1..BP12

Grundlage: Blueprint v10.16.1 ganz gelesen (13 773 Zeilen), Code aller Claude- und GPT-Zweige bis 27.10. früh (GPT zuletzt Run 629–648), ROADMAP, ABDECKUNG, ZIELABGLEICH, `measure_suite` vom 27.10., Forschungsabgleich WP-FS1..FS10. Handy-Übersicht mit Ampel je Baustein: https://claude.ai/artifact/4eKbPpZEYKPpZZaA93PJKC (Quelle `v13/blueprint-stand/blueprint-stand.html`).

**Befund:** Fundament fertig. Die Gehirn-Mitte ist fast ganz gebaut, ihr Nutzen ist meist nicht gezeigt. §100: 1 von 10 grün (G-SELF-WORLD, Cloud). Viele FAILs lagen an **fehlenden Voraussetzungen**, nicht an der Idee: STEP2 Zwei-Hälften, Z6e Wecken, Z6 Observer-Nutzen, Z5e Koalition, Z6a Denktiefe (alle: C3 verwertet Hinweise der Hälften nicht, Z3 NO_CONSUMER_PATH); Z9 Traum, G-AGE-REOPEN, Z6k Modulatoren (alle: kein Gewichts-Lernen im Alltag); B3 L1 nicht repliziert (kein echtes B1→B2-Tap-Paar für die Empfänger-Kalibrierung). Diese Gates gelten als **noch nicht prüfbar**, nicht als widerlegt.

**Regel vor jedem Test (Nutzer, 27.10.):** Vor jedem Test am Blueprint prüfen, ob der Baustein die nötigen Daten und Voraussetzungen hat (inkl. eines Verbrauchers für sein Ergebnis) und wie viel Gewinn überhaupt sichtbar werden kann, auch für ihn allein. Fehlt etwas, erst bauen. Die Übersicht führt dazu je Baustein: braucht / da / Test jetzt sinnvoll.

**Bau-Reihenfolge (Voraussetzungen zuerst; GPT macht jeweils die Gegenprüfung nach der Cross-Review-Regel):**

1. **WP-BP1 Verbraucher für die Hälften:** C3 lernt, Angebote der Hälften und den Arbeitsbereich zu verwerten (Nachtraining mit Angeboten im Text, Gegenprobe ohne), zusammengeführt mit GPTs nativem C3-LoRA/GGUF. Braucht: nichts Neues. Öffnet: BP4, BP6.
2. **WP-BP2 Lernen in den Gewichten im Alltag:** wenig Vergessen hinter dem AG6-Freigabe-Tor, Cloud + Handy-Bauteil; Arme Sparse-Memory, LoRA je Rolle, Subspace Tuning (WP-FS2), Ablauf-Schema (WP-FS7). Braucht: nichts Neues. Öffnet: BP7, BP8, BP9, Body-JEPA.
3. **WP-BP3 Experten-Hälften einbauen (= WP-Z10):** EuroMoE + SmallThinker als B1/B2, §24.19 Pre-Router-Vergessen, Expert-Deltas bei eingefrorenem Router; Späher-Sonden für die Wahl B1/B2/Lehrer (WP-FS9). Braucht: BP2. Öffnet: BP4, BP5.
4. **WP-BP4 Zwei Hälften neu prüfen:** STEP2_EXIT / G-B-TIMESCALE-DIVERGENCE mit Verbraucher und verschiedenen Experten-Hälften gegen „ein Körper, zwei Zustände“ (Z2l). Braucht: BP1, BP3.
5. **WP-BP5 B3 Latent:** Z4e (Versuch 7) auswerten; dann echtes B1→B2-Tap-Paar für B3-H4-Kalibrierung. Bleibt L1 FAIL, als Blueprint-Abweichung festhalten. Braucht: BP3.
6. **WP-BP6 Gehirn-Mitte im Zusammenspiel (Rest WP-Z6):** 24.17, 24.22, 24.23, 24.25, 24.26, 24.32 mit Verbraucher und allen Teilen an; neues Pflichtmaß meta-I (WP-FS3) und Selbstvorhersage-Test (WP-FS4). Braucht: BP1.
7. **WP-BP7 Schlaf festigt, Traum mit Kontrolle (= Z9 neu):** Gewichts-Festigung in Sleep mit SSGM-Prüfliste (WP-FS6) und Rekonsolidierung (WP-FS8); dann Traum mit Kontrolle „policy-only“ und Gedächtnis-Test über simulierte Wochen. Braucht: BP2.
8. **WP-BP8 Age-Wiederöffnen neu (G-AGE-REOPEN):** mit echtem Gewichts-Lernen, `noise_aware`. Braucht: BP2.
9. **WP-BP9 Typisierte Modulatoren an echten Updates (G-MODULATOR, Nachfolger Z6k).** Braucht: BP2.
10. **WP-BP10 Weltmodell in den Alltag:** Z12c im Werkzeug-Pfad (SHADOW) mit GPTs Konfidenz-Kontrolle; danach Entscheidungs-Ziel (WP-FS1) und Veraltet-Markierung im Workspace (WP-FS10). Braucht: nichts Neues.
11. **WP-BP11 Module nur mit bewusster Erlaubnis (Nutzerziel):** Herkunft prüfen, DS1-Sandbox, Aktivierung nur nach bewusster Freigabe, Rücknahme; Verbote gegen Umformulierung + Qwen3Guard-Stream-0.6B als Zweitwächter (WP-FS5). Braucht: nichts Neues.
12. **WP-BP12 Handy-Paket komplett (= WP-Z7):** erst wenn BP1–BP11 drin sind; ein großer Testlauf je Bauteil (TRAIN_RUNNER_PROOF, Langlauf, 24.14/24.33, Gewohnheiten Latenz/Energie, Ressourcen-Modi); Lernen in kurzen Fenstern wegen Hitze-Drosselung. Schließt STEP5, STEP7. Braucht: alle davor.

**Abweichungen vom Blueprint (bewusst, mit Grund):** C3 entscheidet nicht selbst (Z3: 0/117), fester Regel-Leser + Zweitleser statt freiem Lesen (UR3–UR8 UNSAFE), ein Körper mit zwei Zuständen reicht bisher (Z2l, wird in BP4 neu geprüft), Weltmodell je Gegenstand (Z12b FAIL, Z12c PASS), relative statt fester Freigabe-Schwelle beim Lernen neuer Hinweise (Z6i2), Werkzeug-Pakete R4 4–11 zählen nicht als Blueprint, Harness²/DeepSeek-Zusätze, Bild-Labor vor STEP8, Speculative Decoding aus, Termux statt APK. **Bewusst später/nicht:** STEP8–11, §8.6.1/3/5 (Architektur fehlt), Head/Layer-KV-Policy (llama.cpp kann es nicht), MobileMoE-S-QAT (Lizenz).
