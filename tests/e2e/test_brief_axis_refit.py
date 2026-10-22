"""날짜 축을 넓게 연 뒤 좁히면 다시 맞춘다(ResizeObserver 경로)는 것과, 오늘(마지막) 이름표가 늘 보인다는 것.

PC(1440)는 두 단이라 축이 오히려 짧다 — 축이 가장 넓은 한 단 1024px에서 열고 320px로 줄여야
'다시 맞추기'를 빼도 통과하던 빈틈(022 교차 검증의 일부러 고장 내기 M1 · M3)이 잡힌다.
"""
import pytest

CHECK = """() => [...document.querySelectorAll('.axis')].map((ax) => {
  const box = ax.getBoundingClientRect(), all = [...ax.children];
  const vis = all.filter((s) => getComputedStyle(s).visibility !== 'hidden');
  const rs = vis.map((s) => { const r = document.createRange(); r.selectNodeContents(s); return r.getBoundingClientRect(); });
  return {width: box.width, overlaps: rs.slice(1).filter((r, i) => rs[i].right > r.left + 0.5).length,
          outside: rs.filter((r) => r.left < box.left - 1 || r.right > box.right + 1).length,
          todayShown: !!all.length && getComputedStyle(all[all.length - 1]).visibility !== 'hidden', total: all.length};
})"""


@pytest.mark.parametrize("lang", ["en", "ko"])
def test_axis_refits_from_wide_to_narrow_and_keeps_today(lang, session_page, site_server):
    page, context, _ = session_page
    context.add_init_script("localStorage.setItem('df-lang','%s')" % lang)
    page.set_viewport_size({"width": 1024, "height": 1000})
    page.goto(site_server + "brief/", wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(200)
    wide = page.evaluate(CHECK)
    assert wide and all(r["total"] and r["todayShown"] for r in wide), wide
    for width in (320, 360, 1024, 320):
        page.set_viewport_size({"width": width, "height": 1000})
        page.wait_for_timeout(300)          # ResizeObserver → 80ms 뒤 다시 맞추기
        rows = page.evaluate(CHECK)
        assert rows and all(not r["overlaps"] and not r["outside"] and r["todayShown"] for r in rows), (width, rows)
    assert rows[0]["width"] < wide[0]["width"] * 0.7, (wide, rows)   # 실제로 축이 좁아졌는지(시험 전제: 1024 → 424px, 320 → 236px)
