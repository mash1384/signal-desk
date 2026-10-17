import json, html
R = json.load(open('/tmp/cmp/out.json')); D = json.load(open('/tmp/cmp/themes.json')); SRC = json.load(open('/tmp/cmp/src.json'))
NAME = {'crypto': '크립토', 'nasdaq': '나스닥', 'econ': '경제', 'ai': 'AI'}
M = [('gemma4:26b', 'Gemma 4 26B', '지금 쓰는 모델 · 생각 단계 없음'), ('qwen3.8:27b', 'Qwen 3.8 27B', '생각(추론) 단계 켬')]
byid = {x['id']: x for t in D['themes'] for x in t.get('top', []) + t.get('latest', []) + t.get('more', [])}
e = html.escape
def col(key):
    r = R.get(key)
    if not r: return '<p class="mute">아직 결과 없음</p>'
    if r.get('error'): return f'<p class="bad">실패: {e(r["error"])}</p>'
    out = [f'<p class="meta">{r["sec"]}초' + (f' · 생각 {r["think_chars"]:,}자' if r.get('think_chars') else '') + f' · 문제 {sum(len(l["problems"]) for l in r["lines"])}건</p><ol>']
    for l in r['lines']:
        refs = ''.join(f'<li><b class="{ "up" if byid.get(i,{}).get("v")=="호재" else "down" if byid.get(i,{}).get("v")=="악재" else ""}">{e(byid.get(i,{}).get("v",""))}</b> {e(byid.get(i,{}).get("ko","(없는 id: "+i+")"))}</li>' for i in [str(x).lstrip('#') for x in l.get('refs') or []])
        pr = ''.join(f'<span class="pb">{e(p)}</span>' for p in l['problems'])
        out.append(f'<li><p class="ko">{e(l.get("ko",""))}</p><p class="en">{e(l.get("en",""))}</p>{pr}<details><summary>근거 소식 {len(l.get("refs") or [])}건</summary><ul>{refs}</ul></details></li>')
    return ''.join(out) + '</ol>'
body = []
for t in D['themes']:
    k = t['k']
    body.append(f'<section><h2>{NAME[k]} <span>소식 {t["n"]}건 · 호재 {t["u"]} · 악재 {t["d"]}</span></h2><div class="g">' + ''.join(f'<div class="c"><h3>{n}<small>{s}</small></h3>{col(m + "|" + k)}</div>' for m, n, s in M) + f'</div><details class="src"><summary>두 모델이 받은 입력 보기</summary><pre>{e(SRC[k])}</pre></details></section>')
page = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>요약 모델 비교 · Gemma vs Qwen</title>
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" rel="stylesheet"><style>
body{{margin:0;background:#f7f9fc;color:#0d253d;font:16px/1.6 "Pretendard Variable",system-ui,sans-serif;-webkit-font-smoothing:antialiased}}main{{max-width:1240px;margin:0 auto;padding:32px 20px 80px}}
h1{{font-size:28px;letter-spacing:-.02em}}.lead{{color:#5b6b82;max-width:60rem}}section{{margin-top:36px}}h2{{font-size:20px}}h2 span{{font-size:13px;font-weight:500;color:#8a96aa;margin-left:8px}}
.g{{display:grid;gap:16px}}@media(min-width:900px){{.g{{grid-template-columns:1fr 1fr}}}}.c{{background:#fff;border-radius:16px;padding:18px 20px;box-shadow:0 0 0 1px #e3e8ee}}
h3{{font-size:16px;margin:0}}h3 small{{display:block;font-size:12px;font-weight:500;color:#8a96aa}}.meta{{font-size:12.5px;color:#5b6b82;margin:6px 0 0}}ol{{padding-left:18px;margin:12px 0 0}}ol>li{{margin-bottom:14px}}
.ko{{margin:0;font-size:15.5px}}.en{{margin:2px 0 0;font-size:13px;color:#5b6b82}}.pb{{display:inline-block;margin:4px 6px 0 0;padding:1px 8px;border-radius:99px;background:#fdecea;color:#c0392b;font-size:12px;font-weight:600}}
details{{margin-top:6px;font-size:13px;color:#5b6b82}}summary{{cursor:pointer}}details ul{{padding-left:16px}}b.up{{color:#0e9f6e}}b.down{{color:#df4a3a}}.src pre{{white-space:pre-wrap;font-size:12px;background:#fff;padding:12px;border-radius:10px;box-shadow:0 0 0 1px #e3e8ee}}.bad{{color:#c0392b}}.mute{{color:#8a96aa}}
</style></head><body><main><h1>테마 요약: Gemma 4 vs Qwen 3.8</h1><p class="lead">같은 입력(오늘의 '변화 신호' + 주요 소식, 각 소식에 id)을 두 모델에 주고 "여러 소식을 연결한 오늘의 흐름 3문장"을 쓰게 했어요. 문장마다 근거 소식을 달게 했고, 프로그램이 자동으로 검사해 문제를 빨간 표로 붙였어요(자료에 없는 숫자 · 시세 원인 단정 · 매매 권유 · 근거 2개 미만 · 없는 id). 근거 소식을 펼쳐 문장이 정말 그 소식들에서 나왔는지 직접 볼 수 있어요.</p>{"".join(body)}</main></body></html>'''
import os; os.makedirs('/tmp/concepts/cmp', exist_ok=True); open('/tmp/concepts/cmp/index.html', 'w').write(page); print('written')
