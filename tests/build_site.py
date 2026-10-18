"""Offline replacement for seed/dfbuild.py; all input/output paths are explicit.
python -m tests.build_site --published .qa/snapshot/gh-pages --flash .qa/snapshot/flash --out .qa/build/signal-desk
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import time


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--published", type=Path, required=True)
    p.add_argument("--flash", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError("build output must be a new directory")
    for required in (args.published / "data/articles.json", args.published / "data/market.json", args.flash / "flash.json"):
        if not required.is_file():
            raise FileNotFoundError(str(required))
    os.environ["SIGNAL_FLASH_DIR"] = str(args.flash.resolve())
    from tests.support import safety
    safety()
    from pipeline import build, config
    start = time.monotonic()
    args.out.mkdir(parents=True)
    for name in ("data", "og"):
        shutil.copytree(args.published / name, args.out / name)
    articles = json.loads((args.out / "data/articles.json").read_text())
    market = json.loads((args.out / "data/market.json").read_text())
    now = json.loads((args.out / "data/feed.json").read_text())["at"]
    health = {s["id"]: {"ok": True} for s in config.SOURCES}
    build.OG_DEFAULT = True
    build.build_site(str(args.out), articles, market, {}, {}, health, now)
    print(json.dumps({"articles": len(articles), "seconds": round(time.monotonic() - start, 3), "now": now, "output": str(args.out)}))


if __name__ == "__main__":
    main()
