"""Add ratios once, retaining all baseline fields and exact original violation keys.
Run two normal full matrices first, then:
python -m tests.e2e.augment_contrast --first REPORT --second REPORT
Changed/missing keys, incomplete runs, missing ratios or >.05 drift abort without writing.
"""
import argparse
import copy
import json
from pathlib import Path

BASELINE = Path(__file__).parent / 'baseline.json'


def augment(baseline, first, second):
    if 'contrast' in baseline:
        raise ValueError('contrast already recorded; replacement forbidden')
    expected = baseline['axe']
    measurements = []
    for report in (first, second):
        rows = report['cases']
        if len(rows) != 48 or len({r['key'] for r in rows}) != 48 or {r['key'] for r in rows} != set(expected):
            raise ValueError('complete original 48-case key set required')
        out = {}
        for row in rows:
            key = row['key']
            if row.get('incomplete') or row['errors'] or set(row['axe']) != set(expected[key]):
                raise ValueError('baseline node keys changed or failed case: ' + key)
            keys = {k for k in expected[key] if k.startswith('color-contrast|')}
            if not keys <= row['contrast'].keys():
                raise ValueError('baseline contrast measurement missing: ' + key)
            out[key] = {k: row['contrast'][k] for k in sorted(keys)}
        measurements.append(out)
    drift = max(abs(v - measurements[1][case][key]) for case, values in measurements[0].items() for key, v in values.items())
    if drift > .05:
        raise ValueError('contrast drift exceeds .05: ' + str(drift))
    result = copy.deepcopy(baseline)
    result['contrast'] = measurements[0]
    result['contrast_measurement'] = {'max_two_run_drift': round(drift, 6), 'tolerance': round(drift, 6),
                                      'method': 'axe 4.10.3 check.data.contrastRatio; same snapshot/build, two full 48-case runs; original node keys unchanged'}
    assert all(result[k] == v for k, v in baseline.items())
    return result


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--first', type=Path, required=True)
    p.add_argument('--second', type=Path, required=True)
    args = p.parse_args()
    out = augment(json.loads(BASELINE.read_text()), json.loads(args.first.read_text()), json.loads(args.second.read_text()))
    BASELINE.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(out['contrast_measurement']))


if __name__ == '__main__':
    main()
