"""Prove performance guards reject deliberately damaged copies, not production."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from tests.perf.budgets import check
from tests.perf.fonts import check as font_check, DEST
from tests.perf.vitals import aggregate


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--flash', type=Path, default=Path('.qa/snapshot-r/flash'))
    parser.add_argument('--published', type=Path, default=Path('.qa/snapshot-r/gh-pages'))
    parser.add_argument('--before', type=Path, default=Path('docs/test-handoff/perf-before.json'))
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--budgets', type=Path, default=Path('tests/perf/budgets.json'))
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--channel', default='chrome')
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=False)
    results = []

    def record(name, killed, detail):
        results.append({'name': name, 'killed': bool(killed), 'detail': detail})
        (args.work / 'result.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)
        assert killed, 'mutation survived: ' + name

    before, after, caps = [json.loads(p.read_text()) for p in (args.before, args.after, args.budgets)]
    assert not check(before, after, caps), 'positive measurement must pass before mutation'
    for metric, bad_value in [('lcp_ms', 10000), ('cls', .5), ('bytes', 10000000),
                              ('font_files', 999), ('font_bytes', 10000000), ('js_bytes', 10000000)]:
        bad = copy.deepcopy(after)
        for run in bad['runs']:
            if run['page'] == 'live/' and run['device'] == 'mobile':
                run[metric] = bad_value
        bad['medians'] = aggregate(bad['runs'])
        (args.work / ('bad-' + metric + '.json')).write_text(json.dumps(bad))
        failures = check(before, bad, caps)
        record(metric, any(metric in f.get('check', '') or (metric == 'lcp_ms' and 'LCP' in f.get('check', '')) for f in failures), failures)

    from fontTools.ttLib import TTFont
    fonts = args.work / 'fonts'
    shutil.copytree(DEST, fonts)
    manifest = json.loads((fonts / 'manifest.json').read_text())
    path = fonts / manifest['mono']['file']
    font = TTFont(path)
    for table in font['cmap'].tables:
        table.cmap.pop(ord('1'), None)
    font.save(path)
    manifest['mono']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    (fonts / 'manifest.json').write_text(json.dumps(manifest))
    result = font_check(args.capture, fonts)
    record('mono missing digit', not result['ok'] and '1' in result['missing']['mono'], result['missing'])

    def clone(name):
        dest = args.work / name / 'signal-desk'
        shutil.copytree(args.site, dest, copy_function=os.link)
        return dest

    def alter(path, old, new):
        original = path.read_text()
        assert old in original, ('mutation target absent', str(path), old)
        # Break the hard link atomically; never truncate the original build.
        temp = path.with_name(path.name + '.mutation')
        temp.write_text(original.replace(old, new, 1))
        temp.replace(path)

    def fail_command(name, command, expected, cwd=None):
        done = subprocess.run(command, text=True, capture_output=True, timeout=240, cwd=cwd)
        output = done.stdout + done.stderr
        (args.work / (name + '.log')).write_text(output)
        record(name, done.returncode != 0 and expected in output, {'exit': done.returncode, 'expected': expected})

    archive = Path(__file__).parent / 'fixtures/snapshot-r.tar.gz'
    bad_archive = args.work / 'bad-fixture.tar.gz'
    damaged = bytearray(archive.read_bytes())
    damaged[-1] ^= 1
    bad_archive.write_bytes(damaged)
    fail_command('snapshot-sha', [sys.executable, '-m', 'tests.perf.snapshot', '--archive', str(bad_archive),
                                  '--out', str(args.work / 'bad-fixture')], 'fixture archive checksum mismatch')

    broken = clone('no-prerender')
    for name in ('live', 'brief', 'calendar'):
        alter(broken / name / 'index.html', 'if(t){app.replaceChildren', 'if(false&&t){app.replaceChildren')
    for scenario, expected in [('blocked', 'blank prerender'), ('delay', 'delayed live CLS')]:
        fail_command(scenario, [sys.executable, '-m', 'tests.perf.browser', '--site', str(broken), '--flash', str(args.flash),
                               '--scenario', scenario, '--channel', args.channel, '--output', str(args.work / (scenario + '.json'))], expected)

    broken = clone('raw')
    alter(broken / 'assets/df/data.js', 'const data = path => ',
          "const data = path => path.startsWith('daily/') ? 'https://raw.githubusercontent.com/mash1384/signal-desk/flash/' + path : ")
    fail_command('raw', [sys.executable, '-m', 'tests.perf.visuals', '--site', str(broken), '--flash', str(args.flash),
                         '--pages', 'live/', '--channel', args.channel, '--forbid-raw', '--out', str(args.work / 'raw-capture')], 'direct raw request')
    broken = clone('polling')
    alter(broken / 'live/index.html', 'window.DF_LIVE = 1', 'window.DF_LIVE = 0')
    fail_command('polling', [sys.executable, '-m', 'tests.perf.browser', '--site', str(broken), '--flash', str(args.flash),
                             '--scenario', 'polling', '--channel', args.channel, '--output', str(args.work / 'polling.json')], 'Worker budget exceeded')
    broken = clone('hidden-polling')
    alter(broken / 'assets/df/lk.js', 'if (!document.hidden &&', 'if (true &&')
    fail_command('hidden-polling', [sys.executable, '-m', 'tests.perf.browser', '--site', str(broken), '--flash', str(args.flash),
                                    '--scenario', 'polling', '--channel', args.channel, '--output', str(args.work / 'hidden.json')], 'hidden tab polled')
    fail_command('legacy-hidden-polling', [sys.executable, '-m', 'pytest', 'tests/e2e/test_polling.py', '--site', str(broken),
                                          '--flash', str(args.flash), '-q'], 'hidden tab must not poll')
    broken = clone('eager-chart')
    alter(broken / 'calendar/index.html', '</head>', '<script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"></script></head>')
    fail_command('lazy-chart', [sys.executable, '-m', 'tests.perf.components', '--site', str(broken), '--flash', str(args.flash),
                                '--channel', args.channel, '--output', str(args.work / 'eager.json')], 'offscreen chart downloaded eagerly')
    broken = clone('theme-single-flight')
    alter(broken / 'assets/df/t2.js', 'function once(key, load) {', 'function once(key, load) { return load();')
    fail_command('theme-single-flight', [sys.executable, '-m', 'tests.perf.components', '--site', str(broken), '--flash', str(args.flash),
                                        '--channel', args.channel, '--output', str(args.work / 'theme.json')], 'repeated theme request')
    broken = clone('article-abi')
    alter(broken / 'assets/article-v1.js', 'DFI.init({', 'void({')
    fail_command('article-abi', [sys.executable, '-m', 'tests.perf.components', '--site', str(broken), '--flash', str(args.flash),
                                 '--old-site', str(args.site), '--channel', args.channel, '--output', str(args.work / 'abi.json')], 'language switch failed for old HTML')

    source = args.work / 'bad-source'
    root = Path(__file__).resolve().parents[2]
    for name in ('web', 'pipeline', 'tests'):
        shutil.copytree(root / name, source / name, ignore=shutil.ignore_patterns('__pycache__', 'vendor'))
    alter(source / 'pipeline/article_bundle.py', 'def article_html(html):', 'def article_html(html):\n    return html  # deliberately restore global-version churn')
    fail_command('incremental', [sys.executable, '-m', 'tests.perf.incremental', '--source', str(source),
                                 '--published', str(args.published), '--flash', str(args.flash), '--work', str(args.work / 'churn')], '"articles_changed": 6000')
    alter(source / 'web/assets/df/candles.js', 'Math.min(1000, Math.max(1, Math.ceil((now - earliest) / step) + 1))', '1')
    fail_command('candle-range', ['node', '--test', str(source / 'tests/perf/candles.test.mjs')], 'every previously visible recent candle')
    alter(source / 'tests/e2e/network.py', '((int(q["startTime"][0]) + step * 1000 - 1) // (step * 1000)) * step', 'int(q["startTime"][0]) // 1000')
    fail_command('fixture-utc', [sys.executable, '-m', 'unittest', 'tests.perf.test_metrics.Metrics.test_detail_fixture_uses_real_utc_opens_and_no_future_candles'], '1020000', cwd=source)
    print(json.dumps({'killed': len(results), 'total': len(results), 'ok': True}))


if __name__ == '__main__':
    main()
