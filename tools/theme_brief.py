"""첫 페이지 '지구' 장면의 테마별 AI 요약: 크립토 · 나스닥(미국 증시) · 경제 · AI.

지난 24시간 실시간 속보(flash.json, 판정된 소식)를 네 테마로 나누고, 기사 제목(articles.json)을 참고 자료로 더해
로컬 Gemma가 테마마다 문장 6개(한국어·영어 짝)와 오늘의 한 줄을 쓴다.
하루 정리와 같은 규칙: 자료에 없는 숫자 금지 · '~때문에 올랐다' 같은 인과 금지 · 매매 권유 금지. 어긴 문장은 빼고, 모자라면 다시 쓰게 한다.
건수(n·호재·악재)는 프로그램이 판정된 속보만으로 센다.

결과: ~/.signal/flash-branch/daily/themes.json → tg_publish가 flash 브랜치로 올린다(사이트는 raw.githubusercontent로 읽는다).
설치: ~/.signal/tgvenv/bin/python tools/theme_brief.py --install   (launchd com.signal.themes, 3시간마다, 로그 ~/.signal/themes.log)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

HOME = os.path.expanduser("~/.signal")
BRANCH = os.path.join(HOME, "flash-branch")
OUT = os.path.join(BRANCH, "daily", "themes.json")
OLLAMA = os.environ.get("SIGNAL_OLLAMA", "http://localhost:11434")
MODEL = os.environ.get("SIGNAL_TG_MODEL", "gemma4:26b")
ARTICLES = "https://mash1384.github.io/signal-desk/data/articles.json"
LABEL = "com.signal.themes"
EVERY = 3 * 3600

NAME = {"crypto": "크립토", "nasdaq": "나스닥·미국 증시", "econ": "경제", "ai": "AI"}
CRYPTO_W = re.compile(r"비트코인|이더리움|코인|가상자산|암호화폐|스테이블코인|거래소|ETF|토큰|블록체인|디파이|채굴|온체인|NFT|웹3")
STOCK_W = re.compile(r"나스닥|S&P|다우|미국 증시|뉴욕 증시|미 증시|미국 주식|빅테크|엔비디아|애플|테슬라|마이크로소프트|메타|아마존|알파벳|구글|반도체|기술주|주가|증시")
STOCK_EN = re.compile(r"Nasdaq|S&P|Dow|Wall Street|stocks?\b|equities|Nvidia|Apple|Tesla|Microsoft|Amazon|Alphabet|Meta\b|chipmakers?", re.I)
AI_W = re.compile(r"(?<![A-Za-z])AI(?![A-Za-z])|인공지능|오픈AI|OpenAI|앤트로픽|Anthropic|엔비디아|챗GPT|ChatGPT|LLM|딥시크|제미나이|데이터센터|xAI")
ECON_W = re.compile(r"연준|Fed|FOMC|CPI|PPI|물가|인플레이션|금리|국채|고용|실업|GDP|PCE|소매판매|달러|환율|재무부|파월|관세|경기")

CAUSAL = re.compile(r"(때문에|탓에|덕분에|영향으로|여파로|에 힘입어|로 인해|으로 인해|에 따른|우려로|우려에|되며|하며|면서|전망에)[^.]{0,30}(올랐|내렸|상승|하락|급등|급락|반등|증발|매도세)")
EN_CAUSAL = re.compile(r"\b(because of|due to|thanks to|driven by|on the back of|amid|as|following|after)\b[^.]{0,40}\b(rose|fell|jumped|dropped|rallied|slid|surged|plunged|declined|sank|tumbled)"
                       r"|\b(rose|fell|jumped|dropped|rallied|slid|surged|plunged|declined|sank|tumbled)\b[^.]{0,30}\b(amid|as|due to|after|following)\b", re.I)
ADVICE = re.compile(r"매수하|매도하|사세요|파세요|추천|담아|비중을 늘|비중을 줄|진입하|손절|\bbuy\b|\bsell\b", re.I)
RULES = """반드시 지킬 것:
- 자료에 있는 사실과 숫자만 쓴다. 자료에 없는 숫자·이름을 만들지 않는다. 숫자는 자료에 적힌 모양 그대로 쓴다.
- 소식(무슨 일이 있었나)을 쓴다. 시세 움직임을 쓰더라도 소식과 한 문장에서 원인·결과로 묶지 않는다('~되며 하락했다', '~우려로 급락했다', '~에 따른', 'fell as/amid/due to ~' 모두 금지).
- 매매 권유 금지. 한국어 말투는 '~했다/~이다'."""


def log(*a):
    print(time.strftime("%m-%d %H:%M:%S"), *a, flush=True)


def get(url, timeout=60):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 delfona-themes"}), timeout=timeout))


def nums(s):
    return {n.replace(",", "").lstrip("+-") for n in re.findall(r"[+-]?\d[\d,]*(?:\.\d+)?", s)}


def ok_ko(v, src):
    return bool(v) and not (nums(v) - nums(src)) and not CAUSAL.search(v) and not ADVICE.search(v)


def ok_en(v):
    return bool(v) and not EN_CAUSAL.search(v) and not ADVICE.search(v)


def chat(system, user, n=2400):
    body = {"model": MODEL, "stream": False, "think": False, "keep_alive": "10m", "options": {"temperature": 0.3, "num_ctx": 8192, "num_predict": n},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        t = json.loads(r.read())["message"]["content"]
    return json.loads(t[t.index("{"): t.rindex("}") + 1])


def buckets(items, arts):
    T = {k: [] for k in NAME}
    A = {k: [] for k in NAME}
    for x in items:
        ko = x.get("ko") or ""
        if x.get("coins") or CRYPTO_W.search(ko):
            T["crypto"].append(x)
        if STOCK_W.search(ko):
            T["nasdaq"].append(x)
        if ECON_W.search(ko) or (x.get("kind") == "data" and not x.get("coins")):
            T["econ"].append(x)
        if "ai" in (x.get("sectors") or []) or AI_W.search(ko):
            T["ai"].append(x)
    for a in arts:
        t, to = a.get("title") or "", a.get("title_orig") or ""
        if STOCK_W.search(t) or STOCK_EN.search(to):
            A["nasdaq"].append(a)
        if a.get("category") == "ai":
            A["ai"].append(a)
        elif a.get("category") == "crypto":
            A["crypto"].append(a)
        elif a.get("category") == "macro":
            A["econ"].append(a)
    return T, A


def pick(arr, n):
    return sorted(arr, key=lambda x: -((x.get("s") or 1) * 3 + (x.get("n") or 1) * 2 + (x.get("v") != "중립")))[:n]


def theme_source(k, xs, arts):
    u = sum(x["v"] == "호재" for x in xs)
    d = sum(x["v"] == "악재" for x in xs)
    L = [f"[{NAME[k]} · 지난 24시간 판정한 속보 {len(xs)}건 · 호재 {u} · 악재 {d}]"]
    L += [f"  ({x['v']}) {x['ko']}" + (f" [{x['n']}곳 보도]" if (x.get("n") or 1) > 1 else "") for x in pick(xs, 24)]
    seen, extra = set(), []
    for a in sorted(arts, key=lambda a: -(a.get("importance") or 0)):
        t = (a.get("title") or "").strip()
        if t and t[:18] not in seen:
            seen.add(t[:18])
            extra.append(f"  (기사 · {a.get('source_name', '')}) {t}")
        if len(extra) >= 10:
            break
    if extra:
        L.append("[참고: 같은 시간 주요 매체 기사 제목]")
        L += extra
    return "\n".join(L), u, d


def write_theme(k, src):
    system = f"""너는 전 세계 시장 소식을 요약하는 편집자다. 아래는 '{NAME[k]}' 테마의 지난 24시간 자료다(판정한 실시간 속보 + 주요 매체 기사 제목). 이 테마를 독자가 한 번에 이해하도록 요약한다.
문장 6개를 쓴다: ① 가장 큰 소식 ② ③ ④ 그다음 중요한 서로 다른 소식들(각각 구체적으로, 회사·기관 이름과 숫자 포함) ⑤ 판정한 속보 중 호재·악재 어느 쪽이 많았는지(자료의 건수 사용) ⑥ 이 테마에서 눈여겨볼 점.
한국어 문장은 각각 35~70자. 영어는 같은 뜻으로 한 문장씩 짝을 맞춘다.
{RULES}
형식: {{"ko": ["", "", "", "", "", ""], "en": ["", "", "", "", "", ""]}}"""
    keep, dropped, note = [], [], ""
    for attempt in range(4):
        try:
            o = chat(system, src + note)
        except Exception as e:
            log(k, "AI 실패", type(e).__name__, str(e)[:120])
            continue
        pairs = list(zip(o.get("ko") or [], o.get("en") or []))
        good = [(a, b) for a, b in pairs if ok_ko(a, src) and ok_en(b)]
        bad = [a for a, b in pairs if (a, b) not in good]
        if len(good) > len(keep):
            keep, dropped = good, bad
        if len(good) >= 5:
            break
        note = "\n\n앞선 답에서 다음 문장은 규칙 위반이라 뺐다: " + " / ".join(bad[:4]) + "\n규칙을 지켜 다시 6문장을 써라."
    return keep, dropped


def run():
    t0 = time.time()
    flash = json.load(open(os.path.join(BRANCH, "flash.json")))
    now = time.time()
    items = [x for x in flash.get("items", []) if x.get("t", 0) >= now - 86400 and x.get("ko")]
    try:
        arts = get(ARTICLES + "?t=%d" % now, 90)
        arts = arts if isinstance(arts, list) else arts.get("articles") or arts.get("items") or []
        arts = [a for a in arts if a.get("t0", 0) >= now - 86400]
    except Exception as e:
        log("기사 못 받음(속보만으로 진행)", type(e).__name__)
        arts = []
    if len(items) < 30:
        log("자료 부족, 건너뜀", len(items))
        return
    T, A = buckets(items, arts)
    themes, dropped = [], {}
    for k in NAME:
        src, u, d = theme_source(k, T[k], A[k])
        keep, bad = write_theme(k, src) if T[k] else ([], [])
        dropped[k] = bad
        themes.append({"k": k, "n": len(T[k]), "u": u, "d": d, "arts": len(A[k]), "ko": " ".join(a for a, _ in keep), "en": " ".join(b for _, b in keep)})
    hsrc = "\n".join(f"[{NAME[t['k']]}] {t['ko']}" for t in themes)
    hl = {"ko": "", "en": ""}
    for attempt in range(4):
        try:
            o = chat("너는 편집자다. 아래 테마별 요약을 보고 오늘 전 세계 흐름을 한 줄로 쓴다. ko: 40자 이내, en: 같은 뜻 80자 이내.\n" + RULES + '\n형식: {"ko": "", "en": ""}', hsrc, 300)
        except Exception as e:
            log("한 줄 실패", type(e).__name__)
            continue
        if ok_ko(o.get("ko", ""), hsrc) and ok_en(o.get("en", "")) and len(o.get("ko", "")) <= 60:
            hl = o
            break
    if not all(t["ko"] for t in themes if t["n"]) or not hl.get("ko"):
        log("요약이 비어 저장하지 않음", [t["k"] for t in themes if t["n"] and not t["ko"]], bool(hl.get("ko")))
        return
    doc = {"v": 1, "made": int(now), "from": int(now - 86400), "model": MODEL, "total": len(items), "articles": len(arts),
           "headline": {"ko": hl["ko"], "en": hl["en"]}, "themes": themes, "dropped": dropped}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT + ".tmp", "w") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(OUT + ".tmp", OUT)          # tg_publish가 다음 차례(1분 안)에 flash 브랜치로 올린다
    log("테마 요약 저장", OUT, "%.0fs" % (time.time() - t0), {t["k"]: (t["n"], len(t["ko"])) for t in themes}, "뺀 문장:", sum(len(v) for v in dropped.values()))


def install():
    dst = os.path.join(HOME, "theme_brief.py")
    shutil.copy2(os.path.abspath(__file__), dst)
    py = os.path.join(HOME, "tgvenv", "bin", "python")
    plist = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LABEL)
    with open(plist, "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array><string>{py}</string><string>{dst}</string></array>
  <key>StartInterval</key><integer>{EVERY}</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>{HOME}/themes.log</string>
  <key>StandardErrorPath</key><string>{HOME}/themes.log</string>
</dict></plist>
""")
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    for _ in range(10):
        if subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", plist], capture_output=True).returncode == 0:
            break
        time.sleep(1)
    log("설치 완료:", plist, "(3시간마다)")


if __name__ == "__main__":
    if "--install" in sys.argv[1:]:
        install()
    else:
        run()
