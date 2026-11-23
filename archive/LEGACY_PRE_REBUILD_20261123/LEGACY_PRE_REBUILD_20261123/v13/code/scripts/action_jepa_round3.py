#!/usr/bin/env python3
"""Action-JEPA round 3: fresh never-seen test topics plus one consistent native recapture.

Rounds 1/2 could only test on six historically exposed topics. This adapter
1) lets C3 (LFM2.5-350M) write sentences for preregistered fresh topics and the
   four original text actions (prompts of bench-results/jepa-action-20261010/gen_actions.py),
2) recaptures ALL rows (old 1875 corpus + fresh rows) with one B2 runtime
   (Qwen3.5-0.8B, llama-server --embedding --pooling mean, batch 16, 2 threads),
   because the release build differs from the earlier local build (cos ~.9999),
3) exports train/calibration/retention from the unchanged plan-v2 episodes and
   test only from fresh topics, dropping every fresh episode whose normalized
   text also occurs in a non-test row.
Each raw response is saved before the checkpoint. Nothing here changes runtime
code, native parameters or authority.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
import uuid

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from action_jepa_objective import SCHEMA, load_dataset
from export_action_jepa_dataset import ACTIONS, corpus, json_sha, sha, source_identity, text_sha

PLAN_SCHEMA = 'v13-action-jepa-round3-plan-v1'
# Exactly the action prompts of bench-results/jepa-action-20261010/gen_actions.py.
ACTION_PROMPTS = {
    'translate_de': 'Translate this sentence into German. Reply with the German sentence only.',
    'question': 'Rewrite this sentence as a yes/no question. Reply with the question only.',
    'negate': 'Rewrite this sentence so that it means the opposite (negate it). Reply with the new sentence only.',
    'summarize': 'Shorten this sentence to at most four words. Reply with the short version only.'}
SENTENCE_PROMPT = ('Write 24 different short English sentences about {topic}. '
                   'Write one sentence per line. Do not number them.')
MIN_SENTENCES = 16


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    tmp = Path(str(path) + '.writing')
    tmp.write_text(json.dumps(value, indent=1, ensure_ascii=False, allow_nan=False) + '\n')
    os.replace(tmp, path)


def post(port, route, body, timeout=600):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{route}', json.dumps(body, ensure_ascii=False).encode(),
                                 {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


class Server:
    """Owned llama-server child; unique alias proves responses come from it."""

    def __init__(self, binary, model, port, log, embedding=False):
        self.alias = 'v13-round3-' + uuid.uuid4().hex
        self.port = port
        env = {k: v for k, v in os.environ.items() if not k.startswith('V13_') and k not in ('LD_PRELOAD', 'LD_LIBRARY_PATH')}
        env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='2')
        cmd = [str(Path(binary).resolve()), '-m', str(Path(model).resolve()), '--host', '127.0.0.1', '--port', str(port),
               '--alias', self.alias, '-c', '2048', '-t', '2', '-tb', '2', '--no-webui', '--log-disable']
        if embedding:
            cmd[3:3] = ['--embedding', '--pooling', 'mean']
        self.command = cmd
        self.log = open(log, 'a')
        self.proc = subprocess.Popen(cmd, stdout=self.log, stderr=subprocess.STDOUT, env=env)
        for _ in range(1200):
            if self.proc.poll() is not None:
                raise RuntimeError('native server exited during startup: %s' % self.proc.returncode)
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=1):
                    return
            except OSError:
                time.sleep(.5)
        raise RuntimeError('native server did not become healthy')

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.log.close()
        return self.proc.returncode


def chat(server, prompt, max_tokens):
    out = post(server.port, '/v1/chat/completions', {'model': server.alias, 'temperature': 0, 'max_tokens': max_tokens,
                                                     'messages': [{'role': 'user', 'content': prompt}]})
    if out.get('model') != server.alias:
        raise ValueError('Response is not from the owned model alias')
    return out


def parse_sentences(text):
    """Keep plain one-line sentences of 3-25 words; numbering/bullets are stripped."""
    kept, seen = [], set()
    for line in text.split('\n'):
        line = re.sub(r'^\s*(?:[-*•]|\d+[.)])\s*', '', line).strip().strip('"')
        words = line.split()
        if not 3 <= len(words) <= 25 or line[-1:] not in '.!?':
            continue
        identity = source_identity(line.rstrip('.!?'))
        if identity not in seen:
            seen.add(identity)
            kept.append(line)
    return kept[:24]


def generate(args):
    prereg = json.loads(Path(args.preregistration).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    raw_log = out / 'generation-raw.jsonl'
    server = Server(args.server, args.model, args.port, out / 'c3-server.log')
    sentences, chosen = {}, []
    try:
        with raw_log.open('a') as raw:
            for topic in prereg['fresh_topics'] + prereg['reserve_topics']:
                if len(chosen) == len(prereg['fresh_topics']):
                    break
                response = chat(server, SENTENCE_PROMPT.format(topic=topic), 1024)
                raw.write(json.dumps({'kind': 'sentences', 'topic': topic, 'response': response}, ensure_ascii=False) + '\n')
                kept = parse_sentences(response['choices'][0]['message']['content'])
                if len(kept) >= MIN_SENTENCES:
                    sentences[topic] = kept
                    chosen.append(topic)
            actions = {}
            for topic in chosen:
                for sentence in sentences[topic]:
                    result = {}
                    for action, instruction in ACTION_PROMPTS.items():
                        response = chat(server, instruction + '\n\n' + sentence, 48)
                        raw.write(json.dumps({'kind': 'action', 'sentence': sentence, 'action': action, 'response': response},
                                             ensure_ascii=False) + '\n')
                        result[action] = response['choices'][0]['message']['content'].strip().split('\n')[0].strip('"')
                    actions[sentence] = result
    finally:
        code = server.close()
    write_json(out / 'fresh-sentences.json', sentences)
    write_json(out / 'fresh-actions.json', actions)
    report = {'schema': 'v13-action-jepa-round3-generation-v1', 'utc': now(), 'topics': chosen,
              'sentences': {t: len(v) for t, v in sentences.items()}, 'c3_model_sha256': sha(args.model),
              'server_sha256': sha(args.server), 'server_exit': code, 'raw_log_sha256': sha(raw_log),
              'sentences_sha256': sha(out / 'fresh-sentences.json'), 'actions_sha256': sha(out / 'fresh-actions.json')}
    write_json(out / 'generation-report.json', report)
    return report


def fresh_corpus(sentences_path, actions_path):
    topics = json.loads(Path(sentences_path).read_text())
    outcomes = json.loads(Path(actions_path).read_text())
    rows = []
    for topic in sorted(topics):
        for position, sentence in enumerate(topics[topic]):
            if any(not str(outcomes[sentence].get(a, '')).strip() for a in ACTIONS):
                raise ValueError('Four nonempty action outcomes required')
            rows.append({'topic': topic, 'position': position, 'input': sentence,
                         'outcomes': {a: outcomes[sentence][a] for a in ACTIONS}})
    texts = [r['input'] for r in rows] + [r['outcomes'][a] for a in ACTIONS for r in rows]
    return rows, texts


def all_texts(args):
    _, _, old = corpus(args.old_sentences, args.old_actions)
    _, fresh = fresh_corpus(args.fresh_sentences, args.fresh_actions)
    return old, fresh


def capture(args):
    old, fresh = all_texts(args)
    texts = old + fresh
    out = Path(args.out)
    (out / 'batches').mkdir(parents=True, exist_ok=True)
    registration = {'schema': 'v13-action-jepa-round3-capture-registration-v1', 'texts_sha256': json_sha(texts),
                    'old_rows': len(old), 'fresh_rows': len(fresh), 'model_sha256': sha(args.model),
                    'server_sha256': sha(args.server),
                    'libraries': {p.name: sha(p) for p in sorted(Path(args.server).resolve().parent.glob('*.so*')) if p.is_file()},
                    'batch_size': 16, 'threads': 2, 'context': 2048, 'pooling': 'mean'}
    reg_path = out / 'registration.json'
    if reg_path.exists():
        if json.loads(reg_path.read_text()) != registration:
            raise ValueError('Resume registration differs')
    else:
        write_json(reg_path, registration)
    reg_sha = sha(reg_path)
    chunks, records = [], []
    server = None
    try:
        for start in range(0, len(texts), 16):
            end = min(start + 16, len(texts))
            name = f'batches/batch-{start:05d}-{end:05d}.json'
            path = out / name
            if not path.exists():
                if server is None:
                    server = Server(args.server, args.model, args.port, out / 'b2-server.log', embedding=True)
                payload = post(server.port, '/v1/embeddings', {'input': texts[start:end], 'model': server.alias})
                write_json(path, {'registry_sha256': reg_sha, 'start': start, 'end': end, 'inputs': texts[start:end],
                                  'model_alias': server.alias, 'response': payload, 'utc': now()})
            batch = json.loads(path.read_text())
            response = batch['response']
            if (batch['registry_sha256'] != reg_sha or batch['inputs'] != texts[start:end]
                    or response.get('model') != batch['model_alias']
                    or sorted(r['index'] for r in response['data']) != list(range(end - start))):
                raise ValueError('Raw batch lineage mismatch')
            x = np.asarray([r['embedding'] for r in sorted(response['data'], key=lambda r: r['index'])], dtype=np.float64)
            if x.shape != (end - start, 1024) or not np.isfinite(x).all():
                raise ValueError('Finite 1024-D native embeddings required')
            chunks.append(x)
            records.append({'path': name, 'sha256': sha(path)})
            if len(records) % 20 == 0:
                print(json.dumps({'rows': end, 'of': len(texts), 'utc': now()}), flush=True)
    finally:
        code = server.close() if server else None
    x = np.concatenate(chunks)
    np.savez(out / 'taps.npz', x=x, texts=np.asarray(texts),
             checkpoint=np.asarray(json.dumps({'registry_sha256': reg_sha, 'batch_records': records}, sort_keys=True)))
    report = {'status': 'CAPTURED', 'rows': len(x), 'batches': len(records), 'taps_sha256': sha(out / 'taps.npz'),
              'array_sha256': hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest(),
              'registration_sha256': reg_sha, 'last_server_exit': code, 'utc': now()}
    write_json(out / 'capture-report.json', report)
    return report


def export(args):
    old, fresh = all_texts(args)
    _, old_rows, _ = corpus(args.old_sentences, args.old_actions)
    fresh_rows, _ = fresh_corpus(args.fresh_sentences, args.fresh_actions)
    plan = json.loads(Path(args.old_plan).read_text())
    taps = Path(args.taps)
    with np.load(taps, allow_pickle=False) as z:
        if z['texts'].tolist() != old + fresh or z['x'].shape != (len(old) + len(fresh), 1024):
            raise ValueError('Capture texts/shape differ from round-3 corpus')
    kept_old = [e for e in plan['kept_episodes'] if e['partition'] != 'test']
    used = set()
    for e in kept_old:
        row = old_rows[e['original_index']]
        used.update(source_identity(t) for t in [row['input'], *row['outcomes'].values()])
    kept_fresh, dropped, seen = [], [], set()
    for i, row in enumerate(fresh_rows):
        ids = [source_identity(t) for t in [row['input'], *row['outcomes'].values()]]
        reason = 'shares_text_with_training_side' if any(s in used for s in ids) else None
        if ids[0] in seen:
            reason = reason or 'duplicate_normalized_input_episode'
        seen.add(ids[0])
        if reason:
            dropped.append({'fresh_index': i, 'input_sha256': text_sha(row['input']), 'reason': reason})
        else:
            kept_fresh.append(i)
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Export destination must be empty')
    (out / 'sources').mkdir(parents=True)
    (out / 'native-taps.npz').write_bytes(taps.read_bytes())
    encoder = {'schema': 'v13-action-jepa-round3-encoder-v1', 'tap_kind': 'llama.cpp-mean-last-layer-embedding',
               'capture_registration': json.loads(Path(args.registration).read_text()),
               'capture_registration_sha256': sha(args.registration), 'taps_sha256': sha(taps)}
    write_json(out / 'encoder-binding.json', encoder)
    bindings = {'encoder': {'path': 'encoder-binding.json', 'sha256': sha(out / 'encoder-binding.json')},
                'native_taps': {'path': 'native-taps.npz', 'sha256': sha(out / 'native-taps.npz')}}

    def bind(text):
        key = 'text-' + text_sha(text)
        if key not in bindings:
            path = out / 'sources' / (key + '.txt')
            path.write_bytes(text.encode())
            bindings[key] = {'path': path.relative_to(out).as_posix(), 'sha256': sha(path)}
        return key

    rows = []
    for e in kept_old:
        i = e['original_index']
        r = old_rows[i]
        for j, action in enumerate(ACTIONS):
            rows.append({'row_id': e['episode_id'] + ':' + action, 'episode_id': e['episode_id'], 'topic': r['topic'],
                         'partition': e['partition'], 'action': action,
                         'source_ids': [bind(r['input']), bind(r['outcomes'][action])],
                         'context_artifact_index': i, 'future_artifact_index': len(old_rows) * (j + 1) + i})
    n = len(fresh_rows)
    for i in kept_fresh:
        r = fresh_rows[i]
        episode = 'fresh-' + text_sha(source_identity(r['input']))
        for j, action in enumerate(ACTIONS):
            rows.append({'row_id': episode + ':' + action, 'episode_id': episode, 'topic': r['topic'],
                         'partition': 'test', 'action': action,
                         'source_ids': [bind(r['input']), bind(r['outcomes'][action])],
                         'context_artifact_index': len(old) + i, 'future_artifact_index': len(old) + n * (j + 1) + i})
    round3_plan = {'schema': PLAN_SCHEMA, 'old_plan_sha256': sha(args.old_plan),
                   'fresh_sentences_sha256': sha(args.fresh_sentences), 'fresh_actions_sha256': sha(args.fresh_actions),
                   'test_topics': sorted({r['topic'] for r in fresh_rows}), 'excluded_fresh_episodes': dropped,
                   'episodes': {p: len({r['episode_id'] for r in rows if r['partition'] == p})
                                for p in ('train', 'calibration', 'retention', 'test')},
                   'fresh_held_out_data': True, 'historical_test_topics_used': False}
    dataset = {'schema': SCHEMA, 'provenance_kind': 'native_dense_tap', 'bindings': bindings,
               'state_artifact': {'binding_id': 'native_taps', 'array_key': 'x', 'transform': 'rms_normalize',
                                  'materialize_states_from_indices': True},
               'export_plan': round3_plan, 'rows': rows}
    write_json(out / 'dataset.json', dataset)
    load_dataset(out / 'dataset.json')
    receipt = {'status': 'EXPORTED', 'dataset_sha256': sha(out / 'dataset.json'), 'pairs': len(rows),
               'episodes': round3_plan['episodes'], 'excluded_fresh': len(dropped), 'taps_sha256': sha(taps),
               'receiver_authority': 0, 'semantic_quality_proven': False}
    write_json(out / 'export-receipt.json', receipt)
    return receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    g = sub.add_parser('generate')
    for name in ('--server', '--model', '--preregistration', '--out'):
        g.add_argument(name, required=True)
    g.add_argument('--port', type=int, default=18231)
    c = sub.add_parser('capture')
    e = sub.add_parser('export')
    for p in (c, e):
        for name in ('--old-sentences', '--old-actions', '--fresh-sentences', '--fresh-actions', '--out'):
            p.add_argument(name, required=True)
    for name in ('--server', '--model'):
        c.add_argument(name, required=True)
    c.add_argument('--port', type=int, default=18232)
    for name in ('--old-plan', '--taps', '--registration'):
        e.add_argument(name, required=True)
    args = ap.parse_args()
    print(json.dumps({'generate': generate, 'capture': capture, 'export': export}[args.command](args)))


if __name__ == '__main__':
    main()
