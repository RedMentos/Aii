#!/usr/bin/env python3
"""WP-N7 rest (§8.5, §8.6, G6B): measure native llama.cpp cache primitives on the pinned bodies.

Isolated candidate bench: starts its own llama-server processes with the same base flags as `v13/runners.py`
(-c 2048 -np 1 -t 4 -b/-ub 128 -ngl 0 --no-warmup) plus the flag under test, and never touches a V13 home or
the frozen runtime. Each experiment is compared against a cold reference (prompt cache off, no checkpoints,
cache_prompt=false) on the identical prompt with greedy decoding; exactness classes are defined in
native_cache_primitives.classify_exactness: same greedy tokens required; logprob drift judged against the measured
batch-split noise floor of re-prefill itself (tol_close = max(0.05, 2 x floor)).

Experiments (per body): prefix, edit_replay (default vs dense checkpoints), switch (host prompt cache on/off),
persist (slot save -> server restart -> restore), shift (--cache-reuse), kvquant (q8_0 vs f16 K/V).

  python3 scripts/native_cache_bench.py --bin DIR/llama-server --model C3_LANGUAGE=c3.gguf --model B1_FINE=b1.gguf \
      --model B2_GIST=b2.gguf --out bench-results/native-cache-20261012
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_cache_primitives as P  # noqa: E402

BASE = ['-c', '2048', '-np', '1', '-t', '4', '-tb', '4', '-b', '128', '-ub', '128', '-ngl', '0', '--no-warmup', '--no-webui', '-lv', '4']
COLD = ['--cache-ram', '0', '--ctx-checkpoints', '0']
N_PRED = 24

SOURCE = ("Field notes, Graz clinic, week 41. Lena Hofer works as a nurse on ward 3B. Her weekday shift starts at 06:30 "
          "and ends at 15:00; on Saturdays she covers the 07:00 to 13:00 slot. The ward has 24 beds, of which 6 are "
          "reserved for post-operative patients. The head nurse is Martin Klein, who joined in March 2019. Medication "
          "rounds happen at 08:00, 12:00, 18:00 and 22:00. The clinic cafeteria closes at 19:30. Visitors must sign in at "
          "the east entrance between 10:00 and 20:00. The pharmacy code for ward 3B is PH-3B-7741. Emergency drills take "
          "place on the first Tuesday of every month at 14:00. Parking for staff is in garage level -2, spaces 40 to 88. ")
SYSTEM = 'You are a concise assistant. Answer in one sentence using only the notes.\n\nNotes:\n' + SOURCE * 2
TURNS = [('When does Lena start on weekdays?', 'Lena starts at 06:30 on weekdays.'),
         ('Who is the head nurse?', 'The head nurse is Martin Klein.'),
         ('How many beds are post-operative?', 'Six of the 24 beds are post-operative.'),
         ('What is the pharmacy code?', 'The pharmacy code is PH-3B-7741.'),
         ('When are medication rounds?', 'Rounds are at 08:00, 12:00, 18:00 and 22:00.'),
         ('Where do staff park?', 'Staff park on garage level -2, spaces 40 to 88.')]
EDIT_AT = 2  # edit turn index 2 (middle of the conversation)
OTHER = ('Recipe card: whisk two eggs with 200 ml milk and 120 g flour, rest the batter ten minutes, fry thin pancakes '
         'in butter over medium heat, fill with apricot jam, roll, and dust with sugar. Serves four. ') * 6


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


class Server:
    def __init__(self, binary, model, flags, log, slot_dir=None):
        self.port = free_port(); self.log = Path(log)
        cmd = [str(binary), '-m', str(model), '--host', '127.0.0.1', '--port', str(self.port)] + BASE + list(flags)
        if slot_dir:
            cmd += ['--slot-save-path', str(slot_dir)]
        self.cmd = cmd
        env = dict(os.environ, LD_LIBRARY_PATH=str(Path(binary).parent))
        self.fh = open(self.log, 'ab')
        self.proc = subprocess.Popen(cmd, stdout=self.fh, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        t0 = time.monotonic()
        while time.monotonic() - t0 < 300:
            if self.proc.poll() is not None:
                raise RuntimeError(f'server exited rc={self.proc.returncode}, see {self.log}')
            try:
                if json.loads(self.get('/health')).get('status') == 'ok':
                    break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError('server did not become healthy')
        self.load_s = round(time.monotonic() - t0, 2)

    def get(self, path):
        return urllib.request.urlopen(f'http://127.0.0.1:{self.port}{path}', timeout=600).read()

    def post(self, path, body):
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', data=json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json'})
        return json.loads(urllib.request.urlopen(req, timeout=900).read())

    def render(self, msgs):
        # identical to v13/runners.py: generation prompt on, Qwen3.5 hidden thinking off (LFM ignores the flag)
        return self.post('/apply-template', {'messages': msgs, 'add_generation_prompt': True,
                                             'chat_template_kwargs': {'enable_thinking': False}})['prompt']

    def ntok(self, text):
        return len(self.post('/tokenize', {'content': text})['tokens'])

    def complete(self, prompt, cache=True, n=N_PRED):
        t0 = time.monotonic()
        d = self.post('/completion', {'prompt': prompt, 'n_predict': n, 'temperature': 0, 'n_probs': 1, 'cache_prompt': cache,
                                      'id_slot': 0, 'return_tokens': True})
        cp = d.get('completion_probabilities') or []
        tm = d.get('timings', {})
        return {'tokens': [c['id'] for c in cp] or d.get('tokens'), 'logprobs': [c['logprob'] for c in cp],
                'text': d.get('content'), 'prompt_n': tm.get('prompt_n'), 'cache_n': tm.get('cache_n'),
                'prompt_ms': tm.get('prompt_ms'), 'wall_ms': round((time.monotonic() - t0) * 1000, 1)}

    def mem(self):
        st = Path(f'/proc/{self.proc.pid}/status').read_text()
        g = lambda k: int(next(l.split()[1] for l in st.splitlines() if l.startswith(k))) // 1024
        return {'rss_mib': g('VmRSS'), 'hwm_mib': g('VmHWM')}

    def stop(self):
        m = None
        try:
            m = self.mem()
        except Exception:
            pass
        if self.proc.poll() is None:
            os.killpg(self.proc.pid, signal.SIGTERM)
            try:
                self.proc.wait(30)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid, signal.SIGKILL); self.proc.wait()
        self.fh.close()
        return m


def convo(k, edit=False):
    msgs = [{'role': 'system', 'content': SYSTEM}]
    for i, (q, a) in enumerate(TURNS[:k]):
        if edit and i == EDIT_AT:
            q, a = 'How many beds does the ward have?', 'The ward has 24 beds.'
        msgs += [{'role': 'user', 'content': q}, {'role': 'assistant', 'content': a}]
    msgs.append({'role': 'user', 'content': TURNS[k][0] if k < len(TURNS) else 'Summarise Lena\'s Saturday shift.'})
    return msgs


def strip(r):
    return {k: r[k] for k in ('prompt_n', 'cache_n', 'prompt_ms', 'wall_ms', 'text')}


def run_body(binary, role, model, out, repeats):
    d = out / role; d.mkdir(parents=True, exist_ok=True)
    logs = {}
    res = {'role': role, 'model': str(model), 'experiments': {}, 'servers': {}}

    def srv(name, flags, slot_dir=None):
        lp = d / f'{name}.log'; lp.unlink(missing_ok=True); logs[name] = lp
        s = Server(binary, model, flags, lp, slot_dir); res['servers'][name] = {'flags': flags, 'load_s': s.load_s}; return s

    def done(name, s):
        res['servers'][name]['mem'] = s.stop()
        res['servers'][name]['log_facts'] = P.parse_server_log(logs[name].read_text(errors='replace'))

    # ---- cold references (no prompt cache, no checkpoints, cache_prompt=false)
    s = srv('cold', COLD)
    prompts = {'final': s.render(convo(len(TURNS))), 'edited': s.render(convo(len(TURNS), edit=True))}
    A = s.render(convo(3))
    # A2 continues A with the body's *actual* answer (V13 commits what the body said), then the next question.
    a_said = s.complete(A, cache=False)['text']
    A2 = s.render(convo(3) + [{'role': 'assistant', 'content': a_said}, {'role': 'user', 'content': TURNS[4][0]}])
    B = s.render([{'role': 'system', 'content': 'You are a cook. Use only the card.\n\n' + OTHER}, {'role': 'user', 'content': 'How many does it serve?'}])
    head = s.render(convo(1))[: len(s.render(convo(1))) // 2]
    tail_txt = ' Question: what time do medication rounds start?'
    shift_full = head + ' ' + OTHER[:600] + tail_txt; shift_cut = head + tail_txt
    prompts.update({'A': A, 'A2': A2, 'B': B, 'shift_full': shift_full, 'shift_cut': shift_cut})
    ntok = {k: s.ntok(v) for k, v in prompts.items()}
    cold = {k: s.complete(v, cache=False) for k, v in prompts.items()}
    repeat = {k: s.complete(v, cache=False) for k, v in prompts.items()}
    common_edit = os.path.commonprefix([prompts['final'], prompts['edited']])
    res['tokens'] = ntok | {'edit_common_prefix': s.ntok(common_edit), 'shift_head': s.ntok(head)}
    done('cold', s)
    # Noise floor of re-prefill itself: same prompts, other physical batch split (-b/-ub 64 instead of 128).
    # Cached paths evaluate the same tokens in other splits, so their float drift is judged against this floor.
    s = srv('cold_b64', COLD + ['-b', '64', '-ub', '64'])
    b64 = {k: s.complete(v, cache=False) for k, v in prompts.items()}
    done('cold_b64', s)
    floor = {k: P.classify_exactness(cold[k], b64[k]) for k in prompts}
    rerun = {k: P.classify_exactness(cold[k], repeat[k]) for k in prompts}
    same = [f['max_abs_dlogp'] or 0 for f in floor.values() if f['same_tokens']]
    tol = max(5e-2, 2 * max(same, default=0))
    res['noise_floor'] = {'batch_split': floor, 'same_server_rerun': rerun, 'tol_close': round(tol, 6),
                          'split_unstable_prompts': [k for k, f in floor.items() if not f['same_tokens']],
                          'rule': 'tol_close = max(0.05, 2 x largest batch-split drift among prompts whose tokens stay equal); '
                                  'same tokens required. A prompt whose greedy tokens change with the batch split alone is '
                                  'listed as split-unstable: re-prefill itself is not reproducible there.'}
    unstable = set(res['noise_floor']['split_unstable_prompts'])

    def cmp(ref_key, r, ref=None):
        # a prompt whose cold greedy tokens already flip with the batch split cannot decide a cached path's exactness
        e = P.classify_exactness(ref or cold[ref_key], r, tol_close=tol)
        return e | {'class': 'BASELINE_SPLIT_UNSTABLE', 'raw_class': e['class']} if ref_key in unstable else e

    # ---- prefix: production-like defaults, growing conversation on one slot
    rows = []
    for rep in range(repeats):
        s = srv(f'prefix{rep}', [])
        for k in range(len(TURNS) + 1):
            r = s.complete(s.render(convo(k))); rows.append({'rep': rep, 'turn': k} | strip(r))
        last = r
        done(f'prefix{rep}', s)
    after0 = [x for x in rows if x['turn'] > 0]
    res['experiments']['prefix'] = {
        'rows': rows, 'usable': sum(x['cache_n'] or 0 for x in after0) > 0, 'exactness': cmp('final', last),
        'cost': {'reprefill_tokens_after_turn0': sum(x['prompt_n'] or 0 for x in after0) / repeats,
                 'reused_tokens_after_turn0': sum(x['cache_n'] or 0 for x in after0) / repeats,
                 'cold_final_prompt_ms': cold['final']['prompt_ms'], 'warm_final_prompt_ms': last['prompt_ms']},
        'summary': 'growing conversation on one slot with default b10964 flags'}

    # ---- edit_replay: change turn EDIT_AT after the full conversation; default vs dense checkpoints (§8.6.2)
    er = {}
    dense = ['--cache-ram', '0', '--ctx-checkpoints', '32', '--checkpoint-min-step', '64']
    for name, flags, turnwise in (('turnwise_default', ['--cache-ram', '0'], True), ('oneshot_default', ['--cache-ram', '0'], False),
                                  ('oneshot_dense_ckpt', dense, False)):
        reps = []
        for rep in range(repeats):
            s = srv(f'edit_{name}{rep}', flags)
            # turnwise: the chat grew turn by turn (one checkpoint per request); oneshot: the whole history arrived at once
            for k in (range(len(TURNS) + 1) if turnwise else [len(TURNS)]):
                s.complete(s.render(convo(k)), n=4)
            r = s.complete(prompts['edited']); reps.append(r)
            done(f'edit_{name}{rep}', s)
        f = res['servers'][f'edit_{name}0']['log_facts']
        er[name] = {'rows': [strip(x) for x in reps], 'exactness': cmp('edited', reps[-1]),
                    'checkpoints_created': len(f['checkpoints_created']), 'checkpoints_restored': f['checkpoints_restored'],
                    'checkpoint_mib': f['checkpoint_mib'],
                    'mean_prompt_ms': round(sum(x['prompt_ms'] for x in reps) / len(reps), 1),
                    'mean_prompt_n': sum(x['prompt_n'] for x in reps) / len(reps)}
    best = max(er.values(), key=lambda v: v['rows'][-1]['cache_n'] or 0)
    res['experiments']['edit_replay'] = {
        'variants': er, 'usable': (best['rows'][-1]['cache_n'] or 0) > 0, 'exactness': best['exactness'],
        'cost': {'cold_prompt_ms': cold['edited']['prompt_ms'], 'cold_prompt_n': cold['edited']['prompt_n'],
                 'upper_bound_reusable_tokens': res['tokens']['edit_common_prefix']},
        'summary': 'edit turn %d after the full conversation; turnwise vs one-shot history; dense = --ctx-checkpoints 32 --checkpoint-min-step 64' % EDIT_AT}

    # ---- switch: A -> B -> A' on one slot, host prompt cache on (default 8192 MiB) vs off
    sw = {}
    for name, flags in (('cache_ram_default', []), ('cache_ram_0', ['--cache-ram', '0'])):
        s = srv(f'switch_{name}', flags)
        s.complete(A); m1 = s.mem(); s.complete(B); r = s.complete(A2); m2 = s.mem()
        sw[name] = {'A2': strip(r), 'exactness': cmp('A2', r), 'rss_after_A_mib': m1['rss_mib'], 'rss_after_A2_mib': m2['rss_mib']}
        done(f'switch_{name}', s)
    on = sw['cache_ram_default']
    res['experiments']['switch'] = {
        'variants': sw, 'usable': (on['A2']['cache_n'] or 0) > (sw['cache_ram_0']['A2']['cache_n'] or 0), 'exactness': on['exactness'],
        'cost': {'cold_prompt_ms': cold['A2']['prompt_ms'], 'on_prompt_ms': on['A2']['prompt_ms'], 'off_prompt_ms': sw['cache_ram_0']['A2']['prompt_ms']},
        'summary': 'conversation A, unrelated B, back to A on a single slot'}

    # ---- persist: save slot after A, restart the server, restore, continue with A' (resume after restart)
    slots = d / 'slots'; shutil.rmtree(slots, ignore_errors=True); slots.mkdir()
    s = srv('persist_a', ['--cache-ram', '0'], slots); s.complete(A)
    sv = s.post('/slots/0?action=save', {'filename': 'a.bin'}); done('persist_a', s)
    s = srv('persist_b', ['--cache-ram', '0'], slots)
    t0 = time.monotonic(); rs = s.post('/slots/0?action=restore', {'filename': 'a.bin'}); restore_wall = (time.monotonic() - t0) * 1000
    r = s.complete(A2); done('persist_b', s)
    fbytes = (slots / 'a.bin').stat().st_size
    res['experiments']['persist'] = {
        'save': sv, 'restore': rs, 'restore_wall_ms': round(restore_wall, 1), 'file_bytes': fbytes, 'A2': strip(r),
        'usable': (r['cache_n'] or 0) > 0, 'exactness': cmp('A2', r),
        'cost': {'cold_prompt_ms': cold['A2']['prompt_ms'], 'restore_ms': (rs.get('timings') or {}).get('restore_ms'),
                 'resumed_prompt_ms': r['prompt_ms'], 'file_mib': round(fbytes / 2**20, 2)},
        'summary': 'slot saved to disk, server restarted, slot restored, conversation continued'}
    shutil.rmtree(slots, ignore_errors=True)

    # ---- shift: --cache-reuse 64 after removing a middle chunk
    s = srv('shift', ['--cache-ram', '0', '--cache-reuse', '64']); s.complete(shift_full); r = s.complete(shift_cut); done('shift', s)
    warn = [l for l in logs['shift'].read_text(errors='replace').splitlines() if 'cache_reuse' in l or 'cache reuse' in l][:5]
    res['experiments']['shift'] = {
        'cut': strip(r), 'log_lines': warn, 'head_tokens': res['tokens']['shift_head'],
        'usable': (r['cache_n'] or 0) > res['tokens']['shift_head'] + 16, 'exactness': cmp('shift_cut', r),
        'cost': {'cold_prompt_ms': cold['shift_cut']['prompt_ms'], 'prompt_ms': r['prompt_ms']},
        'summary': 'KV shifting reuse of the tail after a removed middle chunk'}

    # ---- kvquant: q8_0 K/V vs f16 K/V, both with flash attention, cold prompts
    kq = {}
    for name, flags in (('f16', COLD + ['-fa', 'on']), ('q8_0', COLD + ['-fa', 'on', '-ctk', 'q8_0', '-ctv', 'q8_0'])):
        s = srv(f'kv_{name}', flags)
        kq[name] = {k: s.complete(prompts[k], cache=False) for k in ('final', 'edited', 'B')}
        done(f'kv_{name}', s)
    ex = {k: cmp(k, kq['q8_0'][k], ref=kq['f16'][k]) for k in kq['f16']}
    order = ['EXACT', 'NUMERIC_CLOSE', 'BASELINE_SPLIT_UNSTABLE', 'DIVERGENT', 'UNMEASURED']
    worst = max(ex.values(), key=lambda e: order.index(e['class']))
    f16f, q8f = res['servers']['kv_f16']['log_facts'], res['servers']['kv_q8_0']['log_facts']
    res['experiments']['kvquant'] = {
        'per_prompt': ex, 'usable': bool(q8f['kv_mib'] and f16f['kv_mib'] and q8f['kv_mib'] < f16f['kv_mib']), 'exactness': worst,
        'cost': {'kv_mib_f16': f16f['kv_mib'], 'kv_mib_q8_0': q8f['kv_mib'], 'kv_types_q8': q8f['kv_types'],
                 'hwm_mib_f16': (res['servers']['kv_f16'].get('mem') or {}).get('hwm_mib'), 'hwm_mib_q8_0': (res['servers']['kv_q8_0'].get('mem') or {}).get('hwm_mib')},
        'summary': 'q8_0 K/V cache vs f16 at 2048 cells, 3 cold prompts x %d greedy tokens' % N_PRED}

    facts = res['servers']['prefix0']['log_facts']
    res['manifest'] = P.build_manifest(role, Path(model).name, facts, res['experiments'])
    res['policy'] = {sit: {'exact_required': P.select_mechanism(res['manifest'], sit, exact_required=True),
                           'approx_ok': P.select_mechanism(res['manifest'], sit, exact_required=False)} for sit in P.SITUATIONS}
    res['runner_flags_256mib'] = P.runner_flags(res['manifest'], 256)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bin', required=True); ap.add_argument('--model', action='append', required=True, help='ROLE=path.gguf')
    ap.add_argument('--out', required=True); ap.add_argument('--repeats', type=int, default=2)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    binary = Path(a.bin).resolve()
    report = {'created': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'platform': platform.platform(), 'cpu_count': os.cpu_count(),
              'evidence_level': 'LINUX_NATIVE_CLOUD (not Redmi)', 'runner_binary_sha256': sha256(binary),
              'script_sha256': {n: sha256(Path(__file__).parent / n) for n in ('native_cache_bench.py', 'native_cache_primitives.py')},
              'base_flags': BASE, 'n_predict': N_PRED, 'repeats': a.repeats, 'bodies': {}}
    for spec in a.model:
        role, path = spec.split('=', 1)
        report['bodies'][role] = {'model_sha256': sha256(path)}
        try:
            report['bodies'][role] |= run_body(binary, role, Path(path).resolve(), out, a.repeats)
        except Exception as e:  # a failed body is kept as an explicit error, never dropped
            report['bodies'][role] |= {'status': 'ERROR', 'error': f'{type(e).__name__}: {e}'}
        (out / 'report.json').write_text(json.dumps(report, indent=1))
        print(role, 'done', flush=True)
    (out / 'report.json').write_text(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
