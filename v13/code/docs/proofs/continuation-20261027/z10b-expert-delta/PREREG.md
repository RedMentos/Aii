# WP-Z10b (WP-BP3) Vorregistrierung: aktive Experten-Deltas bei eingefrorenem Router (§91 Phase A/B, STEP6C)

**Vorab-Prüfung (Regel 27.10.):** Daten und Voraussetzungen sind da: EuroMoE-Körper, Router-Monitor und Kalibrierung
(N11/Z10a), dieselben Faktenmengen je Seed wie Z10a (`fresh_facts`), Z10a-Arm „experts“ als Vergleich. Ein Verbraucher
des Ergebnisses ist gebaut (`v13/moe_learning.py`: nimmt den Messbericht, urteilt SHADOW_OK/REJECTED). Sichtbarer Gewinn
möglich: Z10a-Experten-Arm vergaß noch +0,33 bis +0,43 nats und verschob die Route nahe an die Grenze; ein
niedrigrangiges, rückholbares Delta nur auf den aktiven Experten sollte deutlich weniger vergessen. Wenn nicht, ist das
ein echtes Ergebnis. Nicht geprüft wird: Handy, llama.cpp, Fenster 16–17 (erst wenn 8–9 trägt).

**Aufbau** (`code/scripts/z10b_expert_delta.py`): EuroMoE-2.6B-A0.6B @ 96e19829, HF fp32, Cloud-CPU. Fenster Schichten 8–9,
Seeds 13/21/34 mit denselben Faktenmengen wie Z10a, Alt-Aufgabe die 48 EN/DE-Texte, Kalibrierung wie N11/Z10a neu gemessen.
Router, Attention, Norms, Embeddings nie trainierbar. Delta = LoRA (Rang 8, alpha 16, B=0 am Start) auf w1/w2/w3.
Arme: `active16` (die 16 Experten je Schicht, die von den Router-Top-k der neuen Fakten-Token am häufigsten getroffen
werden), `random16` (16 zufällige, Kontrolle „zählt die Auswahl?“), `all64` (alle Experten, Kontrolle „kostet die
Beschränkung etwas?“). Adam, bis neuer Verlust ≤ 10 % des Starts oder 40 Schritte. Lernrate wird **vorab** an einem
Probe-Seed 7 (nicht in der Wertung) aus {1e-3, 3e-3, 1e-2} gewählt (kleinste, die `active16` auf ≤ 20 % bringt), dann fest.

**Kriterien** (Urteil `Z10B_ACTIVE_DELTA_PASS` nur wenn D1–D4 gelten; D5 getrennt berichtet):
- D1 gelernt: `active16` neuer Verlust am Ende ≤ 20 % des Starts in 3/3 Seeds.
- D2 Behalten: `active16` Alt-Verlust-Zuwachs ≤ 0,5 × Zuwachs des Z10a-Arms „experts“ (+0,37 / +0,33 / +0,43 nats) in ≥ 2/3 Seeds
  und absolut ≤ 0,2 nats in ≥ 2/3 Seeds.
- D3 Routen-Tor: B3-H6-Router-Tor (Router-KL, Top-k-Flip, Router-Eingangs-Norm, Residual-Norm gegen die
  Empfänger-eigene Kalibrierung) PASS für `active16` in ≥ 2/3 Seeds.
- D4 Rückholbar: Alt-Verlust mit abgeschaltetem Delta und mit entferntem Delta weicht um ≤ 1e-6 nats vom Start ab, alle Arme/Seeds.
- D5 Auswahl (nur Bericht): `SELECTION_HELPS` wenn `active16` bei gleicher Parameterzahl in ≥ 2/3 Seeds einen kleineren
  End-Verlust ODER weniger Schritte hat als `random16`, sonst `NO_SELECTION_EFFECT`. Dazu Größe des Deltas (Parameter, fp16-Bytes)
  gegen die ersetzten Voll-Gewichte.
Sonst `Z10B_ACTIVE_DELTA_FAIL` mit Angabe der verfehlten Kriterien. Keine Nachbesserung nach dem Lauf; ein geändertes
Verfahren wäre ein neues Paket mit neuer Vorregistrierung.
Grenzen: HF fp32, ein Körper, erfundene Fakten, Phase B als SHADOW-Messung, nicht in die Laufzeit-Antwort verdrahtet.
