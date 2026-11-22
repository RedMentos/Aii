#!/usr/bin/env python3
"""WP-N15 lab bench: synthetic scenes with known ground truth -> RAW EYE features, TEACHER EYE captions, student alignment.

Scenes: one shape (circle/square/triangle) in one colour (red/green/blue/yellow) at one place (left/right/top/bottom),
jittered size and position, optional grey distractor. Measures
  teacher_colour/shape/place  how often the frozen VLM caption names the true attribute (why it is REFERENCE_NOT_FACT)
  alignment                   held-out caption retrieval of the student projector (k-fold), per text encoder
  zero_shot                   student embedding vs prompts "a red shape"/"a circle"/"on the left" (held-out folds)
  raw_probe                   linear probe of the raw features on the true attributes (what the raw eye can carry)
  reconstruction              8x8 thumbnail from the student embedding vs the mean image (measurement only)
  regions (WP-N15b)           teacher also describes the four halves; the student is trained on whole-image + half
                              captions of the training folds and must find the object's half in held-out images by
                              scoring the halves against "a <colour> <shape>" (place via region provenance, not words)
  python3 scripts/vision_bench.py --mtmd BIN --model GGUF --mmproj GGUF [--embed-server BIN --embed-model GGUF] --out DIR
Teacher captions are cached in DIR/captions.json, so reruns only refit.
"""
import argparse, json, platform, random, subprocess, sys, time, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13 import vision  # noqa: E402

COLOURS = {'red': (220, 30, 30), 'green': (30, 170, 40), 'blue': (30, 60, 220), 'yellow': (235, 210, 20)}
SHAPES = ('circle', 'square', 'triangle'); PLACES = ('left', 'right', 'top', 'bottom')
SYN = {'square': ('square', 'rectangle', 'box', 'cube'), 'circle': ('circle', 'dot', 'ball', 'round', 'sphere', 'disc', 'oval'), 'triangle': ('triangle', 'triangular', 'pyramid'),
       'left': ('left',), 'right': ('right',), 'top': ('top', 'upper', 'above'), 'bottom': ('bottom', 'lower', 'below')}

def scene(colour, shape, place, rng, size=224):
    from PIL import Image, ImageDraw
    bg = tuple(rng.randint(235, 255) for _ in range(3)); im = Image.new('RGB', (size, size), bg); d = ImageDraw.Draw(im)
    r = rng.randint(28, 44); c = size//2+rng.randint(-12, 12)
    cx, cy = {'left': (size//4, c), 'right': (3*size//4, c), 'top': (c, size//4), 'bottom': (c, 3*size//4)}[place]
    cx += rng.randint(-8, 8); cy += rng.randint(-8, 8); col = COLOURS[colour]
    if shape == 'circle': d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=col)
    elif shape == 'square': d.rectangle((cx-r, cy-r, cx+r, cy+r), fill=col)
    else: d.polygon([(cx, cy-r), (cx-r, cy+r), (cx+r, cy+r)], fill=col)
    return im

def scenes(seed=13):
    rng = random.Random(seed); out = []
    for colour in COLOURS:
        for shape in SHAPES:
            for place in PLACES: out.append({'colour': colour, 'shape': shape, 'place': place, 'im': scene(colour, shape, place, rng)})
    rng.shuffle(out); return out

def named(caption, value):
    words = set(vision.WORD.findall(caption.lower())); return any(w in words for w in SYN.get(value, (value,)))

class EmbedServer:
    def __init__(self, binary, model, port=18093):
        self.url = 'http://127.0.0.1:%d' % port
        self.p = subprocess.Popen([binary, '-m', model, '--embedding', '--port', str(port), '-c', '512', '-t', '4', '--no-webui', '--log-disable'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(240):
            try: urllib.request.urlopen(self.url+'/health', timeout=1); return
            except OSError: time.sleep(.5)
        raise RuntimeError('embedding server did not start')
    def __call__(self, texts):
        import numpy as np
        req = urllib.request.Request(self.url+'/v1/embeddings', json.dumps({'input': ['task: sentence similarity | query: '+t for t in texts]}).encode(), {'Content-Type': 'application/json'})
        data = json.load(urllib.request.urlopen(req, timeout=600))['data']; v = np.asarray([r['embedding'] for r in sorted(data, key=lambda r: r['index'])], dtype=np.float32)
        return v/np.maximum(1e-8, np.linalg.norm(v, axis=1, keepdims=True))
    def close(self): self.p.kill(); self.p.wait()

def zero_shot(X, Y, truth, enc, folds=4):
    """Held-out: fit the projector on the other folds, then pick the attribute prompt nearest to the student embedding."""
    import numpy as np
    prompts = {'colour': {c: 'a %s shape' % c for c in COLOURS}, 'shape': {s: 'a %s' % s for s in SHAPES}, 'place': {p: 'an object on the %s' % p for p in PLACES}}
    P = {k: (list(v), enc(list(v.values()))) for k, v in prompts.items()}; hits = {k: 0 for k in prompts}; n = len(X); idx = np.arange(n)
    for f in range(folds):
        te = idx[f::folds]; tr = np.setdiff1d(idx, te); p = vision.Projector().fit(X[tr], Y[tr]); Z = p(X[te])
        for k, (names, E) in P.items():
            pred = (Z@E.T).argmax(1); hits[k] += sum(names[j] == truth[i][k] for j, i in zip(pred, te))
    return {k: {'accuracy': v/n, 'chance': 1/len(prompts[k])} for k, v in hits.items()}

HALVES = {'hl': 'left', 'hr': 'right', 'ht': 'top', 'hb': 'bottom'}

def crop(im, rid):
    w, h = im.size; box = next(r['box'] for r in vision.boxes(w, h, 4) if r['region_id'] == rid); return im.crop(tuple(box))

def region_place(data, enc, folds=4):
    """Held-out by image: fit on (whole + half) pairs of the other folds, predict the half that best matches the object."""
    import numpy as np
    feats = [{rid: vision.features(crop(s['im'], rid) if rid != 'g' else s['im']) for rid in ['g', *HALVES]} for s in data]
    capemb = [dict(zip(['g', *HALVES], enc([s['caption']]+[s['half_captions'][r] for r in HALVES]))) for s in data]
    n = len(data); idx = np.arange(n); hit = 0; axis_hit = 0
    for f in range(folds):
        te = idx[f::folds]; tr = np.setdiff1d(idx, te)
        X = np.stack([feats[i][r] for i in tr for r in feats[i]]); Y = np.stack([capemb[i][r] for i in tr for r in feats[i]]); p = vision.Projector().fit(X, Y)
        for i in te:
            q = enc(['a %s %s' % (data[i]['colour'], data[i]['shape'])])[0]; sc = {HALVES[r]: float(p(feats[i][r][None])[0]@q) for r in HALVES}
            hit += max(sc, key=sc.get) == data[i]['place']
            pair = ('left', 'right') if data[i]['place'] in ('left', 'right') else ('top', 'bottom'); axis_hit += max(pair, key=sc.get) == data[i]['place']
    return {'place_top1_of_4': hit/n, 'chance': .25, 'place_within_axis': axis_hit/n, 'axis_chance': .5}

def raw_probe(X, truth, folds=4):
    import numpy as np
    out = {}; n = len(X); idx = np.arange(n)
    for k, names in (('colour', list(COLOURS)), ('shape', list(SHAPES)), ('place', list(PLACES))):
        Y = np.eye(len(names))[[names.index(t[k]) for t in truth]]; hit = 0
        for f in range(folds):
            te = idx[f::folds]; tr = np.setdiff1d(idx, te); p = vision.Projector(1.).fit(X[tr], Y[tr])
            hit += int(((p._x(X[te])@p.W).argmax(1) == Y[te].argmax(1)).sum())
        out[k] = {'accuracy': hit/n, 'chance': 1/len(names)}
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--mtmd', required=True); ap.add_argument('--model', required=True); ap.add_argument('--mmproj', required=True)
    ap.add_argument('--embed-server'); ap.add_argument('--embed-model'); ap.add_argument('--out', required=True); ap.add_argument('--threads', type=int, default=4); a = ap.parse_args()
    import numpy as np
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); cache = out/'captions.json'
    caps = json.loads(cache.read_text()) if cache.exists() else {}
    data = scenes(); teacher = vision.Teacher('/nonexistent', cfg=dict(vision.DEFAULTS, threads=a.threads), binary=a.mtmd, model=a.model, mmproj=a.mmproj); secs = []
    for i, s in enumerate(data):
        key = '%02d-%s-%s-%s' % (i, s['colour'], s['shape'], s['place'])
        if key not in caps:
            c = teacher.describe(s['im']); caps[key] = c['text']; secs.append(c['seconds']); cache.write_text(json.dumps(caps, indent=1))
            print(key, '|', c['text'], flush=True)
        s['caption'] = caps[key]; s['half_captions'] = {}
        for rid in HALVES:
            hk = key+'@'+rid
            if hk not in caps:
                c = teacher.describe(crop(s['im'], rid)); caps[hk] = c['text']; secs.append(c['seconds']); cache.write_text(json.dumps(caps, indent=1))
            s['half_captions'][rid] = caps[hk]
    truth = [{k: s[k] for k in ('colour', 'shape', 'place')} for s in data]
    X = np.stack([vision.features(s['im']) for s in data]); T = np.stack([vision.thumbnail(s['im']) for s in data]); texts = [s['caption'] for s in data]
    doc = {'schema': 'v13-vision-bench-v1', 'date': time.strftime('%Y-%m-%d'), 'platform': platform.platform(), 'n_images': len(data), 'raw_eye_dim': int(X.shape[1]),
           'teacher': {'model': Path(a.model).name, 'mmproj': Path(a.mmproj).name, 'authority': vision.AUTHORITY, 'prompt': vision.PROMPT,
                       'seconds_per_image': round(sum(secs)/len(secs), 2) if secs else None,
                       'names_true': {k: sum(named(s['caption'], s[k]) for s in data)/len(data) for k in ('colour', 'shape', 'place')},
                       'half_names_colour': {'object_half': sum(named(s['half_captions'][r], s['colour']) for s in data for r in HALVES if HALVES[r] == s['place'])/len(data),
                                             'opposite_half': sum(named(s['half_captions'][r], s['colour']) for s in data for r in HALVES if HALVES[r] == {'left': 'right', 'right': 'left', 'top': 'bottom', 'bottom': 'top'}[s['place']])/len(data)}},
           'raw_probe': raw_probe(X, truth), 'encoders': {}}
    encs = [('hashed_bow', lambda t: np.stack([vision.hashed_embed(x) for x in t]))]; server = None
    if a.embed_server and a.embed_model: server = EmbedServer(a.embed_server, a.embed_model); encs.append(('embeddinggemma', server))
    try:
        for name, enc in encs:
            Y = enc(texts); doc['encoders'][name] = {'alignment': vision.crossval(X, Y, T), 'zero_shot': zero_shot(X, Y, truth, enc), 'regions': region_place(data, enc)}
            print(name, json.dumps(doc['encoders'][name]), flush=True)
    finally:
        if server: server.close()
    (out/'vision_bench.json').write_text(json.dumps(doc, indent=1)); print(json.dumps({k: doc[k] for k in ('teacher', 'raw_probe')}), flush=True)
    return 0

if __name__ == '__main__':
    sys.exit(main())
