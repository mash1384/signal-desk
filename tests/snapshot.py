"""Read public git refs into a NEW directory; no checkout, push or private state.
python -m tests.snapshot --out .qa/snapshot
Refresh explicitly first: git fetch --no-tags origin gh-pages flash
"""
import argparse
import io
import json
from pathlib import Path
import subprocess
import tarfile


def export(ref, paths, out):
    data = subprocess.check_output(["git", "archive", "--format=tar", ref] + paths)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for item in archive.getmembers():
            target = out / item.name
            if not target.resolve().is_relative_to(out.resolve()):
                raise ValueError("unsafe archive path")
            if item.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif item.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(item).read())
            else:
                raise ValueError("non-regular public artifact")


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    manifest = {}
    for branch, paths in (("gh-pages", ["data", "og"]), ("flash", ["daily", "flash.json"])):
        sha = subprocess.check_output(["git", "rev-parse", "origin/" + branch], text=True).strip()
        manifest[branch] = sha
        export(sha, paths, args.out / branch)
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
