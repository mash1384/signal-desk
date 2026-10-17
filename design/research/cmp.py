# 같은 입력으로 두 모델의 '변화 연결 요약'을 비교한다. 결과: /tmp/cmp/out.json
import json, os, re, sys, time, urllib.request
sys.path.insert(0, os.path.expanduser('~/.signal'))
import theme_brief as B
DOC = json.load(open('/tmp/cmp/themes.json'))   # 두 모델이 같은 입력을 받게 고정
MODELS = sys.argv[1:] or ['gemma4:26b', 'qwen3.8:27b']
SYS = """너는 전 세계 시장 소식을 다루는 편집자다. 아래는 '{name}' 테마의 오늘(지난 24시간) 자료다.
[변화 신호]는 프로그램이 평소(최근 며칠)와 비교해 센 숫자이고, [주요 소식]은 판정한 속보다(각 줄 앞의 #기호가 소식 id).
할 일: 신호와 소식을 서로 연결해 '오늘의 흐름'을 문장 3개로 쓴다. 기사 하나를 옮겨 쓰지 말고, 여러 소식이 함께 가리키는 흐름(같은 방향의 움직임, 서로 다른 신호의 연결, 엇갈리는 신호)을 쓴다.
- 문장마다 근거 소식 id 를 2개 이상 refs 에 넣는다(자료에 있는 id 만).
- 숫자는 자료에 있는 것만, 적힌 모양 그대로. 새 숫자·이름을 만들지 않는다.
- 시세 움직임의 원인을 단정하지 않는다('~때문에 올랐다', '~로 하락' 금지). 매매 권유 금지.
- ko: 한국어 문장(40~90자, '~했다/~이다'), en: 같은 뜻의 영어 한 문장.
형식: {{"lines": [{{"ko": "", "en": "", "refs": ["id", "id"]}}]}}"""

def source(t):
    L = [f"[{B.NAME[t['k']]} · 지난 24시간 소식 {t['n']}건 · 호재 {t['u']} · 악재 {t['d']}]", "[변화 신호]"]
    L += [f"- {c['ko']} (관련 소식: {', '.join('#' + i for i in c['ids'][:6])})" for c in t.get('changes', [])]
    L.append("[주요 소식]")
    seen = set()
    for x in (t.get('top', [])[:24] + t.get('more', [])):
        if x['id'] in seen: continue
        seen.add(x['id']); L.append(f"#{x['id']} ({x['v']}, 세기 {x.get('s', 1)}, {x.get('n', 1)}곳 보도) {x['ko']}")
    return "\n".join(L), seen

def ask(model, system, user):
    think = model.startswith('qwen')
    body = {"model": model, "stream": False, "think": think, "keep_alive": "5m", "options": {"temperature": 0.3, "num_ctx": 12288, "num_predict": 6000 if think else 1600},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    t0 = time.time()
    with urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=1800) as r:
        out = json.loads(r.read())
    txt = out["message"]["content"]
    return txt, time.time() - t0, len(out["message"].get("thinking") or "")

def check(line, src, ids):
    probs = []
    extra = B.nums(line.get("ko", "")) - B.nums(src)
    if extra: probs.append("자료에 없는 숫자 " + ", ".join(sorted(extra)))
    if B.CAUSAL.search(line.get("ko", "")) or B.EN_CAUSAL.search(line.get("en", "")): probs.append("인과 단정")
    if B.ADVICE.search(line.get("ko", "") + " " + line.get("en", "")): probs.append("매매 권유")
    refs = [str(r).lstrip('#') for r in line.get("refs") or []]
    bad = [r for r in refs if r not in ids]
    if len([r for r in refs if r in ids]) < 2: probs.append("근거 소식 2개 미만")
    if bad: probs.append("없는 id " + ", ".join(bad[:3]))
    return probs

res = json.load(open('/tmp/cmp/out.json')) if os.path.exists('/tmp/cmp/out.json') else {}
for model in MODELS:
    for t in DOC['themes']:
        src, ids = source(t)
        key = f"{model}|{t['k']}"
        try:
            txt, sec, thk = ask(model, SYS.format(name=B.NAME[t['k']]), src)
            o = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
            lines = [dict(l, problems=check(l, src, ids)) for l in (o.get("lines") or [])]
            res[key] = {"model": model, "theme": t['k'], "sec": round(sec, 1), "think_chars": thk, "lines": lines}
        except Exception as e:
            res[key] = {"model": model, "theme": t['k'], "error": f"{type(e).__name__}: {str(e)[:200]}"}
        print(key, res[key].get('sec'), [len(l['problems']) for l in res[key].get('lines', [])], res[key].get('error', ''), flush=True)
        json.dump(res, open('/tmp/cmp/out.json', 'w'), ensure_ascii=False, indent=1)
json.dump({t['k']: source(t)[0] for t in DOC['themes']}, open('/tmp/cmp/src.json', 'w'), ensure_ascii=False, indent=1)
