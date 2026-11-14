#!/usr/bin/env python3
"""Commit and push this workspace; no pull/merge/reset or authenticated URL logs."""
import datetime as dt
import fcntl
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(rb'(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})'),
    re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(rb'(?i)(?:api[_-]?key|auth[_-]?key|service[_-]?key|access[_-]?token|KPX_SERVICE_KEY|KMA_APIHUB_AUTH_KEY|KMA_APIHUB_KEY|DATA_GO_KR_SERVICE_KEY|FRED_API_KEY)[\x22\x27]?\s*[:=]\s*[\x22\x27][A-Za-z0-9_%+/=-]{16,}[\x22\x27]'),
    re.compile(rb'(?i)[?&](?:serviceKey|authKey|api_key)=[A-Za-z0-9_%+/=-]{16,}'),
]

def git(*args, check=True):
    r = subprocess.run(['git', *args], cwd=ROOT, capture_output=True)
    if check and r.returncode:
        # Do not print remote URLs, which could contain credentials.
        raise RuntimeError('git ' + args[0] + ' failed; inspect manually (possible network or remote changes)')
    return r

def scan_staged():
    paths = git('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z').stdout.split(b'\0')
    violations = []
    for raw in filter(None, paths):
        name = os.fsdecode(raw)
        if git('ls-files', '--stage', '--', name).stdout.startswith(b'160000 '):
            continue  # Existing repository recorded as a submodule, no file body.
        content = git('show', ':' + name).stdout
        if len(content) > 5 * 1024 * 1024:
            violations.append((name, 'file exceeds 5 MiB'))
        elif any(p.search(content) for p in PATTERNS):
            violations.append((name, 'possible credential'))
    return violations

def main():
    runtime = ROOT / '.git-sync'
    runtime.mkdir(exist_ok=True)
    with (runtime / 'lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        # Refuse to act during a merge/rebase or while GitHub synchronization is unfinished.
        if git('symbolic-ref', '-q', 'HEAD', check=False).returncode:
            raise RuntimeError('detached HEAD; automatic synchronization stopped')
        for marker in ['MERGE_HEAD', 'rebase-merge', 'rebase-apply', 'CHERRY_PICK_HEAD']:
            location = Path(os.fsdecode(git('rev-parse', '--git-path', marker).stdout).strip())
            if not location.is_absolute(): location = ROOT / location
            if location.exists(): raise RuntimeError('merge/rebase in progress; automatic synchronization stopped')
        git('add', '--all', '--', '.')
        violations = scan_staged()
        if violations:
            for path, reason in violations:
                print('BLOCKED:', path, reason)
            raise RuntimeError('upload blocked by staged-file checks; no commit or push made')
        if git('diff', '--cached', '--quiet', check=False).returncode:
            git('commit', '-m', 'Auto-sync workspace ' + dt.datetime.now().astimezone().isoformat(timespec='seconds'))
        # Retry previous pending commits too. Never force push or auto pull.
        git('push', 'origin', 'HEAD')
        print(dt.datetime.now().astimezone().isoformat(timespec='seconds'), 'GitHub sync complete')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('SYNC STOPPED:', str(exc), file=sys.stderr)
        sys.exit(1)
