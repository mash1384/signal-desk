"""운영자 Mac에서 상시: 판정된 텔레그램 속보(tg_judge.py)를 같은 소식끼리 묶어 사이트용 flash.json을 만들고 `flash` 브랜치에 올린다.

묶기: 한국어 한 줄(ko)을 qwen3-embedding으로 임베딩해, 6시간 안에 나온 비슷한 줄을 하나로 묶는다.
  유사도 ≥ 0.85면 같은 소식. 0.80~0.85는 숫자나 코인이 겹칠 때만. 둘 다 %가 있는데 하나도 안 겹치면 다른 소식(CPI 전년비 3.3% ≠ 전월비 0.6%).
  기준은 2026-10-13 수집분의 짝 120여 개를 직접 보고 정했다.
사이트에 싣는 것: 우리가 만든 한국어 한 줄, 판정, 코인·섹터, 몇 곳이 보도했는지, 관련 기사 링크.
채널 이름·텔레그램 링크·원문 본문은 싣지 않는다(운영자 결정, 2026-10-13). 브라우저는 Worker의 /flash 로 받는다.

설치: ~/.signal/tgvenv/bin/python tools/tg_publish.py --install   (launchd com.signal.tgpub, 로그 ~/.signal/tgpub.log)
한 번만 만들어 보기(올리지 않음): ~/.signal/tgvenv/bin/python tools/tg_publish.py --dry
"""

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import urllib.request

HOME = os.path.expanduser("~/.signal")
DB = os.path.join(HOME, "tg", "tg.db")
VENV_PY = os.path.join(HOME, "tgvenv", "bin", "python")
BRANCH_DIR = os.path.join(HOME, "flash-branch")
REPO = "https://github.com/mash1384/signal-desk.git"
LABEL = "com.signal.tgpub"
OLLAMA = "http://localhost:11434"
EMB_MODEL = "qwen3-embedding:0.6b"
WINDOW = 48 * 3600          # 사이트에 싣는 기간
GAP = 6 * 3600              # 이 시간 안에 나온 줄끼리만 묶는다
SAME, MAYBE = 0.85, 0.80
EVERY = 30                  # 묶기 간격(초)
PUSH_GAP = 60               # 올리기 최소 간격(초)
MAX_ITEMS = 400
SHOW_KINDS = ("event", "data", "opinion", "price_recap")

NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
# 출처 채널이 드러나는 링크는 싣지 않는다: 텔레그램, X(속보 계정 글), 채널 운영사 사이트. 언론사 기사·거래소 공식 공지만 남는다
TG_LINK = re.compile(r"(?i)^(?!https?://)|^https?://([\w-]+\.)*(t\.me|telegram\.(me|org)|x\.com|twitter\.com|coinness\.com|theblockbeats\.\w+|"
                     r"blockbeats\.\w+|watcher\.guru|lookonchain\.com|whale-alert\.io|financialjuice\.com|wu-?blockchain\.\w+|"
                     r"substack\.com|bit\.ly|tradingbeats\.\w+|hdmune\.\w+|digitalasset\.works)(/|$)")
# 한 줄 안에 채널 이름이 들어가면 지운다(예: "룩온체인에 따르면, ")
BRAND = re.compile(r"(?i)\s*(코인니스|coinness|블록비츠|blockbeats|律动|wu ?blockchain|우블록체인|watcher ?guru|워처 ?구루|lookonchain|룩온체인|"
                   r"whale ?alert|웨일 ?얼럿|웨일 ?알러트|financial ?juice|파이낸셜 ?주스|market ?feed|마켓 ?피드|zachxbt|잭엑스비티|텔레그램|telegram)"
                   r"(에 따르면|의 보도에 따르면|가 전했다|이 전했다|는|은|이|가|에서|,)?\s*[,:·-]?\s*")
TRACK = re.compile(r"(?i)^(utm_\w+|from|ref|source)$")


def clean_link(u):
    """링크 꼬리표(utm_source=telegram-…, from=telegram)를 떼어 출처가 드러나지 않게."""
    p = urllib.parse.urlsplit(u)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True) if not TRACK.match(k)]
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(q), ""))


def log(*a):
    print(time.strftime("%m-%d %H:%M:%S"), *a, flush=True)


# ---------- 묶기 ----------
def nums(s):
    return {n.replace(",", "") for n in NUM.findall(s) if len(n.replace(",", "").replace(".", "")) >= 2}


def pcts(s):
    return set(PCT.findall(s))


def same_story(sim, a, b):
    """a, b: {'ko', 'coins'}. 임베딩 유사도와 숫자·코인으로 같은 소식인지."""
    pa, pb = pcts(a["ko"]), pcts(b["ko"])
    if pa and pb and not pa & pb:
        return False
    if sim >= SAME:
        return True
    if sim >= MAYBE:
        return bool(nums(a["ko"]) & nums(b["ko"])) or bool(set(a["coins"]) & set(b["coins"]))
    return False


def cluster(rows, sim):
    """rows는 시간순. 각 줄을, 마지막 글이 GAP 안에 있는 묶음 중 가장 비슷한 멤버가 있는 곳에 넣는다(없으면 새 묶음).
    sim[i][j]: 코사인 유사도. 반환: 묶음마다 멤버 인덱스 목록."""
    groups = []                       # [멤버 인덱스], 마지막 시각
    for i, r in enumerate(rows):
        best, best_sim = None, 0.0
        for g in groups:
            if r["t"] - rows[g[-1]]["t"] > GAP:
                continue
            for j in g:
                s = float(sim[i][j])
                if s > best_sim and same_story(s, r, rows[j]):
                    best, best_sim = g, s
        if best is None:
            groups.append([i])
        else:
            best.append(i)
    return groups


def merge(members):
    """묶음 하나 → 사이트용 항목. 대표 줄은 가장 먼저 나온 것, 판정은 세기로 가중한 다수결.
    출처 채널은 싣지 않고 몇 곳이 보도했는지만 센다. id도 채널을 드러내지 않게 해시로."""
    first = members[0]
    score = sum((m["strength"] + 1) * {"호재": 1, "악재": -1}.get(m["verdict"], 0) for m in members)
    verdict = "호재" if score > 0 else "악재" if score < 0 else "중립"
    count = lambda key: sorted({x for m in members for x in m[key]}, key=lambda x: -sum(x in m[key] for m in members))
    link = next((clean_link(u) for m in members for u in m["links"] if not TG_LINK.search(u)), "")
    ko = BRAND.sub(" ", first["ko"]).strip(" ,·-") or first["ko"]
    return {"id": hashlib.sha1(("%s-%d" % (first["ch"], first["id"])).encode()).hexdigest()[:12], "t": first["t"], "ko": " ".join(ko.split()),
            "v": verdict, "s": max(m["strength"] for m in members), "kind": first["kind"], "coins": count("coins")[:4],
            "sectors": count("sectors")[:2] if verdict != "중립" else [], "mw": any(m["market_wide"] for m in members),
            "n": len({m["ch"] for m in members}), "link": link, "en": next((" ".join((BRAND.sub(" ", m["en"]).strip(" ,·-") or m["en"]).split()) for m in members if m.get("en")), "")}


def visible(it):
    """사이트에 보일 만한 묶음: 호재·악재이거나, 큰 소식이거나, 코인을 다루는 중립 소식(크립토와 먼 중립 속보는 뺀다)."""
    return it["kind"] in SHOW_KINDS and (it["v"] != "중립" or it["s"] >= 2 or (bool(it["coins"]) and it["s"] >= 1))


# ---------- 임베딩 ----------
def db():
    con = sqlite3.connect(DB, timeout=30)
    con.execute("CREATE TABLE IF NOT EXISTS emb(ch TEXT, id INTEGER, ko TEXT, v TEXT, PRIMARY KEY(ch, id))")
    return con


def embed(texts):
    req = urllib.request.Request(OLLAMA + "/api/embed", data=json.dumps({"model": EMB_MODEL, "input": texts, "keep_alive": "30m"}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.loads(r.read())["embeddings"]
    res = []
    for v in out:
        n = sum(x * x for x in v) ** 0.5 or 1.0
        res.append([round(x / n, 5) for x in v])
    return res


KEEP_EMB = 72 * 3600        # 임베딩 보관(하루 정리가 지난 하루를 다시 묶을 수 있게)


def load(con, since=None, until=None):
    since = int(since if since is not None else time.time() - WINDOW - GAP)
    until = int(until if until is not None else time.time() + 3600)
    rows = con.execute("""SELECT m.ch, m.id, m.t, m.links, a.ko, a.kind, a.verdict, a.coins, a.sectors, a.market_wide, a.strength, a.en
        FROM msgs m JOIN ai a ON a.ch=m.ch AND a.id=m.id
        WHERE m.t >= ? AND m.t < ? AND a.ko != '' AND a.kind IN (%s) ORDER BY m.t, m.ch, m.id""" % ",".join("?" * len(SHOW_KINDS)),
                       (since, until, *SHOW_KINDS)).fetchall()
    rows = [{"ch": r[0], "id": r[1], "t": r[2], "links": json.loads(r[3] or "[]"), "ko": r[4], "kind": r[5], "verdict": r[6],
             "coins": json.loads(r[7]), "sectors": json.loads(r[8]), "market_wide": bool(r[9]), "strength": r[10], "en": r[11] or ""} for r in rows]
    have = {(c, i): (ko, json.loads(v)) for c, i, ko, v in con.execute("SELECT ch, id, ko, v FROM emb WHERE ch||id IN (SELECT ch||id FROM msgs WHERE t >= ?)", (since,))}
    need = [r for r in rows if have.get((r["ch"], r["id"]), ("",))[0] != r["ko"]]
    for k in range(0, len(need), 64):
        part = need[k:k + 64]
        for r, v in zip(part, embed([r["ko"] for r in part])):
            have[(r["ch"], r["id"])] = (r["ko"], v)
            con.execute("INSERT OR REPLACE INTO emb VALUES(?,?,?,?)", (r["ch"], r["id"], r["ko"], json.dumps(v)))
        con.commit()
    con.execute("DELETE FROM emb WHERE ch||id NOT IN (SELECT ch||id FROM msgs WHERE t >= ?)", (int(time.time()) - KEEP_EMB,))
    con.commit()
    return rows, [have[(r["ch"], r["id"])][1] for r in rows]


def stories(con, since=None, until=None):
    """기간 안의 판정된 줄을 같은 소식끼리 묶어 항목 목록으로(거르지 않음)."""
    import numpy as np
    rows, vecs = load(con, since, until)
    if not rows:
        return []
    V = np.array(vecs, dtype=np.float32).reshape(len(rows), -1)
    return [merge([rows[i] for i in g]) for g in cluster(rows, V @ V.T)]


def build(con, now=None):
    now = int(now or time.time())
    items = [it for it in stories(con) if it["t"] >= now - WINDOW and visible(it)]
    items.sort(key=lambda it: -it["t"])
    last = con.execute("SELECT MAX(got) FROM msgs").fetchone()[0] or 0
    return {"v": 2, "at": now, "last_got": last, "sectors": __import__("tg_judge").SECTORS, "items": items[:MAX_ITEMS]}


# ---------- 올리기 ----------
def git(*args):
    env = dict(os.environ, PATH="/usr/bin:/bin:/usr/sbin:/sbin:" + os.path.expanduser("~/.local/bin") + ":/opt/homebrew/bin")
    return subprocess.run(["git", *args], cwd=BRANCH_DIR, env=env, check=True, capture_output=True, text=True).stdout


def publish(doc):
    """flash 브랜치에 커밋 하나만 두고 고쳐 쓴다(이력을 쌓지 않는다). llm 브랜치(judge_live)와는 따로 둔다."""
    if not os.path.isdir(os.path.join(BRANCH_DIR, ".git")):
        os.makedirs(BRANCH_DIR, exist_ok=True)
        git("init", "-q")
        git("remote", "add", "origin", REPO)
        git("checkout", "-q", "-b", "flash")
        git("config", "user.name", "signal-flash")
        git("config", "user.email", "signal-flash@users.noreply.github.com")
    with open(os.path.join(BRANCH_DIR, "flash.json"), "w") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(BRANCH_DIR, "README.md"), "w") as f:
        f.write("운영자 Mac이 만든 속보 묶음. 사이트가 Worker /flash 로 읽는다. 사람이 고치지 않는다.\n")
    git("add", "-A")
    has_head = subprocess.run(["git", "rev-parse", "-q", "--verify", "HEAD"], cwd=BRANCH_DIR, capture_output=True).returncode == 0
    git("commit", "-q", *(["--amend"] if has_head else []), "-m", "flash")
    git("push", "-q", "-f", "origin", "HEAD:flash")


def run():
    sys.path.insert(0, HOME)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    con = db()
    log("묶기·올리기 시작")
    sent_key, sent_at, fails = None, 0, 0
    while True:
        try:
            doc = build(con)
            daily = os.path.join(BRANCH_DIR, "daily")    # daily_brief.py가 여기에 하루 정리를 넣는다
            key = json.dumps(doc["items"], ensure_ascii=False) + "".join(
                "%s%d" % (f, os.path.getmtime(os.path.join(daily, f))) for f in sorted(os.listdir(daily))) if os.path.isdir(daily) else json.dumps(doc["items"], ensure_ascii=False)
            if key != sent_key and time.time() - sent_at >= PUSH_GAP:
                publish(doc)
                sent_key, sent_at, fails = key, time.time(), 0
        except Exception as e:
            fails += 1
            log("실패", type(e).__name__, str(e)[:200])
            time.sleep(min(600, 30 * fails))
        time.sleep(EVERY)


def install():
    dst_dir = HOME
    for f in ("tg_publish.py", "tg_judge.py", "tg_collect.py"):
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), f)
        if os.path.abspath(src) != os.path.join(dst_dir, f):
            shutil.copy2(src, os.path.join(dst_dir, f))
    dst = os.path.join(dst_dir, "tg_publish.py")
    plist = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LABEL)
    with open(plist, "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array><string>{VENV_PY}</string><string>{dst}</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardOutPath</key><string>{HOME}/tgpub.log</string>
  <key>StandardErrorPath</key><string>{HOME}/tgpub.log</string>
</dict></plist>
""")
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    for _ in range(10):
        if subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", plist], capture_output=True).returncode == 0:
            break
        time.sleep(1)
    log("설치 완료:", plist)


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--install" in a:
        install()
    elif "--dry" in a:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        d = build(db())
        out = "/tmp/flash.json"
        json.dump(d, open(out, "w"), ensure_ascii=False, separators=(",", ":"))
        multi = [it for it in d["items"] if it["n"] > 1]
        log("묶음", len(d["items"]), "· 여러 채널", len(multi), "·", os.path.getsize(out) // 1024, "KB →", out)
        for it in multi[:25]:
            print(" ", it["n"], it["v"], it["ko"][:60])
    else:
        run()
