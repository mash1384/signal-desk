"""다른 연도·윤년 입력, 글꼴 지연, 실제 크기 변경으로 날짜 축을 교차 검수한다."""
import time

import pytest


CHECK = """() => [...document.querySelectorAll('.axis')].map(ax=>{
 const box=ax.getBoundingClientRect(), all=[...ax.children];
 const visible=all.filter(s=>getComputedStyle(s).visibility!=='hidden');
 const rects=visible.map(s=>{const r=document.createRange();r.selectNodeContents(s);return r.getBoundingClientRect()});
 return {overlaps:rects.slice(1).filter((r,i)=>rects[i].right>r.left+0.5).length,
 outside:rects.filter(r=>r.left<box.left-1||r.right>box.right+1).length,
 hiddenMonths:all.filter(s=>s.dataset.m&&getComputedStyle(s).visibility==='hidden').length,
 shown:visible.length,total:all.length};
})"""


@pytest.mark.parametrize("lang", ["en", "ko"])
@pytest.mark.parametrize("start", [[2026, 11, 28], [2028, 1, 25]])
def test_axis_delayed_fonts_year_and_leap_boundary(lang, start, session_page, site_server):
    page, context, _ = session_page
    context.add_init_script("localStorage.setItem('df-lang','%s')" % lang)
    page.set_viewport_size({"width": 1440, "height": 1000})

    def delay(route):
        time.sleep(.12)
        route.fallback()
    context.route("**/*PretendardVariable*.woff2", delay)
    page.goto(site_server + "brief/", wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(200)
    assert all(not r["overlaps"] and not r["outside"] for r in page.evaluate(CHECK))
    page.evaluate("""async ([url,start])=>{
      const m=await import(url),d=new Date(...start),days=[];
      for(let i=0;i<9;i++){days.push(+d/1000);d.setDate(d.getDate()+1)}
      document.querySelector('.axis').outerHTML=m.axisHTML({days,X:t=>(t-days[0])/(9*86400)*100});
      if(m.fitAxis)m.fitAxis(document);
    }""", [site_server + "assets/df/brk.js", start])
    for width in (320, 1040, 390, 1440, 320):
        page.set_viewport_size({"width": width, "height": 1000})
        page.wait_for_timeout(250)
        rows = page.evaluate(CHECK)
        assert rows and all(not r["overlaps"] and not r["outside"] and not r["hiddenMonths"]
                            and r["shown"] * 2 >= r["total"] for r in rows), (width, rows)
