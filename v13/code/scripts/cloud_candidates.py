#!/usr/bin/env python3
"""Cloud comparison of model candidates (WP-B/WP-G/WP-S1/S2); never changes the installed manifest.

Uses the pinned llama-server of an installed V13 home (cloud_bench.sh). Chat candidates run the
German C3 fixtures from benchmark_c3.py plus a few extra ones; the embedding candidate is scored on
German paraphrase-vs-distractor triples. Results are diagnostic only: no promotion, no routing change.
"""
import argparse, hashlib, json, math, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP / 'scripts'))
from benchmark_c3 import FIXTURES, lexical_checks  # noqa: E402

EXTRA = [
 {'id':'de_arith','system':'Antworte nur mit der Zahl.','user':'Was ist 17 plus 25?','must_all':['42']},
 {'id':'de_fact','system':'Antworte kurz auf Deutsch.','user':'Was ist die Hauptstadt von Frankreich?','must_all':['Paris']},
 {'id':'de_list','system':'Antworte kurz auf Deutsch.','user':'Nenne drei Farben, durch Kommas getrennt.','must_any':['rot','blau','grün','gelb']},
 {'id':'grounded_date','system':'Antworte ausschließlich aus der Quelle. Kurz auf Deutsch.','user':'Quelle: Das Treffen ist am Dienstag um 14 Uhr im Raum B. Frage: Wann ist das Treffen?','must_all':['Dienstag','14']},
]
EN = [
 {'id':'en_greeting','system':'Answer briefly and naturally in English.','user':'Say hello briefly. What could I ask you first?','must_any':['Hello','Hi']},
 {'id':'en_rewrite','system':'Only rephrase the given content briefly in English. Do not invent anything.','user':'Rephrase briefly: The test runs locally and uses no cloud.','must_all':['local'],'forbid':['online']},
 {'id':'en_grounded_report','system':'Answer only from the given sentence. Be brief.','user':'Source: Project Aurora has a budget of 120 euros. Question: How large is the budget?','must_all':['120']},
 {'id':'en_abstain','system':'If the answer is not in the text, briefly say it is not supported. Do not invent anything.','user':'Source: Project Aurora has a budget of 120 euros. Question: Who leads Project Aurora?','must_any':['not','unknown','no ']},
 {'id':'en_arith','system':'Answer only with the number.','user':'What is 17 plus 25?','must_all':['42']},
 {'id':'en_fact','system':'Answer briefly.','user':'What is the capital of France?','must_all':['Paris']},
 {'id':'en_list','system':'Answer briefly.','user':'Name three colors, separated by commas.','must_any':['red','blue','green','yellow']},
 {'id':'en_grounded_date','system':'Answer only from the source. Be brief.','user':'Source: The meeting is on Tuesday at 2 pm in room B. Question: When is the meeting?','must_all':['Tuesday','2']},
]
EN_TRIPLES = [
 ('The budget of Project Aurora is 120 euros.','Project Aurora has 120 euros available.','Project Aurora is led by Lena.'),
 ('I left my keys in the car.','My keys are still in the vehicle.','I washed my car yesterday.'),
 ('What time is it right now?','Can you tell me the current time?','How far is it to the station?'),
 ('The phone battery is almost empty.','My phone has hardly any charge left.','The phone has a large screen.'),
 ('It is supposed to rain heavily tomorrow.','Lots of rain is forecast for tomorrow.','Yesterday was sunny and warm.'),
 ('Please remind me about my medication at eight.','Tell me at 8 that I need to take my pills.','The movie starts at eight at the cinema.'),
 ('The cat is sleeping on the sofa.','The cat lies asleep on the couch.','The dog is barking in the garden.'),
 ('The train to Berlin is delayed.','The Berlin train will arrive late.','The train to Berlin is very crowded.'),
]
TRIPLES = [  # anchor, paraphrase, distractor (German)
 ('Das Budget von Projekt Aurora beträgt 120 Euro.','Projekt Aurora hat 120 Euro zur Verfügung.','Projekt Aurora wird von Lena geleitet.'),
 ('Ich habe meinen Schlüssel im Auto vergessen.','Mein Schlüssel liegt noch im Wagen.','Ich habe mein Auto gestern gewaschen.'),
 ('Wie spät ist es gerade?','Kannst du mir die aktuelle Uhrzeit sagen?','Wie weit ist es bis zum Bahnhof?'),
 ('Der Akku des Handys ist fast leer.','Mein Telefon hat kaum noch Strom.','Das Handy hat einen großen Bildschirm.'),
 ('Morgen soll es stark regnen.','Für morgen ist viel Regen angesagt.','Gestern war es sonnig und warm.'),
 ('Bitte erinnere mich um acht an die Medikamente.','Sag mir um 8 Uhr Bescheid, dass ich meine Tabletten nehmen muss.','Um acht Uhr beginnt der Film im Kino.'),
 ('Die Katze schläft auf dem Sofa.','Auf der Couch liegt die Katze und schläft.','Der Hund bellt im Garten.'),
 ('Der Zug nach Berlin hat Verspätung.','Die Bahn nach Berlin kommt später an.','Der Zug nach Berlin ist sehr voll.'),
]

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

def fetch(c, cache):
    p = cache / c['local_name']
    if not (p.exists() and p.stat().st_size == c['size'] and sha256(p) == c['sha256']):
        url = f"https://huggingface.co/{c['model_id']}/resolve/{c['revision']}/{c['local_name']}"
        tmp = p.with_suffix('.part'); print('lade', c['id'], flush=True)
        subprocess.run(['curl', '-sSfL', '-o', str(tmp), url], check=True)
        if sha256(tmp) != c['sha256']: tmp.unlink(); raise SystemExit(f"hash mismatch {c['id']}")
        tmp.rename(p)
    return p

def post(port, path, body, timeout):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', json.dumps(body).encode(), {'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())

def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close(); return port

def serve(server, model, extra, log):
    port = free_port()
    proc = subprocess.Popen([str(server), '-m', str(model), '--host', '127.0.0.1', '--port', str(port), '-c', '2048',
                             '-t', str(os.cpu_count() or 4), '--jinja', '--no-webui', *extra],
                            stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'LD_LIBRARY_PATH': str(server.resolve().parent)})
    t0 = time.monotonic()
    while time.monotonic() - t0 < 120:
        if proc.poll() is not None: return proc, port, 'EXITED'
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=2) as r:
                if r.status == 200: return proc, port, 'OK'
        except Exception: time.sleep(0.5)
    return proc, port, 'TIMEOUT'

def run_chat(port, fixtures):
    rows = []
    for fx in fixtures:
        t0 = time.monotonic()
        try:
            d = post(port, '/v1/chat/completions', {'messages':[{'role':'system','content':fx['system']},{'role':'user','content':fx['user']}],
                     'max_tokens':96,'temperature':0,'seed':13,'chat_template_kwargs':{'enable_thinking':False}}, 120)
            text = d['choices'][0]['message'].get('content') or ''; tim = d.get('timings', {})
            checks = lexical_checks(text, fx)
            rows.append({'id':fx['id'],'pass':bool(checks) and all(checks.values()),'checks':checks,'text':text.strip()[:400],
                         'seconds':round(time.monotonic()-t0,3),'prompt_tps':tim.get('prompt_per_second'),'gen_tps':tim.get('predicted_per_second')})
        except Exception as e:
            rows.append({'id':fx['id'],'pass':False,'error':repr(e)[:300]})
    n = len(rows); tps = [r['gen_tps'] for r in rows if r.get('gen_tps')]
    return {'fixtures':rows,'passed':sum(r['pass'] for r in rows),'total':n,'mean_gen_tps':round(sum(tps)/len(tps),1) if tps else None}

def cos(a, b):
    return sum(x*y for x, y in zip(a, b)) / (math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(y*y for y in b)) or 1)

def run_embed(port, triples):
    rows = []; t0 = time.monotonic()
    for a, p, d in triples:
        e = [x['embedding'] for x in post(port, '/v1/embeddings', {'input':[a, p, d]}, 60)['data']]
        cp, cd = cos(e[0], e[1]), cos(e[0], e[2]); rows.append({'anchor':a,'cos_para':round(cp,4),'cos_distract':round(cd,4),'pass':cp > cd})
    return {'triples':rows,'passed':sum(r['pass'] for r in rows),'total':len(rows),'dim':len(e[0]),
            'mean_margin':round(sum(r['cos_para']-r['cos_distract'] for r in rows)/len(rows),4),'seconds':round(time.monotonic()-t0,2)}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--home', required=True); ap.add_argument('--cache', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--only', nargs='*')
    ap.add_argument('--lang', choices=['en','de','both'], default='both', help='English first (user decision 2026-10-09)'); a = ap.parse_args()
    langs = ['en','de'] if a.lang == 'both' else [a.lang]
    home, cache, out = Path(a.home), Path(a.cache), Path(a.out); cache.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    server = next((home/'bin').glob('b*/llama-*/llama-server'))
    spec = json.loads((APP/'specs/cloud-candidates.json').read_text()); results = []
    for c in spec['candidates']:
        if a.only and c['id'] not in a.only: continue
        model = next((home/'models').glob(f"*/{c['local_name']}")) if c.get('installed_role') else fetch(c, cache)
        with open(out/f"{c['id']}.server.log", 'w') as log:
            proc, port, state = serve(server, model, ['--embedding'] if c['kind'] == 'embedding' else [], log)
            res = {'id':c['id'],'role':c['role'],'file':c['local_name'],'size_mb':round(model.stat().st_size/1e6,1),'load':state}
            try:
                if state == 'OK':
                    for lang in langs:
                        if c['kind'] == 'embedding': res[lang] = run_embed(port, EN_TRIPLES if lang == 'en' else TRIPLES)
                        else: res[lang] = run_chat(port, EN if lang == 'en' else FIXTURES + EXTRA)
            finally:
                proc.terminate()
                try: proc.wait(10)
                except subprocess.TimeoutExpired: proc.kill()
        results.append(res); print(json.dumps({'id':res['id'],'load':res['load'],**{l:{k:res[l].get(k) for k in ('passed','total','mean_gen_tps','mean_margin')} for l in langs if l in res}}), flush=True)
    doc = {'purpose':spec['purpose'],'runner':server.parent.name,'platform':os.uname().machine,'cpus':os.cpu_count(),
           'langs':langs,'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),'results':results}
    (out/'candidates.json').write_text(json.dumps(doc, indent=1, ensure_ascii=False))

if __name__ == '__main__':
    main()
