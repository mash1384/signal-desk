"""Fail closed on missing measurements, vitals regressions and transfer caps."""
import argparse
import json
import math
from pathlib import Path

from tests.perf.vitals import PAGES, DEVICES, aggregate, METRICS

TRANSFER = ('bytes', 'font_files', 'font_bytes', 'js_bytes')
CASES = {(page, device) for page in PAGES for device in DEVICES}


def cases(report):
    rows = report.get('medians', [])
    keys = [(row.get('page'), row.get('device')) for row in rows]
    if len(keys) != len(CASES) or set(keys) != CASES:
        raise ValueError('all 16 unique page/device measurements are required')
    for row in rows:
        if row.get('runs') != 3:
            raise ValueError('three cold runs per case are required')
        for name in ('lcp_ms', 'cls', 'requests') + TRANSFER:
            value = row.get(name)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError('invalid metric: ' + name)
        if not row['lcp_ms'] or not row['bytes']:
            raise ValueError('empty LCP/transfer measurement')
    return dict(zip(keys, rows))


def make_caps(before, after, previous=None):
    b, a = cases(before), cases(after)
    old = {(r['page'], r['device']): r for r in (previous or {}).get('caps', [])}
    rows = []
    for key, row in a.items():
        cap = {'page': key[0], 'device': key[1]}
        for name in TRANSFER:
            candidates = [math.ceil(row[name] * 1.15), math.ceil(b[key][name] * 1.15)]
            if key in old:
                candidates.append(old[key][name])
            cap[name] = min(candidates)
        rows.append(cap)
    return {'rule': 'measured after +15%, bounded by before +15% and any prior cap; never raise', 'caps': rows}


def check(before, after, budgets):
    failures = []
    try:
        b, a = cases(before), cases(after)
        caps = {(r['page'], r['device']): r for r in budgets['caps']}
        if set(caps) != CASES or len(budgets['caps']) != len(CASES):
            raise ValueError('all 16 transfer caps required')
        for name in ('version', 'mobile_network', 'local_compression', 'requests', 'cls', 'lang', 'mode'):
            if before['method'].get(name) != after['method'].get(name):
                raise ValueError('measurement method changed: ' + name)
        if after['method']['mode'] != 'local':
            raise ValueError('regression gate requires fixed local snapshot')
        if len(after.get('runs', [])) != 48:
            raise ValueError('48 raw run records required')
        samples = {(r['page'], r['device'], r.get('attempt')) for r in after['runs']}
        if samples != {(p, d, n) for p, d in CASES for n in (1, 2, 3)}:
            raise ValueError('one independent run per page/device/attempt required')
        recalculated = {(r['page'], r['device']): r for r in aggregate(after['runs'])}
        for key, row in a.items():
            if any(row[name] != recalculated[key][name] for name in METRICS):
                raise ValueError('median does not match raw records: ' + str(key))
        for run in after['runs']:
            if run.get('errors'):
                failures.append({'case': [run['page'], run['device']], 'check': 'browser/transport', 'errors': run['errors']})
        for key, row in a.items():
            if row['lcp_ms'] > b[key]['lcp_ms'] * 1.2:
                failures.append({'case': key, 'check': 'LCP regression >20%', 'actual': row['lcp_ms'], 'limit': b[key]['lcp_ms'] * 1.2})
            if key[1] == 'mobile':
                for metric, limit in [('lcp_ms', 2500), ('cls', .1)]:
                    if row[metric] > limit:
                        failures.append({'case': key, 'check': metric, 'actual': row[metric], 'limit': limit})
            for name in TRANSFER:
                limit = caps[key][name]
                if limit > math.ceil(b[key][name] * 1.15):
                    failures.append({'case': key, 'check': 'raised original cap: ' + name})
                if row[name] > limit:
                    failures.append({'case': key, 'check': name, 'actual': row[name], 'limit': limit})
    except (KeyError, TypeError, ValueError) as error:
        failures.append({'check': 'invalid evidence', 'error': str(error)})
    return failures


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--before', type=Path, default=Path('docs/test-handoff/perf-before.json'))
    p.add_argument('--after', type=Path, required=True)
    p.add_argument('--budgets', type=Path, default=Path('tests/perf/budgets.json'))
    p.add_argument('--write-caps', action='store_true')
    p.add_argument('--output', type=Path, default=Path('.qa/perf-check.json'))
    args = p.parse_args()
    before, after = json.loads(args.before.read_text()), json.loads(args.after.read_text())
    if args.write_caps:
        previous = json.loads(args.budgets.read_text()) if args.budgets.exists() else None
        args.budgets.write_text(json.dumps(make_caps(before, after, previous), indent=2) + '\n')
    failures = check(before, after, json.loads(args.budgets.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'ok': not failures, 'failures': failures}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'ok': not failures, 'failures': failures}, ensure_ascii=False))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
