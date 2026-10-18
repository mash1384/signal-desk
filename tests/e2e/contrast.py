"""Compare numerical contrast, including axe incomplete/pass classifications."""
import json
import math


def node_key(rule, target):
    return rule + '|' + json.dumps(target, sort_keys=True)


def ratios(results):
    values = {}
    for group in ('violations', 'incomplete', 'passes'):
        for rule in results[group]:
            if rule['id'] != 'color-contrast':
                continue
            for node in rule['nodes']:
                measured = [check.get('data', {}).get('contrastRatio') for check in node.get('checks', []) if isinstance(check.get('data'), dict)]
                measured = [x for x in measured if isinstance(x, (float, int)) and math.isfinite(x)]
                if measured:
                    values[node_key(rule['id'], node['target'])] = min(measured)
    return values


def regressions(expected, actual, tolerance):
    return [{'kind': 'contrast-regression', 'node': key, 'before': before, 'after': actual[key], 'tolerance': tolerance}
            for key, before in expected.items() if key in actual and actual[key] < before - tolerance]
