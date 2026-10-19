"""Build two isolated source copies, change one screen, count byte changes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def run(args):
    args.work.mkdir(parents=True, exist_ok=False)
    source = args.work / 'source'
    for name in ('pipeline', 'web', 'tests'):
        shutil.copytree(args.source / name, source / name,
                        ignore=shutil.ignore_patterns('__pycache__', 'vendor'))
    builds, times = [], []
    for name in ('before', 'after'):
        if name == 'after':
            path = source / 'web/assets/df/r3.js'
            path.write_text(path.read_text() + '\n// isolated screen-only mutation\n')
        dest = (args.work / name / 'signal-desk').resolve()
        started = time.monotonic()
        result = subprocess.run([sys.executable, '-m', 'tests.build_site', '--published', str(args.published.resolve()),
                                 '--flash', str(args.flash.resolve()), '--out', str(dest)], cwd=str(source),
                                text=True, capture_output=True, timeout=120, check=True)
        times.append(round(time.monotonic() - started, 3))
        (args.work / (name + '.log')).write_text(result.stdout + result.stderr)
        builds.append(hashes(dest))
    old, new = builds
    changed = sorted(p for p in set(old) | set(new) if old.get(p) != new.get(p))
    articles = [p for p in changed if p.startswith('a/') and p.endswith('.html')]
    return {'ok': len(changed) <= args.limit and not articles, 'limit': args.limit,
            'changed': len(changed), 'articles_changed': len(articles), 'files': changed,
            'build_seconds': times, 'article_count': sum(p.startswith('a/') and p.endswith('.html') for p in new)}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--source', type=Path, default=ROOT)
    parser.add_argument('--published', type=Path, default=Path('.qa/snapshot-r/gh-pages'))
    parser.add_argument('--flash', type=Path, default=Path('.qa/snapshot-r/flash'))
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=100)
    args = parser.parse_args()
    args.work = args.work.resolve()
    report = run(args)
    (args.work / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'files'}))
    return int(not report['ok'])


if __name__ == '__main__':
    raise SystemExit(main())
