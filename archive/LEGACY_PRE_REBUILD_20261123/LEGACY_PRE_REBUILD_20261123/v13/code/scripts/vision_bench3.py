#!/usr/bin/env python3
"""WP-T16 vision lab step 3: alignment per tile, several objects per image, teacher removal (reliance curve).

Data (synthetic, known ground truth; real photos need the user's permission and are not part of this run):
  single  the 48 WP-N15 scenes (one shape, one colour, one place); teacher captions for whole image + halves are reused
          from the N15 cache when given (--n15-captions), else described anew
  multi   48 scenes with two objects of different colour and shape in two different quadrants; the teacher describes the
          whole image, the four halves and the four quadrants (9 calls per image)
Measurements, 4 folds by image, the teacher is never called at test time (teacher removed):
  tile_find      tile projector (weak tile labels: salient tile -> caption of the smallest described region around it,
                 else BACKGROUND) scores the 16 tiles for "a <colour> <shape>"; hit = best tile in the object's place
                 (half for single, quadrant for multi). Baseline region_locate: the N15b region projector picks the best
                 half/quadrant crop directly.
  teacher        how often the whole-image caption names both objects' colours (multi)
  reliance       multi tile_find when only a fraction of the training images were described by the teacher, without and
                 with self-training (student pseudo-labels for the undescribed training images)
  python3 scripts/vision_bench3.py --mtmd BIN --model GGUF --mmproj GGUF [--embed-server BIN --embed-model GGUF]
                                   [--n15-captions captions.json] --out DIR
Teacher captions are cached in DIR/captions.json.
"""
import argparse, json, platform, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13 import vision  # noqa: E402
import vision_bench as VB  # noqa: E402

QUADS = {'qtl': (0, 0), 'qtr': (1, 0), 'qbl': (0, 1), 'qbr': (1, 1)}
HALVES = VB.HALVES
FRACTIONS = (1., .5, .25, .125)

def draw(d, shape, colour, cx, cy, r):
    col = VB.COLOURS[colour]
    if shape == 'circle': d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=col)
    elif shape == 'square': d.rectangle((cx-r, cy-r, cx+r, cy+r), fill=col)
    else: d.polygon([(cx, cy-r), (cx-r, cy+r), (cx+r, cy+r)], fill=col)

def multi_scenes(seed=29, n=48, size=224):
    from PIL import Image, ImageDraw
    rng = random.Random(seed); out = []
    for i in range(n):
        cols = rng.sample(list(VB.COLOURS), 2); shapes = rng.sample(list(VB.SHAPES), 2); quads = rng.sample(list(QUADS), 2)
        bg = tuple(rng.randint(235, 255) for _ in range(3)); im = Image.new('RGB', (size, size), bg); d = ImageDraw.Draw(im); objs = []
        for c, s, q in zip(cols, shapes, quads):
            qx, qy = QUADS[q]; r = rng.randint(22, 32); cx = size//4+qx*size//2+rng.randint(-10, 10); cy = size//4+qy*size//2+rng.randint(-10, 10)
            draw(d, s, c, cx, cy, r); objs.append({'colour': c, 'shape': s, 'quad': q})
        out.append({'im': im, 'objects': objs, 'key': 'm%02d-' % i+'-'.join(o['colour']+'_'+o['shape']+'_'+o['quad'] for o in objs)})
    return out

def tiles_in(rid_box, size=224, grid=4):
    return [t['region_id'] for t in vision.boxes(size, size, grid) if t['region_id'][0] == 'r' and vision.inside(t['box'], rid_box)]

def region_box(rid, size=224):return next(r['box'] for r in vision.boxes(size, size, 4) if r['region_id'] == rid)

def build_tiles(data, idx, enc, E):
    """Weak tile pairs of the images in idx (only regions with a caption)."""
    import numpy as np
    X = []; texts = []
    for i in idx:
        s = data[i]
        for _, f, text, _ in vision.tile_pairs(s['im'], vision.boxes(224, 224, 4), s['caps']):X.append(f); texts.append(text)
    for t in set(texts) - set(E):E[t] = enc([t])[0]
    return np.stack(X), np.stack([E[t] for t in texts]), texts

def eval_find(p, data, te, enc, E, truth_place):
    """Best tile for each object query; hit if it lies in the object's place box."""
    hit = n = 0; bvec = E.setdefault(vision.BACKGROUND, enc([vision.BACKGROUND])[0])
    for i in te:
        regs = vision.boxes(224, 224, 4)
        for o in data[i]['objects']:
            q = enc(['a %s %s' % (o['colour'], o['shape'])])[0]; tiles, s = vision.tile_scores(p, data[i]['im'], regs, q, bvec)
            best = tiles[int(s.argmax())]['region_id']; hit += best in tiles_in(region_box(truth_place(o))); n += 1
    return hit/n

def eval_region(data, tr, te, enc, E, places, truth_place):
    """N15b baseline: projector on (whole + place-region crops) -> captions; pick the best place crop per query."""
    import numpy as np
    X = []; Y = []
    for i in tr:
        for rid, text in data[i]['caps'].items():
            im = data[i]['im'] if rid == 'g' else data[i]['im'].crop(tuple(region_box(rid)))
            X.append(vision.features(im)); Y.append(E.setdefault(text, enc([text])[0]))
    p = vision.Projector().fit(np.stack(X), np.stack(Y)); hit = n = 0
    for i in te:
        feats = {r: vision.features(data[i]['im'].crop(tuple(region_box(r)))) for r in places}
        for o in data[i]['objects']:
            q = enc(['a %s %s' % (o['colour'], o['shape'])])[0]; sc = {r: float(p(feats[r][None])[0]@q) for r in places}
            hit += max(sc, key=sc.get) == truth_place(o); n += 1
    return hit/n

def self_label(p, data, idx, known_texts, enc, E):
    """Pseudo-labels for undescribed training images: salient tile -> nearest known caption by the student; else BACKGROUND."""
    import numpy as np
    K = sorted(set(known_texts) - {vision.BACKGROUND}); KE = np.stack([E[t] for t in K]); X = []; texts = []
    for i in idx:
        im = data[i]['im']; bg = vision.background(im)
        for t in vision.boxes(224, 224, 4):
            if t['region_id'][0] != 'r': continue
            f = vision.tile_features(im.crop(tuple(t['box']))); X.append(f)
            texts.append(K[int((p(f[None])[0]@KE.T).argmax())] if vision.saliency(im, t['box'], bg) > vision.SALIENT else vision.BACKGROUND)
    return np.stack(X), np.stack([E[t] for t in texts])

def folds_of(n, k=4):
    import numpy as np
    idx = np.arange(n); return [(np.setdiff1d(idx, idx[f::k]), idx[f::k]) for f in range(k)]

def run_encoder(single, multi, enc, seed=13):
    import numpy as np
    E = {}; out = {}
    sp = lambda o: {'left': 'hl', 'right': 'hr', 'top': 'ht', 'bottom': 'hb'}[o['place']]; mp = lambda o: o['quad']
    for name, data, place, places in (('single', single, sp, list(HALVES)), ('multi', multi, mp, list(QUADS))):
        tf = rf = 0; n = 0
        for tr, te in folds_of(len(data)):
            X, Y, _ = build_tiles(data, tr, enc, E); p = vision.Projector().fit(X, Y)
            tf += eval_find(p, data, te, enc, E, place)*len(te); rf += eval_region(data, tr, te, enc, E, places, place)*len(te); n += len(te)
        out[name] = {'tile_find': round(tf/n, 4), 'region_locate': round(rf/n, 4), 'chance': round(1/len(places), 4),
                     'salient_tile_chance': .5 if name == 'multi' else 1.}
    rng = np.random.default_rng(seed); rel = {}
    for f in FRACTIONS:
        a = b = 0; n = 0
        for tr, te in folds_of(len(multi)):
            lab = tr if f >= 1 else rng.choice(tr, max(2, int(round(f*len(tr)))), replace=False); unl = np.setdiff1d(tr, lab)
            X, Y, texts = build_tiles(multi, lab, enc, E); p = vision.Projector().fit(X, Y); a += eval_find(p, multi, te, enc, E, mp)*len(te)
            if len(unl):
                Xu, Yu = self_label(p, multi, unl, texts, enc, E); p2 = vision.Projector().fit(np.vstack([X, Xu]), np.vstack([Y, Yu])); b += eval_find(p2, multi, te, enc, E, mp)*len(te)
            else: b += eval_find(p, multi, te, enc, E, mp)*len(te)
            n += len(te)
        rel[str(f)] = {'teacher_images_per_fold': int(round(f*len(multi)*3/4)), 'tile_find': round(a/n, 4), 'tile_find_self_training': round(b/n, 4)}
    out['reliance_multi'] = rel
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--mtmd', required=True); ap.add_argument('--model', required=True); ap.add_argument('--mmproj', required=True)
    ap.add_argument('--embed-server'); ap.add_argument('--embed-model'); ap.add_argument('--n15-captions'); ap.add_argument('--out', required=True); ap.add_argument('--threads', type=int, default=4); a = ap.parse_args()
    import numpy as np
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); cache = out/'captions.json'
    caps = json.loads(cache.read_text()) if cache.exists() else {}
    if a.n15_captions:
        for k, v in json.loads(Path(a.n15_captions).read_text()).items(): caps.setdefault('s'+k, v)
    teacher = vision.Teacher('/nonexistent', cfg=dict(vision.DEFAULTS, threads=a.threads), binary=a.mtmd, model=a.model, mmproj=a.mmproj); secs = []
    def cap(key, im):
        if key not in caps:
            c = teacher.describe(im); caps[key] = c['text']; secs.append(c['seconds']); cache.write_text(json.dumps(caps, indent=1)); print(key, '|', c['text'], flush=True)
        return caps[key]
    single = VB.scenes()
    for i, s in enumerate(single):
        key = 's%02d-%s-%s-%s' % (i, s['colour'], s['shape'], s['place'])
        s['caps'] = {'g': cap(key, s['im']), **{r: cap(key+'@'+r, s['im'].crop(tuple(region_box(r)))) for r in HALVES}}
        s['objects'] = [{'colour': s['colour'], 'shape': s['shape'], 'place': s['place']}]
    multi = multi_scenes()
    for s in multi:
        s['caps'] = {'g': cap(s['key'], s['im']), **{r: cap(s['key']+'@'+r, s['im'].crop(tuple(region_box(r)))) for r in list(HALVES)+list(QUADS)}}
    both = sum(all(VB.named(s['caps']['g'], o['colour']) for o in s['objects']) for s in multi)/len(multi)
    quad_names = sum(VB.named(s['caps'][o['quad']], o['colour']) for s in multi for o in s['objects'])/(2*len(multi))
    sal = [vision.saliency(s['im'], t['box'], vision.background(s['im'])) for s in multi for t in vision.boxes(224, 224, 4) if t['region_id'][0] == 'r']
    doc = {'schema': 'v13-vision-bench3-v1', 'date': time.strftime('%Y-%m-%d'), 'platform': platform.platform(), 'n_single': len(single), 'n_multi': len(multi),
           'teacher': {'model': Path(a.model).name, 'authority': vision.AUTHORITY, 'seconds_per_call': round(sum(secs)/len(secs), 2) if secs else None, 'new_calls': len(secs),
                       'multi_whole_caption_names_both_colours': round(both, 4), 'multi_quadrant_caption_names_its_colour': round(quad_names, 4)},
           'tiles': {'salient_threshold': vision.SALIENT, 'salient_share_multi': round(float(np.mean(np.asarray(sal) > vision.SALIENT)), 4)},
           'teacher_calls_at_test': 0, 'encoders': {}}
    encs = [('hashed_bow', lambda t: np.stack([vision.hashed_embed(x) for x in t]))]; server = None
    if a.embed_server and a.embed_model: server = VB.EmbedServer(a.embed_server, a.embed_model); encs.append(('embeddinggemma', server))
    try:
        for name, enc in encs:
            doc['encoders'][name] = run_encoder(single, multi, enc); print(name, json.dumps(doc['encoders'][name]), flush=True)
    finally:
        if server: server.close()
    (out/'vision_bench3.json').write_text(json.dumps(doc, indent=1)); print(json.dumps({k: doc[k] for k in ('teacher', 'tiles')}), flush=True)
    return 0

if __name__ == '__main__':
    sys.exit(main())
