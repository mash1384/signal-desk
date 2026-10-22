"""테마 화면: 테마 자료와 브리핑 중 어느 쪽이 먼저 와도 소식 줄은 같아야 한다(테마 자료 우선), 브리핑에만 있는 근거 소식은 열려야 한다.
2026-10-21 릴레이 R2-4: 두 요청 중 먼저 온 쪽의 소식 모양이 store 에 들어가 같은 소식이 실행마다 달라 보였다.

순서는 두 응답을 모두 붙잡아 두고, 하나를 보낸 뒤 그 자료가 페이지에서 처리된 것을 확인하고 다른 하나를 보내서 고정한다.
브리핑은 합성 자료(테마와 겹치는 소식 + 브리핑에만 있는 소식)라 고정 스냅샷에서도 늘 돈다."""
import json

BRIEF_ONLY = "f0f0f0f0f0f0"
# 페이지가 응답 JSON 읽기를 마친 순간을 남긴다(window.__relayRead.themes / .briefing) — 첫 응답이 처리된 것을 확인하고 둘째를 보낸다
READ_MARK = """(() => { window.__relayRead = {}; const f = window.fetch;
  window.fetch = async (...a) => { const r = await f(...a), u = String(r.url || a[0]), k = /daily\\/themes\\.json/.test(u) ? 'themes' : /daily\\/briefing\\.json/.test(u) ? 'briefing' : '';
    if (k) { const j = r.json.bind(r); r.json = async () => { const v = await j(); setTimeout(() => { window.__relayRead[k] = true; }); return v; }; } return r; }; })()"""
STORE = """async () => { const v = new URL(document.querySelector('link[rel="modulepreload"][href*="/t2.js"]').href).search;
  return import('../../assets/df/lk.js' + v).then((m) => m.store.byId); }"""


def synthetic_briefing(themes, now):
    crypto = next(t for t in themes["themes"] if t["k"] == "crypto")
    shared = crypto["latest"][0]["id"]          # 기본 정렬(최신순)의 첫 줄
    copy = lambda i: {"id": i, "t": now - 600, "ko": "브리핑 쪽 소식 모양", "en": "briefing copy", "v": "중립", "s": 1}
    read = {"state": "판세 문장", "refs": [shared], "drivers": [{"s": "판을 움직이는 힘", "refs": [BRIEF_ONLY]}], "shift": [], "links": [], "watch": []}
    return shared, {"v": 1, "made": now - 60, "next": now + 3600, "ko": {"headline": "제목"}, "en": {"headline": "Title"},
                    "stories": {shared: copy(shared), BRIEF_ONLY: copy(BRIEF_ONLY)}, "desks": {"crypto": {"ko": read, "en": read}}}


def load(page, site_server, themes_body, brief_body, first):
    held = {}
    page.route("**/daily/themes.json*", lambda r: held.__setitem__("themes", r))
    page.route("**/daily/briefing.json*", lambda r: held.__setitem__("briefing", r))
    page.goto(site_server + "themes/crypto/", wait_until="domcontentloaded")
    for _ in range(200):
        if len(held) == 2:
            break
        page.wait_for_timeout(25)
    assert len(held) == 2, held.keys()            # 두 요청이 모두 나갔다(병렬)
    body = {"themes": themes_body, "briefing": brief_body}
    second = "briefing" if first == "themes" else "themes"
    held[first].fulfill(body=body[first], content_type="application/json")
    # 먼저 보낸 쪽을 페이지가 읽어 처리할 때까지(이전 코드는 이 순간 store 에 그 모양을 넣었다)
    page.wait_for_function("window.__relayRead && window.__relayRead[%s]" % json.dumps(first))
    assert not page.evaluate("window.__relayRead[%s] || false" % json.dumps(second))
    held[second].fulfill(body=body[second], content_type="application/json")
    page.wait_for_selector("#stories .srow")
    page.wait_for_selector(".sbox .dk")
    # '이어지는 이야기' 표시는 thr.js 가 줄이 그려진 뒤 덧붙인다(처리한 줄에 data-thb). 다 붙은 뒤에 읽어야 두 순서를 같은 시점에서 비교한다
    page.wait_for_function("[...document.querySelectorAll('#stories .srow')].every(e => e.dataset.thb)")
    page.unroute("**/daily/themes.json*")
    page.unroute("**/daily/briefing.json*")
    return page.evaluate("[...document.querySelectorAll('#stories .srow')].map(e => [e.dataset.id, e.innerText])")


def test_rows_do_not_depend_on_arrival_order(session_page, site_server):
    page, context, offline = session_page
    page.set_viewport_size({"width": 1440, "height": 1000})
    context.add_init_script(READ_MARK)
    themes_body = (offline.site / "data/daily/themes.json").read_text()
    shared, brief = synthetic_briefing(json.loads(themes_body), int(offline.now))
    brief_body = json.dumps(brief, ensure_ascii=False)
    themes_first = load(page, site_server, themes_body, brief_body, "themes")
    briefing_first = load(page, site_server, themes_body, brief_body, "briefing")
    assert shared in [i for i, _ in themes_first]
    assert themes_first == briefing_first
    assert not any("브리핑 쪽 소식 모양" in text for _, text in briefing_first)     # 겹치는 소식은 테마 자료 모양
    page.locator('.sbox .dk [data-id="%s"]' % BRIEF_ONLY).first.click()            # 브리핑에만 있는 근거도 열린다
    assert page.locator("#sheet").get_attribute("aria-hidden") == "false"
