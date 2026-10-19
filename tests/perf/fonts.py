"""Reproducible font subsets and coverage checks against the rendered corpus.

The source mono font has no Hangul. Preserve its existing system fallback;
check every source-supported character, and record the fallback characters
explicitly instead of claiming that JetBrains Mono suddenly supports Hangul.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / 'tests/e2e/vendor'
DEST = ROOT / 'web/assets/fonts'
SOURCES = {'mono': 'eecd9be6bd30124bd5fc.woff2', 'logo': 'fde0c9f6284a58af95c2.woff2'}


def corpus(path):
    result = {'mono': set(), 'logo': set()}
    for row in json.loads(Path(path).read_text())['rows']:
        for item in row['corpus']['dom'] + row['corpus']['canvas']:
            kind = 'logo' if 'Michroma' in item['font'] else 'mono'
            result[kind].update(item['text'])
    return result


def build(path):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    chars = corpus(path)
    # Dynamic prices/tickers must also work when the fixture happens not to
    # contain a digit or letter. These are a bounded superset of the corpus.
    chars['mono'].update(chr(i) for i in range(32, 127))
    chars['mono'].update('%$+−·↗→↑↓▲▼■–—…')
    manifest, css = {}, []
    vendor = json.loads((VENDOR / 'manifest.json').read_text())
    DEST.mkdir(exist_ok=True)
    for kind, name in SOURCES.items():
        source = VENDOR / name
        font = TTFont(source)
        cmap = font.getBestCmap()
        supported = {ord(c) for c in chars[kind] if ord(c) in cmap}
        fallback = sorted(c for c in chars[kind] if ord(c) not in cmap and not c.isspace())
        options = subset.Options()
        options.recalc_timestamp = False
        sub = subset.Subsetter(options=options)
        sub.populate(unicodes=supported)
        sub.subset(font)
        filename = 'jetbrains-mono.woff2' if kind == 'mono' else 'michroma-logo.woff2'
        font.save(DEST / filename)
        data = (DEST / filename).read_bytes()
        family = 'JetBrains Mono' if kind == 'mono' else 'Michroma'
        weight = '400 500' if kind == 'mono' else '400'
        css.append('@font-face{font-family:"%s";font-style:normal;font-weight:%s;font-display:swap;src:url("%s") format("woff2");unicode-range:%s}' %
                   (family, weight, filename, ','.join('U+%X' % cp for cp in sorted(supported))))
        manifest[kind] = {'file': filename, 'source': next(u for u, v in vendor.items() if v['file'] == name),
                          'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                          'version': font['name'].getDebugName(5), 'sha256': hashlib.sha256(data).hexdigest(),
                          'bytes': len(data), 'source_bytes': source.stat().st_size,
                          'codepoints': sorted(supported), 'unchanged_system_fallback': fallback}
    (DEST / 'subsets.css').write_text('\n'.join(css) + '\n')
    # Inter stays external until its own reversible optimization commit.
    original = (VENDOR / '92d5ce85eb724531ddce.css').read_text()
    blocks = re.findall(r'@font-face\s*\{[^}]+\}', original)
    (DEST / 'inter.css').write_text('\n'.join(b for b in blocks if "font-family: 'Inter'" in b) + '\n')
    (DEST / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


def check(path, dest=DEST):
    from fontTools.ttLib import TTFont
    manifest = json.loads((dest / 'manifest.json').read_text())
    chars, failures, fallbacks, hashes = corpus(path), {}, {}, []
    for kind, row in manifest.items():
        present = TTFont(dest / row['file']).getBestCmap()
        if hashlib.sha256((dest / row['file']).read_bytes()).hexdigest() != row['sha256']:
            hashes.append(row['file'])
        original = TTFont(VENDOR / SOURCES[kind]).getBestCmap()
        # Also reject new fallback symbols not in the reviewed corpus. A
        # missing digit, ticker letter, arrow or a new fallback fails closed.
        allowed_fallback = set(row['unchanged_system_fallback'])
        missing = sorted(c for c in chars[kind] if not c.isspace() and ord(c) not in present and
                         (ord(c) in original or c not in allowed_fallback))
        failures[kind] = sorted(set(missing) | {chr(cp) for cp in row['codepoints'] if cp not in present})
        fallbacks[kind] = sorted(c for c in chars[kind] if not c.isspace() and ord(c) not in original)
    return {'missing': failures, 'preserved_fallback': fallbacks, 'hash_mismatch': hashes, 'ok': not hashes and not any(failures.values())}


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('--build', action='store_true')
    p.add_argument('--fonts', type=Path, default=DEST)
    a = p.parse_args()
    if a.build:
        print(json.dumps(build(a.capture), ensure_ascii=False))
    else:
        result = check(a.capture, a.fonts)
        print(json.dumps(result, ensure_ascii=False))
        return int(not result['ok'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
