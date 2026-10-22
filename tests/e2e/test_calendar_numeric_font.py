"""일정의 영문 본문·강조 숫자는 외부 글꼴을 못 받아도 최종 폭을 유지한다."""
import base64
from pathlib import Path
import re

import pytest

SOURCE = Path(__file__).parent / "vendor/3cf5ef80271b7cb1d760.woff2"
ORIGINAL_CSS = Path(__file__).parent / "vendor/b73038d8c83e09519417.css"


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_calendar_numeric_width_without_remote_font(lang, session_page, site_server):
    page, context, _ = session_page
    context.add_init_script("localStorage.setItem('df-lang', '%s')" % lang)
    context.route("**/*PretendardVariable*.woff2", lambda route: route.abort())
    page.goto(site_server + "calendar/", wait_until="networkidle")
    # 운영 자료와 별개로 숫자 · 부호 · 단위와 다른 굵기를 함께 확인한다.
    page.evaluate("""() => {
      const host=document.createElement('div');host.className='it';host.id='numeric-probe';
      const p=document.createElement('p');
      for(const weight of [400,650,900])for(const value of ['0123456789','−12.75%','+1,234.5bp','0.25%p','123k','12천 명']){
        const b=document.createElement('b');b.className='nm';b.textContent=value;
        b.style.cssText=`font-weight:${weight};display:inline-block;white-space:nowrap;margin:0 4px 4px 0`;
        p.append(b);
      }
      const prose=document.createElement('span');
      prose.textContent='Inflation is 3.7% — payroll gains average 56k, while unemployment is 4.2%.';
      prose.style.cssText='display:inline-block;white-space:nowrap';p.append(prose);
      host.append(p);document.body.append(host);
    }""")
    page.evaluate("document.fonts.ready")
    measure = "()=>[...document.querySelectorAll('#numeric-probe p > *')].map(b=>({text:b.textContent,weight:getComputedStyle(b).fontWeight,width:b.getBoundingClientRect().width,height:b.getBoundingClientRect().height}))"
    before = page.evaluate(measure)
    # 원래 CSS의 문자 범위까지 적용한다. 원래도 시스템 글꼴로 그린 기호는 그대로 둔다.
    source = "data:font/woff2;base64," + base64.b64encode(SOURCE.read_bytes()).decode()
    ranges = ','.join(r.strip().rstrip(';') for r in re.findall(r'unicode-range:([^}]+)', ORIGINAL_CSS.read_text()))
    page.evaluate("""async ([url,range]) => {
      const f=new FontFace('Calendar Reference',`url("${url}")`,{weight:'100 900',unicodeRange:range});
      await f.load();document.fonts.add(f);
      document.querySelectorAll('#numeric-probe p > *').forEach(b=>b.style.fontFamily='"Calendar Reference",'+getComputedStyle(b).getPropertyValue('--sans'));
    }""", [source, ranges])
    after = page.evaluate(measure)
    assert len(before) == len(after) == 19
    differences = [{"before": a, "after": b} for a, b in zip(before, after)
                   if abs(a["width"] - b["width"]) > .02 or abs(a["height"] - b["height"]) > .02]
    assert not differences, differences
