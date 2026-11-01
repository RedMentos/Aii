#!/usr/bin/env python3
"""Privacy scan for the public RedMentos/Aii repo, run by Claude and GPT before every push (cross-review rule 2026-10-21).

Scans the lines ADDED between two revisions (default: merge-base with the shared branch .. HEAD, plus staged and
unstaged changes) for credentials, personal contact data and device identifiers. Exit 0 = clean, 1 = hits, 2 = usage.
Container paths (/workspace/scratch, /home/user, /root/...) are generic and allowed. A hit is a stop sign, not proof:
look at it, remove it from the commit, and keep private material on Drive only.

    python scripts/public_repo_privacy_scan.py                      # HEAD vs origin/claude/project-thread-0zelvf
    python scripts/public_repo_privacy_scan.py --base a1973d4 --head origin/codex/continuation-20261016
"""
import argparse
import re
import subprocess
import sys

PATTERNS = {
    'github_token': r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}',
    'openai_or_anthropic_key': r'\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}',
    'aws_key': r'\bAKIA[0-9A-Z]{16}\b',
    'google_api_key': r'\bAIza[0-9A-Za-z_-]{35}\b',
    'slack_token': r'\bxox[abprs]-[A-Za-z0-9-]{10,}',
    'private_key': r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    'bearer_header': r'(?i)\bauthorization:\s*bearer\s+[A-Za-z0-9._-]{20,}',
    'password_assignment': r'(?i)\b(?:password|passwd|api_key|secret_key)\s*[:=]\s*["\'][^"\'\s]{6,}["\']',
    'email': r'\b[A-Za-z0-9._%+-]+@(?:gmail|googlemail|yahoo|outlook|hotmail|gmx|web|icloud|proton(?:mail)?)\.[a-z]{2,}\b',
    'phone_number': r'(?<![\d.])\+\d{2}[ ]?\d{3}[ ]?\d{5,8}(?!\d)',
    'android_device_id': r'(?i)\b(?:imei|android_id|ro\.serialno|serial_number|serialno)\b\s*["\']?\s*[:=]\s*["\']?[0-9A-Za-z]{6,}',
    'termux_user_home': r'/data/data/com\.termux/files/home/(?!v13\b)[^\s"\']+/(?:\.ssh|\.config/gh|\.netrc)',
    'drive_share_link_with_key': r'drive\.google\.com/[^\s"\']*resourcekey=',
}
ALLOW = re.compile(r'example\.(?:com|org)|<redacted>|PRIVACY_SCAN_ALLOW')


def git(*args):
    return subprocess.run(('git',) + args, capture_output=True, encoding='utf-8', errors='replace', check=True).stdout


def added_lines(diff):
    path, line_no = None, 0
    for line in diff.splitlines():
        if line.startswith('+++ '):
            path = line[6:] if line.startswith('+++ b/') else None
        elif line.startswith('@@'):
            m = re.search(r'\+(\d+)', line)
            line_no = int(m.group(1)) - 1 if m else 0
        elif line.startswith('+') and path:
            line_no += 1
            yield path, line_no, line[1:]
        elif not line.startswith('-'):
            line_no += 1


def scan(diff):
    rx = {k: re.compile(v) for k, v in PATTERNS.items()}
    hits = []
    for path, no, text in added_lines(diff):
        if ALLOW.search(text):
            continue
        for kind, r in rx.items():
            if r.search(text):
                hits.append((path, no, kind, text.strip()[:120]))
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--base', default='origin/claude/project-thread-0zelvf')
    ap.add_argument('--head', default='HEAD')
    ap.add_argument('--no-worktree', action='store_true', help='ignore staged/unstaged changes')
    a = ap.parse_args(argv)
    try:
        base = git('merge-base', a.base, a.head).strip()
        diff = git('diff', '--no-color', '-U0', '--text', base, a.head)
        if not a.no_worktree and a.head == 'HEAD':
            diff += git('diff', '--no-color', '-U0', '--text', 'HEAD')
    except subprocess.CalledProcessError as exc:
        print('usage error:', exc.stderr.strip(), file=sys.stderr)
        return 2
    hits = scan(diff)
    for path, no, kind, text in hits:
        print(f'{path}:{no}: {kind}: {text}')
    print(f'privacy scan {base[:9]}..{a.head}: {"CLEAN" if not hits else str(len(hits)) + " HIT(S)"}')
    return 1 if hits else 0


if __name__ == '__main__':
    sys.exit(main())
