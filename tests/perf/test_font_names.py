"""배포 글꼴에서 예약 이름이 다시 생기면 실패한다(성능 도구 의존성 사용)."""
import os
import json
from pathlib import Path

import pytest

from tests.perf.font_names import reserved_names


@pytest.mark.parametrize("filename,family", [
    ("calendar-text.woff2", "DF Calendar Text"), ("pretendard-nav.woff2", "DF Nav"),
])
def test_subset_identity_and_attribution(filename, family):
    from fontTools.ttLib import TTFont
    root = Path(os.environ.get("FONT_TEST_DIR", "web/assets/fonts"))
    font = TTFont(root / filename)
    assert not reserved_names(font), reserved_names(font)
    assert font["name"].getDebugName(1) == family
    assert font["name"].getDebugName(4) == family
    assert "Kil Hyung-jin" in font["name"].getDebugName(0)
    assert font["fvar"].axes[0].axisTag == "wght"


def test_all_subsets_keep_distinct_identities(tmp_path, monkeypatch):
    from fontTools.ttLib import TTFont
    from tests.perf import fonts
    capture = tmp_path / 'capture.json'
    capture.write_text(json.dumps({'rows': [{'corpus': {'dom': [
        {'font': 'Michroma', 'text': 'ADEFLNO'}, {'font': 'JetBrains Mono', 'text': 'ABC012345'}], 'canvas': []}}]}))
    dest = tmp_path / 'fonts'
    monkeypatch.setattr(fonts, 'DEST', dest)
    result = fonts.build(capture)
    assert len({r['file'] for r in result.values()}) == 3
    assert TTFont(dest / result['logo']['file'])['name'].getDebugName(1) == 'Michroma'
    assert TTFont(dest / result['nav']['file'])['name'].getDebugName(1) == 'DF Nav'
    assert not reserved_names(TTFont(dest / result['nav']['file']))
