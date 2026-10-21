"""Reproducible font subsets and coverage checks against the rendered corpus.

The source mono font has no Hangul. Preserve its existing system fallback;
check every source-supported character, and record the fallback characters
explicitly instead of claiming that JetBrains Mono suddenly supports Hangul.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / 'tests/e2e/vendor'
DEST = ROOT / 'web/assets/fonts'
SOURCES = {'mono': 'eecd9be6bd30124bd5fc.woff2', 'logo': 'fde0c9f6284a58af95c2.woff2', 'nav': '3cf5ef80271b7cb1d760.woff2'}
# 메뉴 · 아래 탭의 한국어 이름(라이브 · 내 자산 · 테마 · 브리핑 · 일정). 이 글자만 담은 작은 Pretendard 를 사이트에 두어,
# 메뉴 글자 때문에 Pretendard 조각 파일(24KB 안팎)을 따로 받지 않게 한다 — '브리핑'의 '핑'이 휴대폰 첫 화면을 0.2~0.3초 늦췄다(2026-10-21)
NAV_TEXT = '라이브내자산테마브리핑일정'


def corpus(path):
    result = {'mono': set(), 'logo': set(), 'nav': set(NAV_TEXT)}
    for row in json.loads(Path(path).read_text())['rows']:
        for item in row['corpus']['dom'] + row['corpus']['canvas']:
            kind = 'logo' if 'Michroma' in item['font'] else 'mono'
            result[kind].update(item['text'])   # 메뉴 글자는 고정 목록(NAV_TEXT)으로 확인
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


def build_nav():
    """메뉴 글자만 담은 Pretendard(가변 굵기 그대로). 다른 글꼴 파일은 건드리지 않는다."""
    from fontTools import subset
    from fontTools.ttLib import TTFont
    source = VENDOR / SOURCES['nav']
    font = TTFont(source)
    cmap = font.getBestCmap()
    codepoints = sorted({ord(c) for c in NAV_TEXT})
    assert all(cp in cmap for cp in codepoints), 'Pretendard lacks a menu glyph'
    options = subset.Options()
    options.recalc_timestamp = False
    options.flavor = 'woff2'
    sub = subset.Subsetter(options=options)
    sub.populate(unicodes=codepoints)
    sub.subset(font)
    filename = 'pretendard-nav.woff2'
    font.flavor = 'woff2'
    font.save(DEST / filename)
    data = (DEST / filename).read_bytes()
    # 3KB 남짓이라 CSS 안에 바로 넣는다(요청 하나를 더 만들면 느린 휴대폰 망에서 그만큼 늦다)
    face = '@font-face{font-family:"DF Nav";font-style:normal;font-weight:100 900;font-display:swap;src:url("data:font/woff2;base64,%s") format("woff2");unicode-range:%s}' % (
        base64.b64encode(data).decode(), ','.join('U+%X' % cp for cp in codepoints))
    css = [line for line in (DEST / 'subsets.css').read_text().splitlines() if line and '"DF Nav"' not in line] + [face]
    (DEST / 'subsets.css').write_text('\n'.join(css) + '\n')
    manifest = json.loads((DEST / 'manifest.json').read_text())
    vendor = json.loads((VENDOR / 'manifest.json').read_text())
    manifest['nav'] = {'file': filename, 'source': next(u for u, v in vendor.items() if v['file'] == SOURCES['nav']),
                       'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'version': font['name'].getDebugName(5),
                       'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'source_bytes': source.stat().st_size,
                       'codepoints': codepoints, 'unchanged_system_fallback': []}
    (DEST / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest['nav']


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
    p.add_argument('--build-nav', action='store_true', help='메뉴 글꼴만 다시 만든다')
    p.add_argument('--fonts', type=Path, default=DEST)
    a = p.parse_args()
    if a.build_nav:
        print(json.dumps(build_nav(), ensure_ascii=False))
    elif a.build:
        print(json.dumps(build(a.capture), ensure_ascii=False))
    else:
        result = check(a.capture, a.fonts)
        print(json.dumps(result, ensure_ascii=False))
        return int(not result['ok'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
