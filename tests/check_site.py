"""python -m tests.check_site --site BUILD --flash FLASH [--output REPORT]."""
import argparse
import json
from pathlib import Path
import re
import sys
import time
from jsonschema import Draft202012Validator
from tests.policy.scan import scan


def validate(name, doc):
    path = Path(__file__).parent / "schema" / (name + ".schema.json")
    schema = json.loads(path.read_text())
    Draft202012Validator.check_schema(schema)
    return [{"schema": name, "path": "/" + "/".join(str(x) for x in e.absolute_path), "validator": e.validator, "message": "schema " + e.validator + " failed"} for e in Draft202012Validator(schema).iter_errors(doc)]


def check(site, flash):
    result = {"policy": {}, "schema": [], "files": []}
    for label, root in (("site", site), ("flash", flash)):
        result["policy"][label] = scan(root)
    paths = [("feed", site / "data/feed.json"), ("related", site / "data/related.json"), ("flash", flash / "flash.json")]
    paths += [(name, flash / "daily" / (name + ".json")) for name in ("econ", "threads", "themes")]
    dailies = sorted(p for p in (flash / "daily").glob("*.json") if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", p.name))
    if not dailies:
        raise FileNotFoundError("no dated daily JSON found")
    paths += [("daily", p) for p in dailies]
    for name, path in paths:
        errors = validate(name, json.loads(path.read_text()))
        result["files"].append({"schema": name, "file": str(path), "errors": len(errors)})
        result["schema"].extend(dict(e, file=str(path)) for e in errors)
    return result


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--site", type=Path, required=True)
    p.add_argument("--flash", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path(".qa/contracts.json"))
    # 15분 배포 전 검사용(운영자 결정 2026-10-20): 말투 규칙(ai-korean-style: '~쪽' · 세미콜론)은 경고만 — 문장 하나로 뉴스 배포가 멈추지 않게.
    # 비밀값 · 텔레그램 출처 · 발췌 길이 · 데이터 형식은 그대로 막는다. main 합치기 전 검사(qa-harness)는 이 옵션 없이 엄격.
    p.add_argument("--style-warn", action="store_true")
    args = p.parse_args()
    start = time.monotonic()
    result = check(args.site, args.flash)
    result["seconds"] = round(time.monotonic() - start, 3)
    soft = {"ai-korean-style"} if args.style_warn else set()
    result["warnings"] = [dict(e, scope=k) for k, r in result["policy"].items() for e in r["errors"] if e.get("rule") in soft]
    for r in result["policy"].values():
        r["errors"] = [e for e in r["errors"] if e.get("rule") not in soft]
    for w in result["warnings"]:
        print("WARNING style", w["scope"], w.get("file"), w.get("path"))
    n = sum(len(r["errors"]) for r in result["policy"].values()) + len(result["schema"])
    result["violations"] = n
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("policy files=%d schema files=%d violations=%d seconds=%.3f" % (sum(r["files"] for r in result["policy"].values()), len(result["files"]), n, result["seconds"]))
    print("report:", args.output)
    return int(n > 0)


if __name__ == "__main__":
    sys.exit(main())
