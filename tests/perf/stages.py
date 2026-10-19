"""Local-only build timings; never runs acquisition, AI, dispatch or upload."""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shutil
import sys
import time
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--published', required=True)
    parser.add_argument('--flash', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--output', type=Path, default=Path('.qa/build-stages.json'))
    args = parser.parse_args()
    os.environ['SIGNAL_FLASH_DIR'] = str(Path(args.flash).resolve())
    from pipeline import build, prerender, public_data, article_bundle, util
    from tests import build_site
    records = {}

    def timed(name, fn):
        depth = [0]
        records[name] = {'calls': 0, 'seconds': 0.0}

        def wrapper(*a, **kw):
            depth[0] += 1
            start = time.monotonic()
            try:
                return fn(*a, **kw)
            finally:
                depth[0] -= 1
                if not depth[0]:
                    records[name]['calls'] += 1
                    records[name]['seconds'] += time.monotonic() - start
        return wrapper

    start = time.monotonic()
    with ExitStack() as stack:
        for module, names in [(prerender, ['render']), (public_data, ['copy_daily']), (article_bundle, ['bundle']),
                              (shutil, ['copytree']), (build, ['build_site', 'df_ver', 'stamp_df_imports', 'related', 'page_article']),
                              (util, ['write_text'])]:
            for name in names:
                key = module.__name__ + '.' + name
                stack.enter_context(patch.object(module, name, timed(key, getattr(module, name))))
        stack.enter_context(patch.object(sys, 'argv', ['tests.build_site', '--published', args.published,
                                                      '--flash', args.flash, '--out', args.out]))
        build_site.main()
    report = {'total_seconds': round(time.monotonic() - start, 3),
              'scope': 'local snapshots only; inclusive function timings overlap and must not be summed',
              'functions': {k: {**v, 'seconds': round(v['seconds'], 4)} for k, v in records.items()}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
