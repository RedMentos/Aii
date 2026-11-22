#!/usr/bin/env python3
"""WP-Z12a / G-SELF-WORLD-005 on real cases: own corollary vs. a real, independent world process on real files.

Self acts through the real WP-K path: ToolRegistry 'sandbox_note' (WRITE_LOCAL) -> PROPOSED with preview -> human
approval (the harness approves, sometimes late) -> Transactions -> atomic file write in <home>/data/tool_sandbox.
Before each approval the real SelfSystem (v13/selfmodel.py) issues a SelfCorollary whose predictions come from the
preview: content hash of the target file, tool status EXECUTED, and for a CREATE the declared side-effect channel
'listing'. A separate OS process ("world", own seed, own clock) writes, removes and blocks files in the same folder on
its own schedule. An observer thread polls the folder (20 ms) and hands every change to SelfSystem.observe() at the time
it is seen. Ground truth comes afterwards from the two write logs (content hashes), never from the classifier.

Episode kinds (one per 2 s slot): own, world, interference (world overwrites the own target 0-300 ms after the own
write), fail (world puts a directory at the own target before the write -> the real write fails), ambiguous (two own
proposals with the same content for the same file), side_effect (own CREATE changes the listing), delayed (approval
arrives after the corollary window, < 3x window).
Controls on the same observations: no corollary (attribute([], obs)) and timing only (any open own action on that
channel = SELF). Criteria K1-K6: docs/proofs/continuation-20261026/z12a-self-world-real/PREREG.md.
Usage: z12a_self_world_real.py <out.json> [--seeds 61,62,63] [--episodes 70]   |   z12a_self_world_real.py --world <schedule.json>
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SLOT = 2.0      # seconds per episode
WINDOW = 0.4    # corollary window; DELAY_FACTOR 3 -> delayed outcomes count up to 1.2 s
POLL = 0.02
KINDS = ('own', 'world', 'interference', 'fail', 'ambiguous', 'side_effect', 'delayed')
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()[:16]


# -- world process ----------------------------------------------------------------------------------------------
def world_main(schedule_path):
    """Independent process: executes its schedule against wall-clock time and logs what it actually did."""
    sch = json.loads(Path(schedule_path).read_text()); root = Path(sch['root']); log = open(sch['log'], 'a')
    for it in sch['items']:
        delay = sch['t0']+it['at']-time.time()
        if delay > 0: time.sleep(delay)
        p = root/(it['name']+'.txt'); rec = {'name': it['name'], 'op': it['op'], 'pid': os.getpid()}
        try:
            if it['op'] == 'write':
                tmp = p.with_suffix('.w%d' % os.getpid()); tmp.write_text(it['text']); os.replace(tmp, p); rec['sha'] = sha(it['text'])
            elif it['op'] == 'block':  # a directory where the own target file should be: the own write fails for real
                if p.is_file(): p.unlink()
                p.mkdir(exist_ok=True); rec['sha'] = 'DIR'
            elif it['op'] == 'remove':
                p.unlink(missing_ok=True); rec['sha'] = None
        except OSError as exc:
            rec['error'] = type(exc).__name__
        rec['t'] = time.time(); log.write(json.dumps(rec)+'\n'); log.flush()
    log.close()


# -- observer ---------------------------------------------------------------------------------------------------
def snapshot(root):
    files, count = {}, 0
    for e in os.scandir(root):
        if not e.name.endswith('.txt'): continue
        if e.is_dir(): files[e.name[:-4]] = 'DIR'; continue
        count += 1
        try: files[e.name[:-4]] = sha(Path(e.path).read_text())
        except (OSError, UnicodeDecodeError): pass
    return files, count


class Observer(threading.Thread):
    def __init__(self, root, handle):
        super().__init__(daemon=True); self.root = root; self.handle = handle; self.stop = threading.Event()
        self.prev = snapshot(root)
    def run(self):
        while not self.stop.is_set():
            files, count = snapshot(self.root); t = time.time(); pf, pc = self.prev
            obs = [{'channel': 'file:'+n, 'value': v, 't': t} for n, v in files.items() if pf.get(n) != v]
            obs += [{'channel': 'file:'+n, 'value': None, 't': t} for n in pf if n not in files]
            if count != pc: obs.append({'channel': 'listing', 'value': count, 't': t})
            self.prev = (files, count)
            if obs: self.handle(obs)
            time.sleep(POLL)


# -- one seed ---------------------------------------------------------------------------------------------------
def plan(seed, episodes):
    rng = random.Random(seed); kinds = [KINDS[i % len(KINDS)] for i in range(episodes)]; rng.shuffle(kinds)
    own, world = [], []
    for k, kind in enumerate(kinds):
        base = 1.0+k*SLOT; name = 'e%03d' % k; txt = lambda tag: '%s-%s-%d' % (tag, name, rng.randrange(10**9))
        if kind == 'own': own.append({'ep': k, 'kind': kind, 'at': base+.2, 'name': name, 'text': txt('self')})
        elif kind == 'world': world.append({'ep': k, 'at': base+.2+rng.random()*.6, 'op': 'write', 'name': name, 'text': txt('world')})
        elif kind == 'interference':
            own.append({'ep': k, 'kind': kind, 'at': base+.2, 'name': name, 'text': txt('self')})
            world.append({'ep': k, 'at': base+.2+rng.random()*.3, 'op': 'write', 'name': name, 'text': txt('world')})
        elif kind == 'fail':
            world.append({'ep': k, 'at': base+.1, 'op': 'block', 'name': name})
            own.append({'ep': k, 'kind': kind, 'at': base+.5, 'name': name, 'text': txt('self')})
        elif kind == 'ambiguous':
            t = txt('self'); own.append({'ep': k, 'kind': kind, 'at': base+.2, 'name': name, 'text': t, 'twin': True})
        elif kind == 'side_effect': own.append({'ep': k, 'kind': kind, 'at': base+.2, 'name': 'new_'+name, 'text': txt('self'), 'create': True})
        elif kind == 'delayed': own.append({'ep': k, 'kind': kind, 'at': base+.1, 'name': name, 'text': txt('self'), 'approve_after': WINDOW*(1.25+rng.random()*1.5)})
    return kinds, own, world


def run_seed(seed, episodes):
    from v13.runtime import Runtime
    from v13 import selfmodel as S, neuromod as N
    from v13.agi.tools import ToolRegistry
    kinds, own_plan, world_plan = plan(seed, episodes)
    with tempfile.TemporaryDirectory(prefix='v13-z12a-') as tmp:
        home = Path(tmp)/'home'; r = Runtime(home); root = home/'data/tool_sandbox'; root.mkdir(parents=True, exist_ok=True)
        for k in range(episodes):  # existing notes (REPLACE targets); created before the observer starts
            (root/('e%03d.txt' % k)).write_text('initial-%d' % k)
        reg = ToolRegistry(r.store); reg.enable('sandbox_note')
        selfsys = S.SelfSystem(r, None, N.Neuromod(r.store)); ev = r.store.event(r.session, 'z12a seed %d' % seed)['event_id']
        lock = threading.Lock(); seen = []; own_log = []; open_cor = {}
        def handle(obs):
            with lock:
                now = time.time()
                for aid in [a for a, c in open_cor.items() if now > c['issued_at']+WINDOW*S.DELAY_FACTOR+.2]:
                    open_cor.pop(aid)
                snap = [dict(c) for c in open_cor.values()]
                out = selfsys.observe(ev, obs, close=[])
                for o, a in zip(obs, out):
                    timing = any(o['channel'] in [p['channel'] for p in c['predicted_observations']]+c['affected'] and c['issued_at'] <= o['t'] for c in snap)
                    seen.append({'obs': o, 'cls': a['class'], 'reason': a['reason'], 'no_corollary': S.attribute([], o)['class'],
                                 'timing_only': 'SELF' if timing else 'EXTERNAL', 'open': [c['action_id'] for c in snap]})
        sch_path = Path(tmp)/'world.json'; wlog = Path(tmp)/'world.jsonl'; t0 = time.time()+1.5
        sch_path.write_text(json.dumps({'root': str(root), 'log': str(wlog), 't0': t0, 'items': sorted(world_plan, key=lambda x: x['at'])}))
        world = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--world', str(sch_path)])
        obsv = Observer(root, handle); obsv.start()
        pending = sorted(own_plan, key=lambda x: x['at']); approvals = []
        try:
            while pending or approvals:
                nxt = min([p['at'] for p in pending[:1]]+[a[0] for a in approvals])
                d = t0+nxt-time.time()
                if d > 0: time.sleep(min(d, .05)); continue
                if approvals and approvals[0][0] <= nxt:
                    _, item, txs = approvals.pop(0); approve(reg, item, txs, own_log, handle); continue
                item = pending.pop(0); txs = []
                for j in range(2 if item.get('twin') else 1):
                    tx = reg.call('sandbox_note', {'name': item['name'], 'text': item['text']}, origin='USER'); pv = tx.get('preview') or {}
                    preds = [{'channel': 'file:'+item['name'], 'value': sha(item['text'])}, {'channel': 'status:'+item['name'], 'value': 'EXECUTED'}]
                    aid = '%s#%d' % (tx['id'], j)
                    with lock:
                        c = selfsys.issue(ev, aid, 'sandbox_note %s %s' % (pv.get('effect'), item['name']), preds,
                                          affected=['listing'] if pv.get('effect') == 'CREATE' else [], uncertainty=.2, window_s=WINDOW)
                        open_cor[aid] = {'action_id': aid, 'issued_at': c['issued_at'], 'predicted_observations': preds,
                                         'affected': ['listing'] if pv.get('effect') == 'CREATE' else []}
                    txs.append((tx, aid))
                approvals.append((item['at']+item.get('approve_after', .0), item, txs)); approvals.sort(key=lambda a: a[0])
            time.sleep(WINDOW*S.DELAY_FACTOR+.5)
        finally:
            world.wait(timeout=episodes*SLOT+30); obsv.stop.set(); obsv.join(2)
            modulators = r.store.one("SELECT count(*) AS n FROM packets WHERE kind='ModulatorPacket' AND event_id=?", (ev,))['n']
            r.close()
        world_log = [json.loads(l) for l in wlog.read_text().splitlines()] if wlog.exists() else []
    return {'seed': seed, 'kinds': kinds, 'own_log': own_log, 'world_log': world_log, 'observations': seen, 'modulator_packets': modulators}


def approve(reg, item, txs, own_log, handle):
    for tx, aid in txs:
        t = reg.approve(tx['id']); st = t['status']
        own_log.append({'ep': item['ep'], 'kind': item['kind'], 'name': item['name'], 'sha': sha(item['text']), 'status': st, 'action_id': aid,
                        't_done': time.time(), 'error': str(t.get('error'))[:120] if t.get('error') else None})
        handle([{'channel': 'status:'+item['name'], 'value': st, 't': time.time()}])


# -- ground truth + scoring -------------------------------------------------------------------------------------
def truth(o, res):
    """Who caused the observed value: own / world / both / unknown, from the write logs only."""
    ch, v = o['channel'], o['value']
    if ch.startswith('status:'): return 'own'
    if ch == 'listing':
        return 'own' if any(x['name'].startswith('new_') and abs(x['t_done']-o['t']) < 1.5 for x in res['own_log']) else 'world'
    name = ch[5:]
    o_ = any(x['name'] == name and x['sha'] == v and x['status'] == 'EXECUTED' for x in res['own_log'])
    w_ = any(x['name'] == name and x.get('sha') == v for x in res['world_log']) or (v in ('DIR', None))
    return 'both' if o_ and w_ else 'own' if o_ else 'world' if w_ else 'unknown'


def score(results):
    rows = []
    for res in results:
        kind_of = {('e%03d' % k): kd for k, kd in enumerate(res['kinds'])}
        kind_of.update({('new_e%03d' % k): kd for k, kd in enumerate(res['kinds'])})
        for s in res['observations']:
            o = s['obs']; ch = o['channel']; name = ch.split(':', 1)[1] if ':' in ch else None
            rows.append({'seed': res['seed'], 'channel': ch.split(':')[0], 'kind': kind_of.get(name, 'listing'), 'truth': truth(o, res),
                         'cls': s['cls'], 'reason': s['reason'], 'no_corollary': s['no_corollary'], 'timing_only': s['timing_only']})
    rate = lambda xs, f: (round(sum(map(f, xs))/len(xs), 4) if xs else None)
    file_rows = [r for r in rows if r['channel'] == 'file' and r['truth'] in ('own', 'world')]
    world_rows = [r for r in file_rows if r['truth'] == 'world']; own_rows = [r for r in file_rows if r['truth'] == 'own' and r['kind'] != 'ambiguous']
    interf = [r for r in world_rows if r['kind'] == 'interference']
    k1 = rate(world_rows, lambda r: r['cls'] == 'SELF'); k2 = rate(own_rows, lambda r: r['cls'] == 'EXTERNAL')
    amb = [r for r in file_rows if r['kind'] == 'ambiguous' and r['truth'] == 'own']; k4 = rate(amb, lambda r: r['cls'] == 'UNCLEAR')
    side = [r for r in rows if r['channel'] == 'listing' and r['truth'] == 'own']; k5 = rate(side, lambda r: r['cls'] == 'UNCLEAR')
    delayed = [r for r in own_rows if r['kind'] == 'delayed']
    no_k2 = rate(own_rows, lambda r: r['no_corollary'] == 'EXTERNAL'); tim_k1 = rate(interf, lambda r: r['timing_only'] == 'SELF')
    cor_k1i = rate(interf, lambda r: r['cls'] == 'SELF')
    stat = [x for res in results for x in res['own_log']]
    fail = [x for x in stat if x['kind'] == 'fail']
    return rows, {'n_observations': len(rows), 'n_world_file': len(world_rows), 'n_own_file': len(own_rows), 'n_interference_world': len(interf),
                  'n_ambiguous': len(amb), 'n_side_effect': len(side), 'n_delayed': len(delayed), 'n_fail_actions': len(fail),
                  'false_self_on_world': k1, 'false_external_on_own': k2, 'ambiguous_unclear': k4, 'side_effect_unclear': k5,
                  'delayed_self': rate(delayed, lambda r: r['cls'] == 'SELF'), 'no_corollary_false_external_on_own': no_k2,
                  'timing_only_false_self_on_interference': tim_k1, 'corollary_false_self_on_interference': cor_k1i,
                  'fail_actions_failed': rate(fail, lambda x: x['status'] == 'FAILED'),
                  'unknown_truth': sum(r['truth'] in ('unknown', 'both') for r in rows)}


def criteria(m, status_mixed):
    c = {'K1_false_self_on_world_le_5pct': m['false_self_on_world'] is not None and m['false_self_on_world'] <= .05,
         'K2_false_external_on_own_le_5pct': m['false_external_on_own'] is not None and m['false_external_on_own'] <= .05,
         'K3_failed_own_action_mixed_ge_90pct': status_mixed is not None and status_mixed >= .9,
         'K4_ambiguous_unclear_ge_90pct': m['ambiguous_unclear'] is not None and m['ambiguous_unclear'] >= .9,
         'K5_side_effect_unclear_ge_90pct': m['side_effect_unclear'] is not None and m['side_effect_unclear'] >= .9,
         'K6_controls_worse': (m['no_corollary_false_external_on_own'] or 0)-(m['false_external_on_own'] or 0) >= .5
                              and (m['timing_only_false_self_on_interference'] or 0)-(m['corollary_false_self_on_interference'] or 0) >= .2}
    return c, ('Z12A_SELF_WORLD_REAL_PASS' if all(c.values()) else 'Z12A_SELF_WORLD_REAL_FAIL')


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('out', nargs='?'); ap.add_argument('--world')
    ap.add_argument('--seeds', default='61,62,63'); ap.add_argument('--episodes', type=int, default=70); a = ap.parse_args(argv)
    if a.world: world_main(a.world); return 0
    from v13.common import atomic_write
    results = [run_seed(int(s), a.episodes) for s in a.seeds.split(',')]
    rows, m = score(results)
    status = [s for res in results for s in res['observations'] if s['obs']['channel'].startswith('status:')]
    fail_names = {x['name'] for res in results for x in res['own_log'] if x['kind'] == 'fail'}
    st_fail = [s for s in status if s['obs']['channel'][7:] in fail_names and s['obs']['value'] == 'FAILED']
    status_mixed = round(sum(s['cls'] == 'MIXED' for s in st_fail)/len(st_fail), 4) if st_fail else None
    m['failed_status_mixed'] = status_mixed; m['n_failed_status'] = len(st_fail)
    m['modulator_packets'] = sum(r['modulator_packets'] for r in results)
    crit, verdict = criteria(m, status_mixed)
    doc = {'kind': 'V13_Z12A_SELF_WORLD_REAL', 'seeds': a.seeds, 'episodes': a.episodes, 'window_s': WINDOW, 'poll_s': POLL,
           'metrics': m, 'criteria': crit, 'verdict': verdict, 'rows': rows, 'runs': results, 'phone_measured': False,
           'prereg': 'docs/proofs/continuation-20261026/z12a-self-world-real/PREREG.md',
           'claim_limit': 'real files, real WP-K tool path, real separate world process, cloud timing; no language model, no phone sensors'}
    atomic_write(Path(a.out), json.dumps(doc, indent=1))
    print(json.dumps({'verdict': verdict, 'criteria': crit, 'metrics': m}, indent=1)); return 0


if __name__ == '__main__':
    sys.exit(main())
