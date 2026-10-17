"""잘림 검사: 스크롤·잘라내기 상자 안에서 테두리·그림자·내용이 잘리는 곳, 말줄임 없이 잘린 글자, 화면 밖으로 나간 요소.
실행: python clip_qa.py <주소> [<주소> ...]   (너비 1440 · 1024 · 768 · 390 · 360 · 320)"""
import asyncio, json, sys
from playwright.async_api import async_playwright

AUDIT = r"""() => {
  const out = [], seen = new Set();
  // 보이는 요소만: 자기나 조상 중 하나라도 투명(opacity 0)·숨김이면 제외
  const vis = (e) => { const r = e.getBoundingClientRect(); if (!(r.width > 0 && r.height > 0)) return false; for (let p = e; p && p !== document.documentElement; p = p.parentElement) { const s = getComputedStyle(p); if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity < 0.05) return false; } return true; };
  const name = (e) => { let s = e.tagName.toLowerCase(); if (e.id) s += '#' + e.id; if (e.classList.length) s += '.' + [...e.classList].slice(0, 3).join('.'); const p = e.parentElement; return (p && p !== document.body ? (p.classList[0] ? '.' + p.classList[0] + ' > ' : p.tagName.toLowerCase() + ' > ') : '') + s; };
  // 그림자(테두리 링 포함)가 바깥으로 나가는 폭
  const shadowExt = (e) => { const bs = getComputedStyle(e).boxShadow; if (!bs || bs === 'none') return 0; let m = 0; bs.split(/,(?![^(]*\))/).forEach((p) => { if (/inset/.test(p)) return; const n = (p.replace(/rgba?\([^)]*\)|oklch\([^)]*\)|#[0-9a-f]+/gi, '').match(/-?[\d.]+px/g) || []).map(parseFloat); if (n.length >= 3) { const [x, y, b, sp = 0] = n; m = Math.max(m, sp + b * 0.3 - Math.min(Math.abs(x), Math.abs(y))); } }); return Math.max(0, m); };
  const clips = [...document.querySelectorAll('body *')].filter((e) => { const s = getComputedStyle(e); return vis(e) && (/(auto|scroll|hidden|clip)/.test(s.overflowX) || /(auto|scroll|hidden|clip)/.test(s.overflowY)) && !['CANVAS', 'svg', 'IMG', 'VIDEO'].includes(e.tagName) && !e.closest('.sheet:not(.on), [aria-hidden=true], dialog:not([open])'); });
  for (const c of clips) {
    if (c.closest('.tv-lightweight-charts')) continue;
    const cs = getComputedStyle(c), cr = c.getBoundingClientRect();
    // 처음 열었을 때 이미 옆으로 밀려 있는 줄(맞춤 스크롤 등): 앞쪽이 잘려 보인다
    if (/(auto|scroll)/.test(cs.overflowX) && c.scrollLeft > 0.5) { const key = 'start|' + name(c); if (!seen.has(key)) { seen.add(key); out.push({ kind: 'starts scrolled', box: name(c), how: 'scrollLeft ' + c.scrollLeft.toFixed(1) }); } }
    const L = cr.left + c.clientLeft, T = cr.top + c.clientTop, R = L + c.clientWidth, B = T + c.clientHeight;
    const scrollX = /(auto|scroll)/.test(cs.overflowX), scrollY = /(auto|scroll)/.test(cs.overflowY);
    for (const k of c.querySelectorAll('*')) {
      if (!vis(k) || k.closest('canvas, svg') || ['CANVAS'].includes(k.tagName)) continue;
      let inner = k.parentElement, nested = false; while (inner && inner !== c) { const s = getComputedStyle(inner); if (/(auto|scroll|hidden|clip)/.test(s.overflowX + s.overflowY)) { nested = true; break; } inner = inner.parentElement; } if (nested) continue;
      const r = k.getBoundingClientRect(), ext = shadowExt(k), tol = 0.5;
      const problems = [];
      // 시작 쪽(왼쪽·위)은 스크롤해도 볼 수 없으니 언제나 문제. 끝 쪽은 스크롤 상자면 정상(넘겨서 봄)
      if (r.left - ext < L - tol && r.right > L && (c.scrollLeft < 0.5 || k === c.firstElementChild || k.parentElement === c.firstElementChild)) problems.push('left ' + (L - (r.left - ext)).toFixed(1));
      if (c.scrollTop === 0 && r.top - ext < T - tol && !scrollY) problems.push('top ' + (T - (r.top - ext)).toFixed(1));
      if (!scrollX && r.right + ext > R + tol && r.left < R) problems.push('right ' + (r.right + ext - R).toFixed(1));
      if (!scrollY && r.bottom + ext > B + tol && r.top < B && cs.overflowY !== 'visible') problems.push('bottom ' + (r.bottom + ext - B).toFixed(1));
      if (problems.length) { const key = name(c) + '|' + name(k) + problems.map((p) => p.split(' ')[0]).join(); if (!seen.has(key)) { seen.add(key); out.push({ kind: 'clipped', box: name(c), el: name(k), how: problems.join(', '), txt: (k.textContent || '').trim().slice(0, 30) }); } }
    }
  }
  // 말줄임 없이 잘린 글자(스크롤 상자는 제외)
  for (const e of document.querySelectorAll('body *')) {
    if (!vis(e) || e.children.length > 3 || e.closest('.sheet:not(.on), [aria-hidden=true]')) continue;
    const s = getComputedStyle(e);
    if (!/(hidden|clip)/.test(s.overflowX) || /(auto|scroll)/.test(s.overflowX)) continue;
    if (e.scrollWidth > e.clientWidth + 1 && s.textOverflow !== 'ellipsis' && (e.textContent || '').trim()) { const key = 'trunc|' + name(e); if (!seen.has(key)) { seen.add(key); out.push({ kind: 'text cut', el: name(e), how: `${e.scrollWidth}>${e.clientWidth}`, txt: e.textContent.trim().slice(0, 40) }); } }
  }
  // 화면 밖(가로 스크롤 상자 안은 제외)
  for (const e of document.querySelectorAll('body *')) {
    if (!vis(e) || e.closest('.sheet:not(.on), [aria-hidden=true]')) continue;
    let p = e.parentElement, inScroll = false; while (p) { const s = getComputedStyle(p); if (/(auto|scroll|hidden|clip)/.test(s.overflowX) && p !== document.documentElement && p !== document.body) { inScroll = true; break; } p = p.parentElement; } if (inScroll) continue;
    const r = e.getBoundingClientRect(); if (r.right > innerWidth + 1 || r.left < -1) { const key = 'off|' + name(e); if (!seen.has(key)) { seen.add(key); out.push({ kind: 'off-screen', el: name(e), how: `${r.left.toFixed(0)}..${r.right.toFixed(0)} / ${innerWidth}` }); } }
  }
  return out;
}"""

async def main():
    urls, total = sys.argv[1:], 0
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome")
        for w in (1440, 1024, 768, 390, 360, 320):
            mob = w < 900
            ctx = await b.new_context(viewport={'width': w, 'height': 900 if not mob else 800}, device_scale_factor=2 if mob else 1, is_mobile=mob, has_touch=mob, locale='ko-KR')
            await ctx.add_init_script("localStorage.setItem('df-lang','ko'); localStorage.setItem('df-my', JSON.stringify(['BTC','NVDA','NQ=F','GC=F']));")
            for u in urls:
                pg = await ctx.new_page()
                await pg.goto(u, wait_until='networkidle'); await pg.wait_for_timeout(3500)
                # 맨 아래까지 한 번 스크롤(늦게 그려지는 것까지), 그리고 맨 위로
                await pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); await pg.wait_for_timeout(800); await pg.evaluate("window.scrollTo(0, 0)"); await pg.wait_for_timeout(500)
                res = await pg.evaluate(AUDIT)
                # 스크롤 위치마다(스크롤 장면 · 늦게 나타나는 요소)
                H = await pg.evaluate("document.documentElement.scrollHeight - innerHeight")
                for f in (0.2, 0.4, 0.6, 0.8, 1.0):
                    await pg.evaluate(f"window.scrollTo(0, {int(H * f)})"); await pg.wait_for_timeout(700)
                    res += [dict(r, at=f) for r in await pg.evaluate(AUDIT)]
                await pg.evaluate("window.scrollTo(0, 0)"); await pg.wait_for_timeout(400)
                for lang in ('en',):
                    await pg.evaluate(f"document.querySelector('.lang [data-lang={lang}]')?.click()"); await pg.wait_for_timeout(700)
                    res += [dict(r, lang='en') for r in await pg.evaluate(AUDIT)]
                total += len(res)
                short = u.split('signal-desk')[-1] if 'signal-desk' in u else u.split('8001')[-1]
                for r in res: print(w, short, json.dumps(r, ensure_ascii=False), flush=True)
                await pg.close()
            await ctx.close()
        await b.close()
    print('FOUND', total)
    sys.exit(1 if total else 0)
asyncio.run(main())
