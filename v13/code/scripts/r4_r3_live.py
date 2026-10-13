"""R4 part 11: wordings only rule R3 recognises (part 10), measured live like part 6 on fresh seed 29.

Under the part-6 rule these questions got no proposal; under R3 (agi/listarith.operation since part 10) they do. Capture
reuses r4_listarith_live.capture unchanged; only the task sets are replaced (all rows go into its 'match' slot).
  capture   r4_r3_live.py capture <installed_home> <out.json>
  prereg    r4_r3_live.py prereg <prereg.json>
  evaluate  r4_r3_live.py evaluate <prereg.json> <fresh.json> <report.json>"""
import hashlib
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write  # noqa: E402
from v13.agi import listarith  # noqa: E402
import r4_listarith_live as M  # noqa: E402
import r4_rule_question_only as Q  # noqa: E402
import utility_bench2 as U2  # noqa: E402

SEED = 29
NEW = {'summary': 'Is the summary line correct? Add the items up and give the right figure.',
       'compare': 'Which city was the wettest, and by how many millimetres did it exceed the driest one?'}
DECISION = (f"Fresh seed {SEED}, 30 tasks (15 summary, 15 compare) with wordings only R3 recognises: R3_LIVE_SUPPORTED iff "
            "tool_active vs c3_alone net wins >= +5 AND sign test p < .05 AND tool values correct >= 28/30 AND no kind loses more than 2.")


def rows(seed=SEED):
    out = []
    for fid, text, nums, checks in U2.tasks(seed):
        kind = fid.rstrip('0123456789')
        if kind in NEW:
            old = M.SUMMARY_Q if kind == 'summary' else M.COMPARE_Q
            t = text[:-len(old)]+NEW[kind]
            assert Q.r0(t) is None or kind == 'summary', fid  # compare: part-6 rule saw nothing
            assert listarith.operation(t) == ('total' if kind == 'summary' else 'difference_max_min'), fid
            out.append((fid, t, nums, checks))
    return out


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def capture(installed, out):
    M.task_sets = lambda seed: {'orig': [], 'match': rows(seed), 'nomatch': []}
    M.capture(installed, SEED, out)


def prereg(out):
    body = {'schema': 'v13-r4-r3-live-prereg-v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'seed': SEED,
            'new_wordings': NEW, 'n': len(rows()), 'decision_rule': DECISION, 'script_sha256': sha(__file__),
            'capture_script_sha256': sha(M.__file__), 'code_sha256': M.code_sha()}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


def evaluate(reg_path, fresh, out):
    reg = json.loads(Path(reg_path).read_text()); d = json.loads(Path(fresh).read_text())
    if (reg['script_sha256'], reg['capture_script_sha256'], reg['code_sha256']) != (sha(__file__), sha(M.__file__), M.code_sha()) \
            or d['task_seed'] != SEED or d.get('code_sha256') != reg['code_sha256'] or len(d['rows']) != 30:
        raise SystemExit('script/code changed or capture incomplete')
    s = M.summarize(d['rows'])['match']; drop = max(k['c3_alone']-k['tool_active'] for k in s['by_kind'].values())
    ok = s['net'] >= 5 and s['sign_test_p'] < .05 and s['value_correct'] >= 28 and drop <= 2
    body = {'prereg_sha256': sha(reg_path), 'fresh_sha256': sha(fresh), 'result': s, 'max_kind_drop': drop,
            'verdict': 'R3_LIVE_SUPPORTED' if ok else 'NOT_SUPPORTED', 'age_right_replaced_for_measurement': True, 'phone_measured': False}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'capture':
        capture(a[1], a[2])
    elif a[0] == 'prereg':
        prereg(a[1])
    else:
        evaluate(a[1], a[2], a[3])
