"""Read-only, source-bound STEP2 TP/s27 visibility diagnosis.

Measures whether the C3 consumer was actually shown the literal rule and option
fields needed for the existing eligibility recipe. Never imports oracle values
into the extraction path, modifies weights, or promotes a Canon gate.

Usage: python step2_tp27_visibility_diagnostic.py --zip ORIGINAL.zip \
  --sha256 EXPECTED_ZIP_SHA256 --head EXPECTED_GIT_HEAD --out report.json

The evidence ZIP must be the original sealed GitHub Actions artifact; a fresh
synthetic ZIP may be used for tests, but must not be represented as native proof.
"""
import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

SCHEMA = 'V13_STEP2_TP27_VISIBILITY_DIAGNOSTIC_V1'
VARIANTS = ('b1_only', 'b2_only', 'both_control', 'both_exact', 'both_none',
            'prompt_only_dual', 'same_policy_dual')
RULES = {'budget': r'\bbudget(?:\s+of)?\s+(\d+)\s+euros?\b',
         'deadline': r'\bdeadline(?:\s+of)?\s+(\d+)\s+days?\b',
         'local_only': r'\blocal-only\s+requirement:?\s+(true|false)\b'}
OPTION = re.compile(r'\boption\s+([AB]):\s*cost\s+(\d+)\s+euros?,\s*duration\s+(\d+)\s+days?,\s*local\s+(true|false)\b', re.I)
MAX_ZIP = 25_000_000
MAX_ENTRY = 12_000_000
MAX_ENTRIES = 100
REGISTERED_ZIP_SHA256 = '965bf4ef904cf96c759e1324b74c23662b03f1aa1c5c4698be71e9f5bb9db635'
REGISTERED_HEAD = 'fa76c7599fc066b7cb2d58b133a649bd9604ded9'
REQUIRED_EXITS = ('BLOBS','BOOTSTRAP','COMPILE','DIFF','FOCUSED','FULL','FULL_INSTALL','INSTALL','NATIVE','PRIVACY','REPLAY')


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_archive(path, expected_sha, expected_head):
    if expected_sha != REGISTERED_ZIP_SHA256 or expected_head != REGISTERED_HEAD:
        raise ValueError('NOT_REGISTERED_TP27_EVIDENCE')
    path = Path(path)
    if path.stat().st_size > MAX_ZIP or sha(path.read_bytes()) != expected_sha:
        raise ValueError('ZIP_SIZE_OR_HASH_MISMATCH')
    with zipfile.ZipFile(path) as z:
        entries = z.infolist()
        if len(entries) > MAX_ENTRIES or z.testzip() is not None:
            raise ValueError('ZIP_CRC_OR_ENTRY_COUNT')
        names = set()
        for entry in entries:
            n = entry.filename
            if (n in names or not n or n.startswith('/') or '\\' in n or
                    '..' in Path(n).parts or entry.is_dir() or
                    (entry.external_attr >> 16) & 0o170000 == 0o120000 or
                    entry.file_size > MAX_ENTRY):
                raise ValueError('UNSAFE_ZIP_ENTRY')
            names.add(n)
        required = {'SHA256SUMS.txt', 'HEAD.txt', 'RECEIPT.json', 'step2_TP_s27.json',
                    'tool_TP_s27.json', 'summary_TP_s27.json', 'tool_TP_s27.preregistration.json'}
        required.update(n+'_EXIT.txt' for n in REQUIRED_EXITS)
        if not required.issubset(names):
            raise ValueError('MISSING_EVIDENCE')
        if z.read('HEAD.txt').decode().strip() != expected_head:
            raise ValueError('WRONG_SOURCE_HEAD')
        checks = z.read('SHA256SUMS.txt').decode().splitlines()
        covered = set()
        for line in checks:
            m = re.fullmatch(r'([0-9a-f]{64})\s+\*?(?:\./)?([^\s]+)', line)
            if m is None or m[2] in covered or m[2] not in names or sha(z.read(m[2])) != m[1]:
                raise ValueError('INVALID_SHA256SUMS')
            covered.add(m[2])
        if covered != names - {'SHA256SUMS.txt'}:
            raise ValueError('INCOMPLETE_SHA256SUMS')
        for name in names:
            if name.endswith('_EXIT.txt') and z.read(name).decode().strip() != '0':
                raise ValueError('NONZERO_STAGE_EXIT')
        receipt = json.loads(z.read('RECEIPT.json'))
        if receipt.get('schema') != 'v13.step2.tp27.full70.native_tool.v1' or receipt.get('arm') != 'TP' or receipt.get('seed') != 27:
            raise ValueError('WRONG_REGISTERED_ARM')
        if (receipt.get('native_rows') != 70 or receipt.get('tool_rows') != 70 or
                receipt.get('canonical_gate_pass') is not False or
                receipt.get('redmi_measured') is not False or
                receipt.get('jepa_weight') != 0):
            raise ValueError('UNSAFE_GATE_CLAIM')
        mapping = [('raw_source_sha256', 'step2_TP_s27.json'),
                   ('raw_summary_sha256', 'summary_TP_s27.json'),
                   ('raw_tool_sha256', 'tool_TP_s27.json'),
                   ('raw_tool_prereg_sha256', 'tool_TP_s27.preregistration.json')]
        for key, name in mapping:
            if receipt.get(key) != sha(z.read(name)):
                raise ValueError('RECEIPT_HASH_MISMATCH')
        return (json.loads(z.read('step2_TP_s27.json')),
                json.loads(z.read('tool_TP_s27.json')), receipt)


def checked_rows(native, tool):
    if (native.get('status') not in ('UTILITY_FAIL', 'UTILITY_PASS_SCOPED') or
            tool.get('status') not in ('TOOL_UTILITY_FAIL', 'TOOL_UTILITY_PASS_SCOPED') or
            tool.get('canonical_gate_pass') is not False):
        raise ValueError('INVALID_OR_PROMOTED_STATUS')
    fixtures = native.get('fixtures')
    if type(fixtures) is not list or len(fixtures) != 10 or len({f.get('id') for f in fixtures}) != 10:
        raise ValueError('FIXTURE_SET_CHANGED')
    expected = {(f['id'], v) for f in fixtures for v in VARIANTS}
    for report in (native, tool):
        rows = report.get('rows')
        if type(rows) is not list or len(rows) != 70:
            raise ValueError('ROW_COUNT')
        ids = [(r.get('fixture'), r.get('variant')) for r in rows]
        if len(set(ids)) != 70 or set(ids) != expected:
            raise ValueError('ROW_IDENTITY')
        hashes = report.get('row_sha256')
        if type(hashes) is not dict or set(hashes) != {f+':'+v for f,v in expected}:
            raise ValueError('ROW_DIGEST_SET')
        for row in rows:
            key = row['fixture']+':'+row['variant']
            if sha(canonical(row)) != hashes[key]:
                raise ValueError('ROW_DIGEST_MISMATCH')
            if row.get('oracle_visible_to_native') is not False:
                raise ValueError('ORACLE_LEAK')
    tools = {(r['fixture'],r['variant']):r for r in tool['rows']}
    for row in native['rows']:
        t = tools[(row['fixture'],row['variant'])]
        if t.get('consumer_messages_sha256') != sha(canonical(row.get('consumer_messages'))):
            raise ValueError('CONSUMER_MESSAGES_MISMATCH')
    return native['rows'], tools


def fields(text):
    result = {}
    for key, rx in RULES.items():
        values = re.findall(rx, text, re.I)
        vals = {x.lower() == 'true' if key == 'local_only' else int(x) for x in values}
        result[key] = vals
    return result


def _visible(row):
    messages = row['consumer_messages']
    if type(messages) is not list or sum(m.get('role') == 'user' for m in messages) != 1:
        raise ValueError('CONSUMER_FORMAT')
    packet = json.loads(next(m['content'] for m in messages if m['role'] == 'user'))
    if type(packet) is not dict or type(packet.get('current_source')) is not str or type(packet.get('analysts')) is not list:
        raise ValueError('CONSUMER_PACKET')
    current = packet['current_source']
    evidence = row.get('source_evidence')
    if type(evidence) is not list or not evidence:
        raise ValueError('MISSING_SOURCE_EVIDENCE')
    source_texts = []
    for source in evidence:
        if type(source) is not dict or type(source.get('text')) is not str or type(source.get('source_ref')) is not dict:
            raise ValueError('SOURCE_REF_FORMAT')
        ref = source['source_ref']
        if (type(ref.get('source_id')) is not str or not re.fullmatch(r'src_[0-9a-f]{32}',ref['source_id']) or
                type(ref.get('sha256')) is not str or not re.fullmatch(r'[0-9a-f]{64}',ref['sha256']) or
                type(ref.get('char_start')) is not int or type(ref.get('char_end')) is not int or
                ref['char_start'] < 0 or ref['char_end'] - ref['char_start'] != len(source['text'])):
            raise ValueError('SOURCE_REF_FORMAT')
        source_texts.append(source['text'])
    if current not in source_texts:
        raise ValueError('CURRENT_NOT_SOURCE_BACKED')
    quotes = []
    for analyst in packet['analysts']:
        if type(analyst) is not dict or type(analyst.get('verified_quotes')) is not list:
            raise ValueError('INVALID_ANALYST_QUOTES')
        for q in analyst['verified_quotes']:
            if type(q) is not str or not any(q in text for text in source_texts):
                raise ValueError('UNBACKED_VERIFIED_QUOTE')
            quotes.append(q)
    current_rules = fields(current)
    quote_rules = [fields(q) for q in quotes]
    resolved = {}
    origins = {}
    for k in RULES:
        a = current_rules[k]
        b = set().union(*(x[k] for x in quote_rules)) if quote_rules else set()
        chosen = a if a else b
        resolved[k] = next(iter(chosen)) if len(chosen) == 1 else None
        origins[k] = 'current' if a else ('quotes' if b else 'missing')
    opts = {}
    for text in [current, *quotes]:
        for m in OPTION.finditer(text):
            item = (int(m[2]), int(m[3]), m[4].lower() == 'true')
            opts.setdefault(m[1].upper(), set()).add(item)
    options = {k: next(iter(v)) if len(v) == 1 else None for k,v in opts.items()}
    complete = all(v is not None for v in resolved.values()) and all(options.get(k) is not None for k in 'AB')
    return {'rules': resolved, 'origins': origins, 'options': options, 'complete': complete}


def analyze(native, tool, receipt, zip_sha256, head):
    rows, tools = checked_rows(native, tool)
    counts = {v:Counter() for v in VARIANTS}
    fixture_type = {f['id']:f['type'] for f in native['fixtures']}
    for row in rows:
        v = row['variant']
        vis = _visible(row)
        c = counts[v]
        c['rows'] += 1
        for k in RULES:
            if vis['rules'][k] is not None:
                c['visible_'+k] += 1
                if vis['origins'][k] == 'quotes':c['quoted_'+k] += 1
        for e in 'AB':
            if vis['options'].get(e) is not None:c['visible_option_'+e] += 1
        if vis['complete']:
            c['complete_visible'] += 1
            if tools[(row['fixture'],v)]['score']['exact']:
                c['native_tool_exact_with_complete_visible'] += 1
        answer = tools[(row['fixture'],v)].get('answer')
        try: action = json.loads(answer).get('action')
        except (TypeError,ValueError,AttributeError):action = None
        if action == 'UNKNOWN':c['tool_unknown'] += 1
        score = tools[(row['fixture'],v)]['score']
        if score.get('exact'):
            c['tool_exact'] += 1
        checks = score.get('field_checks',{})
        if type(checks) is dict and checks and all(value is True for key,value in checks.items() if key != 'project'):
            c['tool_decision_exact'] += 1
        if fixture_type[row['fixture']] in ('SPLIT','RULE'):
            c['earlier_rule_fixture'] += 1
            if all(vis['rules'][k] is not None for k in RULES):c['earlier_rule_fully_visible'] += 1
    return {'schema':SCHEMA, 'scope':'POST_HOC_LINUX_NATIVE_SOURCE_VISIBILITY_DIAGNOSTIC',
            'zip_sha256':zip_sha256, 'source_head':head,
            'receipt_source_sha256':receipt['raw_source_sha256'],
            'receipt_tool_sha256':receipt['raw_tool_sha256'],
            'native_rows':70, 'tool_rows':70,
            'per_variant':{v:{**{key:0 for key in ('complete_visible','earlier_rule_fully_visible','tool_unknown','tool_decision_exact','tool_exact', 'visible_budget','visible_deadline','visible_local_only','quoted_budget','quoted_deadline','quoted_local_only')}, **dict(counts[v])} for v in VARIANTS},
            'claim_limits':['Visibility is not comprehension or learning.',
                            'Verified quotes are the only prior-source evidence counted; oracle fields are never used for extraction.',
                            'Post-hoc analysis, not a preregistered performance gate.',
                            'Only TP/s27, not 12-arm/three-seed STEP2.',
                            'No Android/Redmi run, no model training, no B3/Body-JEPA promotion.'],
            'canonical_gate_pass':False, 'jepa_weight':0,
            'age_authority':0, 'whole_system_complete':False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--zip',required=True,type=Path)
    p.add_argument('--sha256',required=True)
    p.add_argument('--head',required=True)
    p.add_argument('--out',required=True,type=Path)
    args = p.parse_args()
    native,tool,receipt = read_archive(args.zip,args.sha256,args.head)
    result = analyze(native,tool,receipt,args.sha256,args.head)
    if args.out.exists():raise ValueError('OUTPUT_EXISTS_REFUSE_OVERWRITE')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_bytes(canonical(result)+b'\n')
    print(json.dumps({'status':'DIAGNOSTIC_ONLY', 'per_variant':result['per_variant']},sort_keys=True))

if __name__ == '__main__':main()
