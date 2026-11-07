"""Publish only the already-public daily documents consumed by the browser."""
from pathlib import Path
import re
import shutil

NAMES = {'threads.json', 'thread_index.json', 'econ.json', 'themes.json', 'briefing.json'}
# 브라우저가 늘 찾는 파일 — Mac 이 아직 안 만들었으면 빈 판을 둬서 404 가 나지 않게(화면은 v 0 을 '없음'으로 본다)
STUBS = {'briefing.json': '{"v": 0}\n'}


def copy_daily(flash, out):
    source = Path(flash) / 'daily'
    dest = Path(out) / 'data/daily'
    copied = []
    for path in sorted(source.glob('*.json')) if source.is_dir() else []:
        if path.name in NAMES or re.fullmatch(r'\d{4}-\d{2}-\d{2}\.json', path.name):
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest / path.name)
            copied.append(path.name)
    if 'threads.json' in copied:
        split_threads(dest)
    for name, text in STUBS.items():
        if not (dest / name).exists():
            dest.mkdir(parents=True, exist_ok=True)
            (dest / name).write_text(text)
    return copied


def split_threads(dest):
    """브리핑이 처음 받는 이야기 자료를 가볍게(7회차): 소식 제목(ko · en)을 따로 둔다.
    첫 화면(히트맵 · 미리 그린 칸)에는 제목이 필요 없고, 이야기를 누르거나 언어를 바꿀 때 brk.js loadText 가 받는다.
    threads.json(원본)은 그대로 둔다 — 빌드 · 감시 · 예전 화면이 쓴다."""
    import json
    doc = json.loads((dest / 'threads.json').read_text())
    stories = doc.get('stories') or {}
    text = {i: [s.get('ko') or '', s.get('en') or ''] for i, s in stories.items()}
    core = dict(doc, stories={i: {k: v for k, v in s.items() if k not in ('ko', 'en')} for i, s in stories.items()})
    dump = lambda x: json.dumps(x, ensure_ascii=False, separators=(',', ':'))
    (dest / 'threads-core.json').write_text(dump(core))   # 예전 화면(캐시된 brk.js)용 — 전환 기간 뒤 지운다
    (dest / 'threads-pack.json').write_text(dump(pack_threads(core)))
    (dest / 'threads-text.json').write_text(dump({'made': doc.get('made'), 'text': text}))


def pack_threads(core):
    """브리핑이 처음 받는 자료를 더 가볍게(11-07: 소식이 1,588개로 늘어 PC 브리핑이 무게 기준 1,210,362바이트를 넘었다).
    소식마다 되풀이되던 이름표(t · v · coins …)를 cols 한 번으로 — stories = {cols: [...], rows: {id: [값…]}}, 없는 값은 null.
    줄기(threads)의 names(화면에서 안 씀)는 뺀다. brk.js unpack() 이 원래 모양으로 되돌린다."""
    stories = core.get('stories') or {}
    cols = sorted({k for s in stories.values() for k in s})
    threads = [{k: v for k, v in t.items() if k != 'names'} for t in core.get('threads') or []]
    return dict(core, threads=threads, stories={'cols': cols, 'rows': {i: [s.get(k) for k in cols] for i, s in stories.items()}})
