# WP-BP1 Verbraucher für die Hälften — Vorregistrierung (2026-10-27, vor jedem Modelllauf auf dem Test-Satz)

Skript `scripts/bp1_consumer.py`, Lehrplan und Bewertung `v13/offer_consumer.py` (Revision `v13-offer-consumer-v1`), Tests `tests/test_offer_consumer.py` (5, nur Software).
Diagnostik, **kein Gate, keine Autorität**: nichts wird eingeschaltet, STEP2 `UTILITY_FAIL` und B3 L1 `FAIL` bleiben unverändert.

## Vorabüberlegung (Nutzerregel 27.10.)
Voraussetzungen sind da: die Angebote erreichen C3 live als Schicht `Internal hypotheses:` im System-Prompt (runtime.py, HYPOTHESES), das Angebots-Schema (4 Felder) steht,
der C3-Master (LFM2.5-350M, HF fp32) und der LoRA-Weg (Ziele wie `lora_trainer.DEFAULT_TARGETS`) sind da. Der Verbraucher ist unabhängig von der Körper-Heterogenität (BP3) prüfbar,
weil er nur lesen muss, was in der Schicht steht. Sichtbarer Gewinn: Z3 zeigte, dass der unveränderte C3 Angebote nicht nutzt (0/117 Entscheidungen, immer UNKNOWN), also viel Luft nach oben.
Grenze, ehrlich vorab: Angebote sind **synthetisch** (gleiche vier Felder wie echte, aber nicht von B1/B2 erzeugt); echte Körper-Angebote sind die zweite Stufe. Ein PASS hier heißt: C3 *kann* die Schicht verwerten und tut es nachweislich ursächlich, nicht, dass STEP2 schon besteht.

## Frage
Kann ein kleiner Nachtrainings-Adapter (LoRA) C3 beibringen, die Angebote-Schicht richtig zu verwerten, und ist die Verwertung ursächlich (Angebote entfernt/vertauscht ändert die Antwort), ohne dass allgemeines Verhalten kippt?

## Lehrplan (7 Verhaltensweisen, 8 Aufgabenfamilien)
`calc_use` geprüftes Ergebnis im Angebot → übernehmen; `calc_hedge` ungeprüftes Angebot (hohe Unsicherheit, needs_reentry) → nur als „Unverified: …“; `lookup_use` Angebot mit wörtlichem Zitat → Wert;
`source_wins` Angebot widerspricht dem Text → Text gewinnt; `pick_quoted` zwei Angebote widersprechen sich, nur ein Zitat steht wörtlich im Text → das belegte; `ignore` Angebot zu anderem Schlüssel → aus dem Text antworten;
`abstain` Wert nicht im Text (ohne Angebot oder mit unbelegtem Angebot) → „nicht angegeben“ (+ Hypothese als unverified); `plain` ohne Angebote, Wert im Text → Wert.
Training (Split 0) und Test (Split 1) haben **disjunkte** Vorlagen, Schlüsselwörter, Projektnamen, Sachnamen, Fragesätze und Unsicherheits-Formulierungen (Software-Test belegt es). Antwort-Wortlaut im Training ≠ Test.

## Aufbau
- Basis: C3 LFM2.5-350M HF-Master fp32 (`LiquidAI/LFM2.5-350M`, Rev. im Report), LoRA r16/α32 auf `v_proj,out_proj,in_proj,w1,w2,w3`, lr 3e-4, Batch 8, Seed 1 und Seed 2 (frische Daten), plus 10 % Selbst-Destillations-Replay (Eigenantworten des Basismodells auf generische Fragen, getrennt von `specs/drift-probes.json`).
- Test: Seed 101, Split 1, 40 Items je Familie (320), Greedy, max 48 neue Token. Der Test-Satz wird vor dem Lauf nicht zum Abstimmen benutzt (Rauchtests nur mit anderem Seed ≠ 101).
- Arme: **base** (kein Adapter) / **adapter** je mit Angeboten *echt*, *entfernt*, *vertauscht* (Angebote eines anderen Items). **Kontrolle**: gleicher Lehrplan, gleiche Antworten, aber Angebote-Schicht im Training entfernt (`no_offers`) — misst Raten/Auswendiglernen statt Verwertung.
- Bewertung lexikalisch und deterministisch (`offer_consumer.score`); falsche Festlegung (`wrong_commit`) = Zahl behauptet, wo das Protokoll Übernahme verbietet. Fehlgeschlagene Antworten zählen als falsch.

## Entscheidungsregel (alles auf Seed 101, beide Trainingsseeds)
`CONSUMER_SUPPORTED` wenn für beide Trainingsseeds gilt:
1. adapter/echt Gesamt-ok ≥ 0.80 und ≥ base/echt + 0.15, und in den drei Lücken-Familien `calc_use`, `calc_hedge`, `abstain` gepoolt ≥ base/echt + 0.50 (gepaarte Bootstrap-95-%-Untergrenze der Differenz > 0, Bootstrap über Items). *Änderung vor dem ersten Lauf auf Seed 101, nach einem Rauchtest mit 16 Items (Seed 7, 3 Trainingsschritte): das Basismodell löst die fünf Text-lesbaren Familien (`lookup_use`, `source_wins`, `pick_quoted`, `ignore`, `plain`) schon, die Luft liegt nur in den drei Lücken-Familien; ein Gesamt-Zuwachs von +0.30 ist deshalb nicht erreichbar.*
2. wrong_commit ≤ 0.05;
3. **Ursächlich**: in den angebotsabhängigen Familien (`calc_use`, `calc_hedge`, dort steht der Wert nur im Angebot) fällt ok von echt → entfernt um ≥ 0.40, und bei *vertauscht* enthält in `calc_use` mindestens 60 % der Antworten den Wert des vertauschten Angebots (Folgerate);
4. Kontrolle (`no_offers`-trainiert, mit Angeboten getestet): ok in `calc_use`+`calc_hedge` ≤ 0.20 (Verwertung statt Raten);
5. Drift: mittlere Token-KL(Basis‖Adapter) auf den festen Drift-Fragen (`specs/drift-probes.json`, teacher-forced über die 24 Token der Basis-Antwort, wie WP-S5) ≤ 0.05; Greedy-Identität wird nur berichtet (zu streng für freie Texte), Stichproben gelesen.
`CONSUMER_PARTIAL` wenn 1 und 2 erfüllt, 3 oder 4 nicht (dann wird Lernen geprüft, aber Ursächlichkeit offen). Sonst `NO_CONSUMER_GAIN`. Kein Nachlauf mit geänderten Parametern unter dieser Registrierung; Änderungen brauchen eine neue Registrierung.

## Grenzen
Synthetische Angebote und Aufgaben einer Form (Schlüsselwert-Notizen, Rechnen); lexikalische Bewertung; HF-fp32-Master auf Cloud-CPU, nicht das quantisierte GGUF und nicht das Handy; Hedging-Signal hängt an Angebots-Metadaten (Unsicherheit/needs_reentry), die in echt von der Kalibrierung der Körper abhängen; 350M, 1 Basismodell.
Weitere Stufen (neue Registrierung): echte B1/B2-Angebote, GGUF-Pfad (GPTs native C3-LoRA), Arbeitsbereich-Schicht (`Task context`).
