"""Manual local-only entrypoint for the narrow AGE0d answer-aware arithmetic audit.

No automatic runtime hook, no network, no store, no logging of user text.
Usage: python scripts/age0d_cli.py --stdin-json < private-input.json
"""
import argparse
import json
import sys

try:
    from .age0d_answer_audit import audit
except ImportError:  # direct invocation from scripts/ directory
    from age0d_answer_audit import audit

MAX_INPUT_CHARS = 4096


def _invalid():
    return {'status': 'ABSTAIN', 'reason': 'INVALID_INPUT',
            'delivery_allowed': False, 'authority': 'NONE',
            'evidence_level': 'SOFTWARE_DETERMINISTIC_ONLY'}


def main(argv=None, stdin=None, stdout=None):
    parser = argparse.ArgumentParser(description='AGE0d local diagnostic; never sends a correction')
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--stdin-json', action='store_true', help='read one private JSON object from stdin')
    modes.add_argument('--demo', action='store_true', help='run a synthetic example only')
    args = parser.parse_args(argv)
    inp = sys.stdin if stdin is None else stdin
    out = sys.stdout if stdout is None else stdout
    if args.demo:
        result = audit('What is 2 + 2?', '5')
        result['scope'] = 'SYNTHETIC_DEMO_ONLY'
        out.write(json.dumps(result, sort_keys=True) + '\n')
        return 0
    try:
        raw = inp.read(MAX_INPUT_CHARS + 1)
        if not isinstance(raw, str) or len(raw) > MAX_INPUT_CHARS:
            raise ValueError('invalid length')
        data = json.loads(raw)
        if (type(data) is not dict or set(data) != {'question', 'answer'}
                or type(data['question']) is not str or type(data['answer']) is not str):
            raise ValueError('invalid shape')
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        out.write(json.dumps(_invalid(), sort_keys=True) + '\n')
        return 2
    result = audit(data['question'], data['answer'])
    out.write(json.dumps(result, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
