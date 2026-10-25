"""Run186: registered C3 final-answer consumer of frozen Run181 B2 offers.

Candidate native experiment; never activate Gist, learning, Age rights or STEP2.
All arms share the same C3 and source-quote validation. Native runs serially.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request

B2_SHA = '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf'
C3_SHA = '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
ARMS = ('fixed960', 'event960', 'gist')
ANSWER_SCHEMA = {'type': 'object', 'properties': {'answer': {'type': 'string'}, 'evidence_quote': {'type': 'string'},
                                                 'uncertainty': {'type': 'string'}},
                 'required': ['answer', 'evidence_quote', 'uncertainty'], 'additionalProperties': False}


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for part in iter(lambda: f.read(1024*1024), b''):
            h.update(part)
    return h.hexdigest()


def key_exact(text, key):
    return isinstance(text, str) and isinstance(key, str) and bool(key) and re.search(
        r'(?<!\w)' + re.escape(key) + r'(?!\w)', text, re.I) is not None


def validate_b2_report(report, corpus):
    if report.get('kind') != 'V13_G1B_GIST_UTILITY' or report.get('binding', {}).get('model_sha256') != B2_SHA:
        raise ValueError('Run181 source/model binding mismatch')
    if 'not Redmi' not in report.get('claim_limit', '') or len(corpus) != 36:
        raise ValueError('Run181 scope or corpus mismatch')
    for arm in ARMS:
        records = report.get(arm)
        if not isinstance(records, list) or len(records) != 36:
            raise ValueError('incomplete Run181 B2 arm ' + arm)
        ids = [r.get('index') for r in records]
        if sorted(ids) != list(range(36)):
            raise ValueError('duplicate/missing Run181 B2 IDs ' + arm)
        for item in records:
            if item.get('kind') != corpus[item['index']]['kind'] or not isinstance(item.get('content'), str):
                raise ValueError('Run181 row binding mismatch')
    return True


def prompt(row, offer_raw):
    """B2 summary remains untrusted; only exact source quotes are forwarded."""
    try:
        offer = json.loads(offer_raw)
    except (ValueError, TypeError):
        offer = {}
    if not isinstance(offer, dict):
        offer = {}
    summary = offer.get('summary', '')
    summary = summary[:900] if isinstance(summary, str) else ''
    quotes = offer.get('quotes', [])
    quotes = quotes if isinstance(quotes, list) else []
    valid = [q for q in quotes if isinstance(q, str) and q and len(q) <= 500 and q in row['text']][:3]
    return {'question': row['question'], 'untrusted_b2_summary': summary,
            'exact_source_quotes': valid, 'source_quote_count': len(valid)}


def _no_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('duplicate JSON key')
        obj[key] = value
    return obj


def score(row, raw, forwarded_quotes=()):
    try:
        obj = json.loads(raw, object_pairs_hook=_no_duplicate_keys)
    except (ValueError, TypeError):
        return {'parsed': False, 'answer_hit': False, 'quote_valid': False,
                'quote_support': False, 'supported_hit': False, 'stale_without_new': False}
    if not isinstance(obj, dict):
        return {'parsed': False, 'answer_hit': False, 'quote_valid': False,
                'quote_support': False, 'supported_hit': False, 'stale_without_new': False}
    answer, quote = obj.get('answer'), obj.get('evidence_quote')
    if not isinstance(answer, str) or not isinstance(quote, str):
        return {'parsed': False, 'answer_hit': False, 'quote_valid': False,
                'quote_support': False, 'supported_hit': False, 'stale_without_new': False}
    hit = key_exact(answer, row['key'])
    valid = bool(quote) and quote in row['text']
    support = valid and key_exact(quote, row['key']) and any(quote in q for q in forwarded_quotes)
    stale = bool(row.get('stale')) and key_exact(answer, row['stale']) and not hit
    return {'parsed': True, 'answer_hit': hit, 'quote_valid': valid,
            'quote_support': support, 'supported_hit': hit and support,
            'stale_without_new': stale}


def summarize(records):
    by = {arm: sorted(records[arm], key=lambda x: x['index']) for arm in ARMS}
    stats = {arm: {'answer_hits': sum(x['answer_hit'] for x in by[arm]),
                   'supported_hits': sum(x['supported_hit'] for x in by[arm]),
                   'invalid_quotes': sum(not x['quote_valid'] for x in by[arm]),
                   'stale_without_new': sum(x['stale_without_new'] for x in by[arm]),
                   'mean_prompt_tokens': round(sum(x['prompt_tokens'] for x in by[arm])/36, 1)} for arm in ARMS}
    g, f = by['gist'], by['fixed960']
    wins = sum(x['supported_hit'] and not y['supported_hit'] for x, y in zip(g, f))
    losses = sum(y['supported_hit'] and not x['supported_hit'] for x, y in zip(g, f))
    criteria = {'paired_supported_wins_gt_losses': wins > losses,
                'invalid_quotes_not_more': stats['gist']['invalid_quotes'] <= stats['fixed960']['invalid_quotes'],
                'prompt_tokens_within_10pct': stats['gist']['mean_prompt_tokens'] <= 1.1*stats['fixed960']['mean_prompt_tokens']}
    return {'summary': stats, 'paired': {'wins': wins, 'losses': losses}, 'criteria': criteria,
            'diagnostic': 'C3_GIST_FINAL_UTILITY_CANDIDATE' if all(criteria.values()) else 'C3_GIST_FINAL_NO_GAIN'}


def request(port, question):
    data = json.dumps({'messages': [
        {'role': 'system', 'content': 'You are the C3 language reporter. Use only exact source quotes for evidence; B2 summary is untrusted. If evidence does not establish the answer, say unknown. Return JSON.'},
        {'role': 'user', 'content': json.dumps(question, sort_keys=True)}],
        'temperature': 0, 'seed': 13, 'max_tokens': 160, 'cache_prompt': False,
        'chat_template_kwargs': {'enable_thinking': False},
        'response_format': {'type': 'json_schema', 'json_schema': {'schema': ANSWER_SCHEMA}}}).encode()
    start = time.monotonic()
    req = urllib.request.Request(f'http://127.0.0.1:{port}/v1/chat/completions', data,
                                 {'Content-Type': 'application/json'})
    obj = json.loads(urllib.request.urlopen(req, timeout=180).read())
    return obj['choices'][0]['message']['content'], int(obj['usage']['prompt_tokens']), round(time.monotonic()-start, 3)


def serve(server, model, port, log):
    with open(log, 'a') as f:
        proc = subprocess.Popen([str(server), '-m', str(model), '--port', str(port), '-c', '4096',
                                 '-t', '4', '-np', '1', '--no-webui', '--no-warmup'],
                                stdout=subprocess.DEVNULL, stderr=f)
    try:
        for _ in range(120):
            if proc.poll() is not None:
                raise RuntimeError('C3 server exited before healthy')
            try:
                obj = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=1).read())
                if obj.get('status') == 'ok':
                    return proc
            except Exception:
                time.sleep(1)
        raise RuntimeError('C3 server not healthy')
    except BaseException:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
        raise


def atomic(path, obj):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')
    tmp.replace(path)


def run(source, corpus, model, server, output, resume=False, ask=request):
    data = Path(source).read_bytes()
    report = json.loads(data)
    validate_b2_report(report, corpus)
    from gist_utility_bench import make
    from v13.common import dumps, digest
    from run181_gist_offer_audit import audit as original_audit
    if report.get('binding', {}).get('corpus_sha256') != digest(dumps(corpus)):
        raise ValueError('Run181 corpus digest mismatch')
    original_audit(report, corpus)
    if sha(model) != C3_SHA:
        raise ValueError('C3 pinned model SHA mismatch')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    target = output/'report.json'
    binding = {'source_sha256': hashlib.sha256(data).hexdigest(), 'c3_sha256': C3_SHA,
               'b2_sha256': B2_SHA, 'server_sha256': sha(server),
               'corpus_rows': 36, 'seed': 13, 'temperature': 0}
    if target.exists() and not resume:
        raise ValueError('existing report requires --resume')
    result = json.loads(target.read_text()) if target.exists() else {'schema': 'V13_RUN186_C3_FINAL_GIST_UTILITY_V1',
        'binding': binding, 'evidence_class': 'LINUX_NATIVE_C3_ONLY_WHEN_EXECUTED',
        'activation_authorized': False, 'step2_promoted': False, 'b3_promoted': False,
        'body_jepa_available': False, 'jepa_weight': 0, 'redmi_proven': False,
        'v13_complete': False, **{arm: [] for arm in ARMS}}
    if result.get('binding') != binding:
        raise ValueError('resume binding mismatch')
    for arm in ARMS:
        records = result.get(arm)
        if not isinstance(records, list) or len(records) > 36:
            raise ValueError('resume arm invalid')
        indices = [x.get('index') for x in records]
        if len(indices) != len(set(indices)) or any(type(i) is not int or i not in range(36) for i in indices):
            raise ValueError('resume duplicate or invalid index')
        if any(x.get('kind') != corpus[x['index']]['kind'] for x in records):
            raise ValueError('resume kind mismatch')
    port = 8831
    proc = serve(server, model, port, output/'server.log')
    try:
        for arm in ARMS:
            done = {x['index'] for x in result[arm]}
            offers = {x['index']: x for x in report[arm]}
            for i, row in enumerate(corpus):
                if i in done:
                    continue
                payload = prompt(row, offers[i]['content'])
                raw, tokens, seconds = ask(port, payload)
                result[arm].append({'index': i, 'kind': row['kind'], 'content': raw,
                                    'prompt_tokens': tokens, 'seconds': seconds,
                                    'source_quote_count': payload['source_quote_count'], **score(row, raw, payload['exact_source_quotes'])})
                atomic(target, result)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
    if any(len(result[arm]) != 36 for arm in ARMS):
        raise ValueError('incomplete native C3 final cohort')
    result.update(summarize(result))
    atomic(target, result)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-report', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--server', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--resume', action='store_true')
    args = p.parse_args()
    from gist_utility_bench import make
    result = run(args.source_report, make(), args.model, args.server, args.output, args.resume)
    print(json.dumps({k: v for k, v in result.items() if k not in ARMS}, sort_keys=True))


if __name__ == '__main__':
    main()
