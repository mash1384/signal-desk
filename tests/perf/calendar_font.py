"""일정 본문·숫자 강조용 Pretendard 조각을 고정 원본에서 재현한다.

python -m tests.perf.calendar_font --out .qa/calendar-font
숫자와 단위는 ek.js의 numHi 범위. 가변 굵기와 tnum을 포함한 기능을 보존한다.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path

from tests.perf.font_names import rename_pretendard, reserved_names

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/e2e/vendor/3cf5ef80271b7cb1d760.woff2"
SOURCE_SHA = "9599f12fd42fc0bce1cd50b47a0c022e108d7aa64dd0d1bb0ed44f3282d900b4"
# 원래 동적 CSS에 없는 U+2212는 기존 시스템 대체 글꼴을 유지한다(최종 모양 보존).
TEXT = "".join(map(chr, range(32, 127))) + "\u00a0°·×–—‘’“”…천 명"
FAMILY = "DF Calendar Text"


def build(out):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    font = TTFont(SOURCE, recalcTimestamp=False)
    codepoints = sorted(set(map(ord, TEXT)))
    assert all(cp in font.getBestCmap() for cp in codepoints)
    opts = subset.Options()
    opts.recalc_timestamp = False
    opts.layout_features = list(dict.fromkeys(opts.layout_features + ["tnum"]))
    sub = subset.Subsetter(options=opts)
    sub.populate(unicodes=codepoints)
    sub.subset(font)
    rename_pretendard(font, FAMILY)
    assert not reserved_names(font)
    font.flavor = "woff2"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "calendar-text.woff2"
    font.save(path)
    data = path.read_bytes()
    css = '@font-face{font-family:"%s";font-style:normal;font-weight:100 900;font-display:swap;src:url("data:font/woff2;base64,%s") format("woff2");unicode-range:%s}\n' % (
        FAMILY, base64.b64encode(data).decode(), ",".join("U+%X" % cp for cp in codepoints))
    (out / "calendar-text.css").write_text(css)
    meta = {"family": FAMILY, "source": str(SOURCE.relative_to(ROOT)), "source_sha256": SOURCE_SHA,
            "version": font["name"].getDebugName(5), "bytes": len(data), "codepoints": codepoints,
            "sha256": hashlib.sha256(data).hexdigest(), "css_sha256": hashlib.sha256(css.encode()).hexdigest(),
            "features": sorted({r.FeatureTag for r in font["GSUB"].table.FeatureList.FeatureRecord}),
            "axes": [{"tag": a.axisTag, "min": a.minValue, "default": a.defaultValue, "max": a.maxValue} for a in font["fvar"].axes]}
    assert "tnum" in meta["features"]
    (out / "calendar-text.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    return meta


if __name__ == "__main__":
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--out", type=Path, required=True)
    print(json.dumps(build(p.parse_args().out), ensure_ascii=False))
