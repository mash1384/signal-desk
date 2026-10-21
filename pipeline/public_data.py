"""Publish only the already-public daily documents consumed by the browser."""
from pathlib import Path
import re
import shutil

NAMES = {'threads.json', 'thread_index.json', 'econ.json', 'themes.json', 'briefing.json'}


def copy_daily(flash, out):
    source = Path(flash) / 'daily'
    dest = Path(out) / 'data/daily'
    copied = []
    if not source.is_dir():
        return copied
    for path in sorted(source.glob('*.json')):
        if path.name in NAMES or re.fullmatch(r'\d{4}-\d{2}-\d{2}\.json', path.name):
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest / path.name)
            copied.append(path.name)
    return copied
