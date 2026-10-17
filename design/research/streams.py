import json, os, sys, time, urllib.request
sys.path.insert(0, os.path.expanduser('~/.signal'))
import theme_brief as B
D = json.load(open(os.path.expanduser('~/.signal/flash-branch/daily/themes.json')))
SYS = """너는 '{name}' 분야를 매일 따라가는 편집자다. 아래는 오늘(지난 24시간) 판정한 속보다(#기호 = 소식 id). 독자는 이 분야에 투자하는 사람이고 목록은 이미 따로 본다.
할 일: 오늘 소식들이 이루는 '줄기'를 2~3개 찾아 정리한다. 줄기 = 여러 소식이 같은 방향을 가리키는 흐름(예: 전통 금융의 진입, 규제 강화, 특정 기술 경쟁). 단발 소식 하나는 줄기가 아니다.
줄기마다:
- title: 무슨 흐름인지 한 줄(25자 이내, 명사형)
- what: 오늘 무엇이 새로 나왔는지(가장 중요한 사실 2~3개를 회사·기관 이름과 숫자로, 1~2문장)
- why: 투자자에게 왜 중요한지(1문장). 자료의 사실에서 바로 따라 나오는 것만. 가격 전망·매매 권유 금지.
- watch: 이 흐름에서 다음에 확인할 것(1문장, 자료에 나온 예정·진행 중인 일만. 없으면 빈 문자열)
- refs: 근거 소식 id 3개 이상
숫자는 자료에 있는 것만 그대로. '~때문에 올랐다' 같은 시세 인과 금지. 한국어 '~했다/~이다'.
형식: {{"streams": [{{"title": "", "what": "", "why": "", "watch": "", "refs": []}}], "solo": [{{"line": "", "ref": ""}}]}}
solo = 줄기에 안 들어가지만 놓치면 안 되는 단발 소식 최대 2개(한 줄 + id)."""
for k in ('crypto', 'econ'):
    t = [x for x in D['themes'] if x['k'] == k][0]; seen=set(); L=[]
    for x in t['top'] + t['latest'] + t.get('more', []):
        if x['id'] in seen or x.get('v') == '중립' and x.get('s', 1) < 2: continue
        seen.add(x['id']); L.append(f"#{x['id']} ({x['v']}, 세기 {x.get('s',1)}, {x.get('n',1)}곳 보도) {x['ko']}")
    src = "\n".join(L[:60])
    body = {"model": "gemma4:26b", "stream": False, "think": False, "keep_alive": "30m", "options": {"temperature": 0.3, "num_ctx": 12288, "num_predict": 2400},
            "messages": [{"role": "system", "content": SYS.format(name=B.NAME[k])}, {"role": "user", "content": src}]}
    t0 = time.time(); out = json.loads(urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=600).read())["message"]["content"]
    o = json.loads(out[out.index("{"): out.rindex("}") + 1])
    print(f"\n######## {B.NAME[k]} ({len(L)} stories in, {time.time()-t0:.0f}s)")
    for s in o.get('streams', []):
        bad = [r for r in s.get('refs', []) if r.lstrip('#') not in seen]; extra = B.nums(s.get('what','')+s.get('why','')+s.get('watch','')) - B.nums(src)
        print(f"\n■ {s['title']}  (근거 {len(s.get('refs',[]))}건{' · 없는id '+str(bad) if bad else ''}{' · 없는숫자 '+str(extra) if extra else ''})\n  무엇: {s['what']}\n  왜 중요: {s['why']}\n  다음: {s.get('watch','')}")
    for s in o.get('solo', []): print(f"  · 단발: {s.get('line')}")
