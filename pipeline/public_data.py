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
    for name, text in STUBS.items():
        if not (dest / name).exists():
            dest.mkdir(parents=True, exist_ok=True)
            (dest / name).write_text(text)
    return copied
