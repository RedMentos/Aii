#!/usr/bin/env python3
"""WP-N12: extract every research knob of blueprint §49–§78 into specs/blueprint-knobs.json.

Lines like `A1.context_shift_gain = 0.35`, `C2.primary_rung = 4L`, `SKILL.shadow_cycles = 10 [BOOT]` and
`A1.segment_size [BOOT/TUNE]` become entries with section, raw value, numeric value (if any) and tags.
The §78 Age-0 bar profile becomes AGE0.<group>.<label> entries. `--suggest` proposes code mappings by
matching knob suffixes against module-level dicts; mappings are curated in specs/knob-map.json.
"""
import argparse, hashlib, importlib, json, re, sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
CANON = 'V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md'
KNOB = re.compile(r'^\s*([A-Z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+)\s*(=\s*(.*?))?\s*(\[[A-Z/_ ]+\])?\s*$')
NUM = re.compile(r'^[-+]?\d+(?:\.\d+)?')
BAR = re.compile(r'^\s{2}(\S.*?)\s{2,}[█░]+\s+(\d+\.\d+)\s*$')
MODULES = ('v13.attention', 'v13.episodes', 'v13.context_os', 'v13.focal', 'v13.effort', 'v13.neuromod', 'v13.guards', 'v13.age', 'v13.plasticity', 'v13.sleep')

def canon_path():
    for p in (APP/'docs/canon'/CANON, APP.parent/'blueprint'/CANON):
        if p.exists(): return p
    raise SystemExit('canon missing')

def parse(text):
    out = []; section = None; title = None; group = None; in_78 = False
    for no, line in enumerate(text.splitlines(), 1):
        h = re.match(r'^(#{1,3}) (\d+(?:\.\d+)*[A-Z]?)\.? (.*)', line)
        if h:
            section = h.group(2); title = h.group(3).strip(); in_78 = section == '78'
            continue
        if section is None: continue
        major = int(re.match(r'\d+', section).group())
        if not 49 <= major <= 78: continue
        if in_78:
            if re.match(r'^[A-Z][A-Z0-9 /_-]+$', line.strip()) and line.strip() and not line.startswith(' '): group = re.sub(r'\W+', '_', line.strip()).strip('_')
            b = BAR.match(line)
            if b and group:
                label = re.sub(r'\W+', '_', b.group(1).strip().lower()).strip('_')
                out.append({'id': f'AGE0.{group}.{label}', 'section': section, 'title': title, 'raw': b.group(2), 'value': float(b.group(2)), 'tags': ['AGE0_PROFILE'], 'line': no})
            continue
        m = KNOB.match(line)
        if not m or '(' in line: continue
        raw = (m.group(3) or '').strip(); tags = [t.strip() for t in (m.group(4) or '').strip('[]').split('/') if t.strip()]
        tail = re.search(r'\[([A-Z/_ ]+)\]', raw)
        if tail: tags += [t.strip() for t in tail.group(1).split('/')]; raw = raw[:tail.start()].strip()
        n = NUM.match(raw); value = float(n.group()) if n else None
        out.append({'id': m.group(1), 'section': section, 'title': title, 'raw': raw or None, 'value': value, 'tags': sorted(set(tags)), 'line': no})
    seen = {}
    for k in out: seen.setdefault(k['id'], []).append(k)
    for kid, rows in seen.items():
        if len(rows) > 1:
            for i, r in enumerate(rows): r['duplicate_index'] = i  # same id declared twice (later sections may override)
    return out

def dicts():
    for name in MODULES:
        try: mod = importlib.import_module(name)
        except Exception: continue
        for attr, val in vars(mod).items():
            if attr.isupper() and isinstance(val, dict) and val and all(isinstance(k, str) for k in val):
                yield name, attr, val

def suggest(knobs):
    found = {}; table = list(dicts())
    for k in knobs:
        if k['value'] is None: continue
        suffix = k['id'].split('.', 1)[1]
        variants = {suffix, re.sub(r'_gain$', '', suffix), re.sub(r'_boundary_gain$', '', suffix), re.sub(r'^boundary_', '', suffix),
                    re.sub(r'_change_boundary_gain$', '_shift', suffix), re.sub(r'_boundary_gain$', '', suffix).replace('goal_change', 'goal_shift')}
        hits = [(mod, attr, key) for mod, attr, d in table for key in d if key in variants and isinstance(d[key], (int, float)) and not isinstance(d[key], bool)]
        prefix = k['id'].split('.')[0].upper()
        pref = [h for h in hits if h[1] == prefix or h[1].startswith(prefix)]
        pick = pref if len(pref) == 1 else (hits if len(hits) == 1 else [])
        if pick: found[k['id']] = {'module': pick[0][0], 'attr': pick[0][1], 'key': pick[0][2]}
    return found

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--suggest', action='store_true'); a = ap.parse_args()
    p = canon_path(); text = p.read_text(encoding='utf-8'); knobs = parse(text)
    doc = {'schema': 'V13_BLUEPRINT_KNOBS_V1', 'canon': CANON, 'canon_sha256': hashlib.sha256(text.encode()).hexdigest(), 'sections': '49-78', 'count': len(knobs), 'knobs': knobs}
    (APP/'specs/blueprint-knobs.json').write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'knobs': len(knobs), 'numeric': sum(k['value'] is not None for k in knobs)}))
    if a.suggest: print(json.dumps(suggest(knobs), indent=1))

if __name__ == '__main__':
    main()
