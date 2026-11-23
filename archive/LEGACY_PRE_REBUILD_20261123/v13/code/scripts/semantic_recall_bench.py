#!/usr/bin/env python3
"""WP-H/WP-S2 cloud benchmark: semantic memory keys (EmbeddingGemma) vs lexical recall.

Fixed English fixture (German as transfer test): stored correction questions, two paraphrases each
(one on the calibration side, one on the test side, alternating) and unrelated negatives.
The admission threshold is chosen on the calibration side only (false admits at most 5 points above
the lexical baseline, which itself admits some negatives through shared function words), then the
test side is reported, and finally the real Memory.recall path is run end to end at that threshold.
Diagnostic only: changes no installed setting. RAM/latency here are Linux numbers, not Redmi.
"""
import argparse, json, os, sys, tempfile, threading, time
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from v13.memory import relevance  # noqa: E402
from v13.retrieval_worker import admissible  # noqa: E402
from v13.semantic_memory import SemanticKeys, prompt, truncate, cosine  # noqa: E402
from v13.resources import process_memory  # noqa: E402

EN = [
 ('What is the budget of Project Aurora?', '120 euros', 'How much money does Project Aurora have available?', 'What funding was allocated to Project Aurora?'),
 ('Where did I park my car?', 'Level 2, spot 14', 'Which spot is my vehicle in?', 'Do you remember where I left the car?'),
 ('When is my dentist appointment?', 'Tuesday 9:30', 'What time do I see the dentist?', 'When do I have to go to the dental clinic?'),
 ("What is my sister's name?", 'Mira', 'How is my sister called?', 'Who is my sister?'),
 ('Which medication do I take in the morning?', 'Ramipril 5 mg', 'What pills do I need after waking up?', 'What are my morning meds?'),
 ('What is the Wi-Fi password at home?', 'blue-otter-42', "What's the home wireless key?", 'How do I log into my home network?'),
 ('What is my favorite programming language?', 'Python', 'Which language do I like to code in most?', 'What do I prefer to program with?'),
 ('How many hours of sleep do I need?', 'about 8', 'How long should I sleep each night?', "What's my ideal amount of rest at night?"),
 ('Who leads Project Borealis?', 'Jonas', 'Who is the manager of Project Borealis?', 'Which person is in charge of Project Borealis?'),
 ('What is my phone model?', 'Redmi Note 9', 'Which smartphone do I own?', 'What handset am I using?'),
 ('When does the gym close on Sundays?', '18:00', 'Until what time is the fitness studio open on Sunday?', 'What are the Sunday closing hours of my gym?'),
 ('What did the doctor say about my blood pressure?', 'walk daily, less salt', "What was the physician's advice on my hypertension?", "What were the doctor's comments on my BP?"),
 ('What is my daughter allergic to?', 'peanuts', "Which foods cause my daughter's allergy?", 'Does my kid have any allergies?'),
 ('Which train do I take to work?', 'S3 at 7:12', 'What rail line do I commute on?', 'How do I get to the office by train?'),
 ('What is the deadline for the tax return?', '31 July', 'When do I have to file my taxes?', 'By when must the tax declaration be submitted?'),
 ('What is my blood type?', 'A positive', 'Which blood group do I have?', 'What type of blood am I?'),
 ('What is the name of my dog?', 'Bruno', 'What is my dog called?', 'How did I name my puppy?'),
 ('Where is the spare house key?', 'under the blue flower pot', 'Where do we hide the extra key to the house?', 'Where can I find the backup key for home?'),
 ("What is my landlord's phone number?", '0171 555 0199', 'How can I call my landlord?', 'What number reaches the person I rent from?'),
 ('What temperature should the oven be for the bread?', '230 °C', 'How hot do I bake the bread?', 'At what heat does the loaf go in the oven?'),
 ('What is the size of my shoes?', '43', 'Which shoe size do I wear?', 'What size are my feet?'),
 ("When is my mother's birthday?", '12 March', 'On what date was my mom born?', "When do we celebrate my mother's birthday?"),
 ('What is the license plate of my car?', 'B-XY 123', "What's my vehicle registration number?", 'Which number plate does my car have?'),
 ('What is the capacity of my phone battery?', '5020 mAh', "How many mAh does my phone's battery have?", "How big is my handset's battery?"),
]
EN_NEG = ['What is the capital of Japan?', 'Tell me a joke about cats.', 'How do I boil an egg?', "What's 17 times 23?",
 'Explain photosynthesis briefly.', 'Who wrote Hamlet?', 'What is the weather like on Mars?', 'Recommend a good science fiction book.',
 'How far is the moon from earth?', "Translate 'good morning' into Spanish.", 'What is a prime number?', 'Write a haiku about autumn.',
 'Who leads Project Cassiopeia?', 'What is the budget of Project Delta?', 'How do airplanes fly?', 'What is the boiling point of water?']
DE = [
 ('Wie hoch ist das Budget von Projekt Aurora?', '120 Euro', 'Wie viel Geld hat Projekt Aurora zur Verfügung?', 'Welche Mittel wurden Projekt Aurora bewilligt?'),
 ('Wo habe ich mein Auto geparkt?', 'Ebene 2, Platz 14', 'An welcher Stelle steht mein Wagen?', 'Weißt du noch, wo ich das Auto abgestellt habe?'),
 ('Wann ist mein Zahnarzttermin?', 'Dienstag 9:30', 'Um wie viel Uhr muss ich zum Zahnarzt?', 'Wann muss ich in die Zahnarztpraxis?'),
 ('Wie heißt meine Schwester?', 'Mira', 'Wie ist der Name meiner Schwester?', 'Wer ist meine Schwester?'),
 ('Welche Medikamente nehme ich morgens?', 'Ramipril 5 mg', 'Welche Tabletten brauche ich nach dem Aufstehen?', 'Was sind meine Morgenmedikamente?'),
 ('Wie lautet das WLAN-Passwort zu Hause?', 'blue-otter-42', 'Wie komme ich zu Hause ins Netz?', 'Was ist der Schlüssel für mein Heimnetz?'),
 ('Wie heißt mein Hund?', 'Bruno', 'Welchen Namen hat mein Hund?', 'Wie habe ich meinen Welpen genannt?'),
 ('Wann hat meine Mutter Geburtstag?', '12. März', 'An welchem Tag wurde meine Mama geboren?', 'Wann feiern wir den Geburtstag meiner Mutter?'),
]
DE_NEG = ['Was ist die Hauptstadt von Japan?', 'Erzähl mir einen Witz über Katzen.', 'Wie koche ich ein Ei?', 'Wer hat Faust geschrieben?',
 'Wie weit ist der Mond entfernt?', 'Was ist eine Primzahl?', 'Wer leitet Projekt Kassiopeia?', 'Wie fliegen Flugzeuge?']
LEXICAL_THRESHOLD = .25
FAR_CAP = .05

class Encoder:
    def __init__(self, runner): self.runner = runner; self.last_metrics = {}
    def installed(self): return True
    def revision(self): return 'bench'
    def pids(self): return self.runner.pids()
    def unload(self): self.runner.unload()
    def __call__(self, texts, cancel, deadline): return self.runner.embed([prompt(t) for t in texts], cancel, deadline)

def split(memories, negatives):
    calib, test = [], []
    for i, (_, _, p0, p1) in enumerate(memories):
        a, b = (p0, p1) if i % 2 == 0 else (p1, p0); calib.append((a, i)); test.append((b, i))
    for j, q in enumerate(negatives): (calib if j % 2 == 0 else test).append((q, None))
    return calib, test

def evaluate(queries, keys, sims, thr):
    """Combined score as in Memory.recall: max(lexical, cosine if cosine >= thr), entity guard first."""
    hit1 = hit3 = pos = neg = false = 0
    for (q, gold), row in zip(queries, sims):
        scored = []
        for k, (key, s) in enumerate(zip(keys, row)):
            if not admissible(q, key): continue
            lex = relevance(q, key); sc = max(lex, s) if thr is not None and s >= thr else lex
            if sc >= LEXICAL_THRESHOLD: scored.append((sc, k))
        ranked = [k for _, k in sorted(scored, reverse=True)]
        if gold is None: neg += 1; false += bool(ranked)
        else: pos += 1; hit1 += ranked[:1] == [gold]; hit3 += gold in ranked[:3]
    return {'hit_at_1': round(hit1/pos, 4), 'recall_at_3': round(hit3/pos, 4), 'false_admit_rate': round(false/max(neg, 1), 4), 'positives': pos, 'negatives': neg}

def bench_lang(name, memories, negatives, enc, dims, out):
    keys = [m[0] for m in memories]; calib, test = split(memories, negatives); t0 = time.monotonic()
    vk = enc(keys, threading.Event(), time.monotonic()+120); vc = enc([q for q, _ in calib], threading.Event(), time.monotonic()+120)
    vt = enc([q for q, _ in test], threading.Event(), time.monotonic()+120); encode_s = time.monotonic()-t0
    res = {'memories': len(keys), 'encode_seconds': round(encode_s, 3), 'per_text_ms': round(1000*encode_s/(len(keys)+len(calib)+len(test)), 1),
           'lexical': {'calibration': evaluate(calib, keys, [[0.]*len(keys)]*len(calib), None), 'test': evaluate(test, keys, [[0.]*len(keys)]*len(test), None)}, 'dims': {}}
    for d in dims:
        K = [truncate(v, d) for v in vk]; sc = [[cosine(truncate(v, d), k) for k in K] for v in vc]; st = [[cosine(truncate(v, d), k) for k in K] for v in vt]
        grid = [round(.3 + i*.01, 2) for i in range(66)]; best = None; lex_far = res['lexical']['calibration']['false_admit_rate']
        for thr in grid:
            m = evaluate(calib, keys, sc, thr)
            if m['false_admit_rate'] <= lex_far + FAR_CAP and (best is None or (m['hit_at_1'], m['recall_at_3'], thr) > (best[1]['hit_at_1'], best[1]['recall_at_3'], best[0])): best = (thr, m)
        thr = best[0] if best else None
        res['dims'][d] = {'threshold_from_calibration': thr, 'calibration': best[1] if best else None, 'test': evaluate(test, keys, st, thr) if thr else None,
                          'gold_cosine_test_mean': round(sum(st[i][g] for i, (_, g) in enumerate(test) if g is not None)/len(memories), 4),
                          'best_negative_cosine_test_max': round(max(max(st[i]) for i, (_, g) in enumerate(test) if g is None), 4)}
    out[name] = res; return res

def end_to_end(enc, memories, negatives, dim, thr):
    """Real Runtime + Memory.recall path with the chosen settings (fresh temp home)."""
    from v13.runtime import Runtime
    with tempfile.TemporaryDirectory() as td:
        r = Runtime(Path(td))
        try:
            r.cfg.update(memory_embedding='on', memory_embed_dim=dim, memory_embed_threshold=thr, memory_embed_keep=1, retrieval_candidates=64)
            r.memory.semantic_keys = SemanticKeys(r.store, r.cfg, enc); ids = []
            for key, value, _, _ in memories:
                e = r.store.event(r.session, key); ids.append(r.memory.feedback(e['event_id'], 'fact', value, key=key))
            hits = channel = false = 0; lat = []
            for i, (_, value, p0, p1) in enumerate(memories):
                for q in (p0, p1):
                    t = time.monotonic(); got = r.memory.recall(q, r.session, cancel=threading.Event(), deadline=time.monotonic()+60); lat.append(time.monotonic()-t)
                    hits += bool(got) and got[0]['id'] == ids[i] and got[0]['value'] == value; channel += bool(got) and got[0].get('retrieval_channel') == 'embedding'
            for q in negatives: false += bool(r.memory.recall(q, r.session, cancel=threading.Event(), deadline=time.monotonic()+60))
            lat.sort()
            return {'hit_at_1': round(hits/(2*len(memories)), 4), 'top1_via_embedding_channel': channel, 'false_admit_rate': round(false/len(negatives), 4),
                    'recall_latency_ms_median': round(1000*lat[len(lat)//2], 1), 'recall_latency_ms_max': round(1000*lat[-1], 1), 'last': r.memory.semantic_keys.last}
        finally: r.close()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True)
    ap.add_argument('--server', help='llama-server binary'); ap.add_argument('--home', help='installed V13 home (cloud_bench) to find llama-server')
    ap.add_argument('--model', help='EmbeddingGemma GGUF'); ap.add_argument('--cache', help='download the pinned specs/models.json embedding file here')
    ap.add_argument('--dims', default='128,256,768'); ap.add_argument('--threads', type=int, default=4); a = ap.parse_args()
    from v13.runners import LlamaRunner
    if not a.server: a.server = str(next(Path(a.home).glob('bin/b*/llama-*/llama-server')))
    if not a.model:
        from v13.models import catalog, download_file
        f = catalog()['models']['embedding']['files'][0]; a.model = str(download_file(f, Path(a.cache)/f['local_name']))
    os.environ['V13_LLAMA_SERVER'] = a.server; dims = [int(x) for x in a.dims.split(',')]
    with tempfile.TemporaryDirectory() as home:
        (Path(home)/'logs').mkdir()
        runner = LlamaRunner(Path(home), 'M_EMBED', Path(a.model), {'context_tokens': 2048, 'threads': a.threads}, purpose='embed'); enc = Encoder(runner)
        t = time.monotonic(); runner.load(threading.Event(), time.monotonic()+120); load_s = time.monotonic()-t
        try:
            out = {'schema': 'V13_SEMANTIC_RECALL_BENCH_V1', 'model': Path(a.model).name, 'runner': Path(a.server).parent.name, 'platform': os.uname().machine, 'cpus': os.cpu_count(),
                   'threads': a.threads, 'cold_load_seconds': round(load_s, 2), 'far_cap': FAR_CAP, 'lexical_threshold': LEXICAL_THRESHOLD,
                   'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'langs': {}}
            bench_lang('en', EN, EN_NEG, enc, dims, out['langs']); bench_lang('de', DE, DE_NEG, enc, dims, out['langs'])
            out['server_memory_after_bench'] = process_memory(runner.pids()[0]) if runner.pids() else None
            pick = 256 if 256 in dims else dims[0]; thr = out['langs']['en']['dims'][pick]['threshold_from_calibration']
            if thr: out['end_to_end'] = {'dim': pick, 'threshold': thr, 'en': end_to_end(enc, EN, EN_NEG, pick, thr), 'de': end_to_end(enc, DE, DE_NEG, pick, thr)}
        finally: runner.unload()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps({'en': {d: v['test'] for d, v in out['langs']['en']['dims'].items()}, 'lexical_en': out['langs']['en']['lexical']['test'], 'end_to_end': out.get('end_to_end')}, ensure_ascii=False))

if __name__ == '__main__':
    main()
