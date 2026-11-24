#!/usr/bin/env python3
"""Real HTTP/model path with explicitly SYNTHETIC slots, never a learned-memory quality proof.

Usage: native_firing_smoke.py --binary SERVER --model GGUF --out NEW_DIRECTORY
Requires LFM2 1024D (current pinned C3); diagnostic and non-diagnostic arms use
identical synthetic bytes. Nothing is registered or activated in a live home.
"""
import argparse
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fast_trace_compare import serve, ask
from v13.common import atomic_write, file_hash
from v13.memory_trainer import live_system
from v13.memory_server import runtime_library_hashes
from v13.sparse_audit import read_firing_window


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    memory = out/'synthetic-memory.bin'
    hidden = 1024
    # Three always-threshold-eligible rows: actual tiny nonzero residual,
    # impossible entity guard, and zero value. This is authored protocol data.
    floats = [0.] * hidden + [0.] * (3*hidden) + [-1.] * 3
    values = [0.] * (3*hidden)
    values[0] = .001
    values[hidden] = .001
    floats += values
    memory.write_bytes(b'V13SMEM1' + struct.pack('<6i2f', 0, hidden, 3, 1, 3, 1, .01, 1.)
                       + struct.pack('<%df'%len(floats), *floats) + struct.pack('<3i', -1, 2147483647, -1))
    binding = {'binary_sha256': file_hash(args.binary), 'runtime_libraries_sha256': runtime_library_hashes(args.binary),
               'model_sha256': file_hash(args.model),
               'memory_sha256': file_hash(memory), 'script_sha256': file_hash(__file__),
               'header_sha256': file_hash(Path(__file__).with_name('v13_memory_hook.h')),
               'parser_sha256': file_hash(Path(__file__).parents[1]/'v13/sparse_audit.py')}
    prompts = ['Reply with the word hello.', 'What is two plus two?', 'Reply with the word hello.']
    report = {'status': 'RUNNING', 'binding': binding, 'memory_origin': 'SYNTHETIC_PROTOCOL_FIXTURE',
              'phone_measured': False, 'learned_recall_proven': False, 'activation_authorized': False,
              'arms': {}}
    def save():
        atomic_write(out/'report.json', json.dumps(report, indent=2, ensure_ascii=False))
    save()
    try:
        for enabled, port in ((False, 8651), (True, 8652)):
            log = out/('audit-on.log' if enabled else 'audit-off.log')
            process = serve(args.binary, args.model, str(memory), port, str(log), audit_firing=enabled)
            rows = report['arms'].setdefault('audit_on' if enabled else 'audit_off', [])
            try:
                for index, prompt in enumerate(prompts):
                    offset = log.stat().st_size
                    answer, tokens, seconds = ask(port, live_system(), prompt)
                    row = {'index': index, 'prompt': prompt, 'answer': answer,
                           'prompt_tokens': tokens, 'seconds': seconds}
                    if enabled:
                        row['native_firing'] = read_firing_window(log, offset)
                    rows.append(row)
                    save()
            finally:
                process.terminate()
                process.wait(timeout=30)
        off, on = report['arms']['audit_off'], report['arms']['audit_on']
        checks = {'answers_identical': all(a['answer'] == b['answer'] for a, b in zip(off, on)),
                  'prompt_tokens_identical': all(a['prompt_tokens'] == b['prompt_tokens'] for a, b in zip(off, on)),
                  'three_requests_bound': [r['native_firing'].get('request') for r in on] == [1, 2, 3],
                  'all_requests_observed': all(r['native_firing']['status'] == 'OBSERVED_NATIVE_WRITES' for r in on),
                  'only_nonzero_unguarded_row_fired': all(r['native_firing'].get('fired_rows') == [0] for r in on),
                  'entity_guard_blocked': all(r['native_firing'].get('slot_guard_blocked_counts', [0,0])[1] > 0 for r in on)}
        report['checks'] = checks
        report['status'] = 'PASS_EXECUTION_ONLY' if all(checks.values()) else 'FAIL'
        save()
        print(json.dumps({'status': report['status'], 'checks': checks}))
        if not all(checks.values()):
            raise SystemExit(1)
    except BaseException as exc:
        report['error'] = {'type': type(exc).__name__, 'detail': str(exc)[:400]}
        if report['status'] == 'RUNNING':
            report['status'] = 'INCOMPLETE'
        save()
        raise


if __name__ == '__main__':
    main()
