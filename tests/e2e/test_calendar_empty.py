"""일정 화면: 지표가 하나도 없는 econ.json(2026-10-22 FRED 점검 때 실제로 나온 파일)에서도 깨지지 않고
'자료 없음' 안내와 다가오는 발표를 보여 준다. 그날 이 파일 때문에 화면이 깨져 배포 전 검사가 배포를 4시간 막았다."""
import json
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "econ-no-indicators-2026-10-22.json"


@pytest.mark.parametrize("lang", ["ko", "en"])
@pytest.mark.parametrize("schedule", ["kept", "empty"])
def test_calendar_with_no_indicators(lang, schedule, session_page, site_server):
    page, context, offline = session_page
    doc = json.loads(FIXTURE.read_text())
    assert doc["indicators"] == [] and doc["upcoming"]
    if schedule == "empty":                      # 일정까지 비면 '예정된 발표 없음' 안내(Codex 교차 검수 R3-1-F1)
        doc["upcoming"] = []
    shift = offline.now - doc["made"]            # 다가오는 발표가 '지금' 뒤에 오도록 시각만 옮긴다
    doc["made"] += shift
    doc["next"] += shift
    for u in doc["upcoming"]:
        u["ts"] += shift
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("**/daily/econ.json*", lambda route: route.fulfill(body=json.dumps(doc), content_type="application/json"))
    context.add_init_script("localStorage.setItem('df-lang', %s)" % json.dumps(lang))
    page.goto(site_server + "calendar/?i=" + "cpi", wait_until="networkidle")
    page.locator("#ind-empty").wait_for(state="visible")
    if schedule == "kept":
        assert page.locator(".schw li.dg").count() >= 1
    else:
        assert page.locator(".schw li.dg").count() == 0
        assert ("예정된 발표가 없어요" if lang == "ko" else "No scheduled releases") in page.locator(".schw ol.sch > li.mute").inner_text()
    assert ("지표 자료를 받지 못했어요" if lang == "ko" else "not available") in page.locator("#ind-empty").inner_text()
    assert not errors, errors
    page.unroute("**/daily/econ.json*")
