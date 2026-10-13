"""운영자 Mac에서 상시: 고른 텔레그램 공개 채널 12곳의 글을 받아 로컬 SQLite(~/.signal/tg/tg.db)에 쌓는다.

운영자 본인 계정으로 텔레그램 API(MTProto, Telethon)에 붙는다. 키와 로그인 세션은 ~/.signal 에만 있고 저장소에는 없다.
받은 글은 사이트에 그대로 싣지 않는다(재게시 금지). 쓰는 쪽(번역·판정·사이트 연결)은 따로 정한다.

처음 한 번:
  1) python3 tools/tg_collect.py --init
       ~/.signal/telegram.json 빈 양식을 만들고(권한 600), 스크립트를 ~/.signal 로 복사한다.
  2) my.telegram.org → API development tools 에서 받은 api_id, api_hash 를 ~/.signal/telegram.json 에 직접 적는다.
  3) ~/.signal/tgvenv/bin/python ~/.signal/tg_collect.py --login
       전화번호와 텔레그램 앱으로 온 코드(2단계 비밀번호가 있으면 그것도)를 직접 넣는다.
  4) ~/.signal/tgvenv/bin/python ~/.signal/tg_collect.py --install
       launchd 상시 실행(com.signal.tg)으로 등록한다. 로그는 ~/.signal/tg.log

선택:
  --join     12개 채널에 가입하고 알림을 끄고 보관함으로 옮긴다. 가입한 채널은 글이 즉시 밀려오고(1초 안팎),
             가입하지 않은 채널은 POLL초마다 확인한다. 계정에 채널이 생기므로 원할 때만 쓴다.
  --status   채널별 최근 24시간 글 수, 마지막 글, 받기까지 걸린 시간(중앙값)
  --tail N   최근 글 N개
"""

import asyncio
import json
import os
import shutil
import sqlite3
import statistics
import subprocess
import sys
import time

HOME = os.path.expanduser("~/.signal")
CONF = os.path.join(HOME, "telegram.json")
SESSION = os.path.join(HOME, "tg_account")          # Telethon이 tg_account.session 을 만든다(로그인 정보, 권한 600)
DB = os.path.join(HOME, "tg", "tg.db")
LOCK = os.path.join(HOME, "tg.lock")
VENV_PY = os.path.join(HOME, "tgvenv", "bin", "python")
LABEL = "com.signal.tg"
POLL = int(os.environ.get("SIGNAL_TG_POLL", 30))    # 가입 안 한 채널 확인 간격(초)
BACKFILL = 100                                      # 처음 볼 때 채널마다 가져올 지난 글 수

# 2026-10-13에 고른 12곳. 같은 시간대 글을 대조해 속도와 출처를 확인했다(signal-research/telegram).
CHANNELS = [
    ("coinnesskr", "크립토 속보", "ko"),
    ("wublockchainenglish", "크립토 속보", "en"),
    ("theblockbeats", "크립토 속보", "zh"),
    ("WatcherGuru", "크립토 속보", "en"),
    ("binance_announcements", "거래소 공지", "en"),
    ("OKXAnnouncements", "거래소 공지", "en"),
    ("Bithumb_Notice", "거래소 공지", "ko"),       # 비공식 미러
    ("lookonchainchannel", "온체인", "en"),
    ("whale_alert_io", "온체인", "en"),
    ("FinancialJuice", "경제지표·세계정세", "en"),
    ("marketfeed", "경제지표·세계정세", "en"),
    ("investigations", "사기·해킹", "en"),          # ZachXBT
]
NAMES = [c[0] for c in CHANNELS]


def log(*a):
    print(time.strftime("%m-%d %H:%M:%S"), *a, flush=True)


# ---------- 저장 ----------
def db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS msgs(
        ch TEXT, id INTEGER, t INTEGER, edit_t INTEGER, text TEXT, links TEXT, media TEXT,
        fwd TEXT, got INTEGER, via TEXT, PRIMARY KEY(ch, id))""")
    con.execute("CREATE INDEX IF NOT EXISTS msgs_t ON msgs(t)")
    return con


def row(ch, m, via, now=None):
    """Telethon 메시지 → 저장할 한 줄. 본문 링크는 표시 텍스트 뒤에 숨은 것까지 모은다."""
    links = []
    for e, txt in (m.get_entities_text() if m.entities else []):   # 오프셋이 UTF-16 기준이라 직접 자르지 않는다
        url = getattr(e, "url", None)
        if url:
            links.append(url)
        elif type(e).__name__ == "MessageEntityUrl":
            links.append(txt)
    fwd = None
    if m.fwd_from:
        fwd = getattr(m.fwd_from, "from_name", None) or str(getattr(getattr(m.fwd_from, "from_id", None), "channel_id", "") or "") or None
    return {"ch": ch, "id": m.id, "t": int(m.date.timestamp()), "edit_t": int(m.edit_date.timestamp()) if m.edit_date else None,
            "text": m.raw_text or "", "links": json.dumps([u for u in links if u], ensure_ascii=False),
            "media": type(m.media).__name__.replace("MessageMedia", "").lower() if m.media else None,
            "fwd": fwd, "got": int(now or time.time()), "via": via}


def save(con, r):
    """새 글이면 넣고 True. 이미 있으면 수정된 본문만 고친다(처음 받은 시각 got은 그대로)."""
    cur = con.execute("""INSERT INTO msgs(ch,id,t,edit_t,text,links,media,fwd,got,via) VALUES(:ch,:id,:t,:edit_t,:text,:links,:media,:fwd,:got,:via)
        ON CONFLICT(ch,id) DO UPDATE SET edit_t=excluded.edit_t, text=excluded.text, links=excluded.links
        WHERE excluded.edit_t IS NOT NULL AND excluded.edit_t IS NOT msgs.edit_t""", r)
    con.commit()
    return cur.rowcount == 1 and con.execute("SELECT got FROM msgs WHERE ch=? AND id=?", (r["ch"], r["id"])).fetchone()[0] == r["got"]


def last_ids(con):
    return dict(con.execute("SELECT ch, MAX(id) FROM msgs GROUP BY ch").fetchall())


# ---------- 설정 ----------
def conf():
    try:
        c = json.load(open(CONF))
        api_id, api_hash = int(c["api_id"]), str(c["api_hash"]).strip()
    except (FileNotFoundError, KeyError, ValueError, TypeError):
        sys.exit(f"{CONF} 에 api_id(숫자)와 api_hash 를 적어 주세요. 양식은 --init 으로 만듭니다.")
    if not api_id or len(api_hash) != 32:
        sys.exit(f"{CONF} 의 api_id / api_hash 가 비어 있거나 형식이 다릅니다(api_hash는 32자).")
    return api_id, api_hash


def client():
    from telethon import TelegramClient
    api_id, api_hash = conf()
    os.umask(0o077)               # 세션·DB 파일을 나만 읽게
    c = TelegramClient(SESSION, api_id, api_hash, device_model="SIGNAL collector", app_version="1",
                       flood_sleep_threshold=120)
    return c


def lock_session():
    for p in (SESSION + ".session", CONF):
        if os.path.exists(p):
            os.chmod(p, 0o600)


class paused:
    """상시 수집기가 세션 파일을 쥐고 있으면 --login/--join 이 'database is locked'로 막힌다. 잠깐 내렸다가 다시 올린다."""
    def __enter__(self):
        self.plist = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LABEL)
        self.target = f"gui/{os.getuid()}/{LABEL}"
        self.was = subprocess.run(["launchctl", "print", self.target], capture_output=True).returncode == 0
        if self.was:
            subprocess.run(["launchctl", "bootout", self.target], capture_output=True)
            for _ in range(50):                     # 프로세스가 내려갈 때까지(최대 10초)
                if not os.path.exists(LOCK) or not _alive(LOCK):
                    break
                time.sleep(0.2)
            log("수집기 잠시 멈춤")

    def __exit__(self, *exc):
        if self.was:
            # bootout 직후엔 launchd가 아직 정리 중이라 bootstrap이 'Input/output error'로 실패할 수 있다
            for _ in range(10):
                r = subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", self.plist], capture_output=True, text=True)
                if r.returncode == 0 or subprocess.run(["launchctl", "print", self.target], capture_output=True).returncode == 0:
                    log("수집기 다시 켬")
                    return
                time.sleep(1)
            log("수집기를 다시 켜지 못함:", r.stderr.strip()[:120], "→ --install 을 실행하세요")


def _alive(path):
    try:
        pid = int(open(path).read().strip())
        if pid <= 0:
            return False
        os.kill(pid, 0)
        return True
    except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
        return False


# ---------- 명령 ----------
def init():
    os.makedirs(HOME, exist_ok=True)
    if not os.path.exists(CONF):
        fd = os.open(CONF, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"api_id": 0, "api_hash": ""}, f, indent=1)
        log("양식 생성:", CONF, "(여기에 직접 적으세요. 대화창에 붙여넣지 마세요)")
    else:
        os.chmod(CONF, 0o600)
        log("이미 있음:", CONF)
    dst = os.path.join(HOME, "tg_collect.py")
    if os.path.abspath(__file__) != dst:
        shutil.copy2(os.path.abspath(__file__), dst)
    if not os.path.exists(VENV_PY):
        log("~/.signal/tgvenv 가 없습니다: /opt/homebrew/bin/python3.14 -m venv ~/.signal/tgvenv && ~/.signal/tgvenv/bin/pip install telethon")
    db().close()
    log("준비 완료:", dst)


async def _login():
    c = client()
    await c.start()             # 전화번호·코드·2단계 비밀번호를 터미널에서 묻는다
    me = await c.get_me()
    lock_session()
    bad = []
    for n in NAMES:
        try:
            await c.get_entity(n)
        except Exception as e:
            bad.append(f"{n}({type(e).__name__})")
        await asyncio.sleep(1)
    log("로그인됨:", me.first_name or "", "· 채널 확인", len(NAMES) - len(bad), "/", len(NAMES), *(["· 실패:"] + bad if bad else []))
    await c.disconnect()


async def _join():
    from telethon.tl.functions.channels import JoinChannelRequest
    from telethon.tl.functions.account import UpdateNotifySettingsRequest
    from telethon.tl.functions.folders import EditPeerFoldersRequest
    from telethon.tl.types import InputPeerNotifySettings, InputFolderPeer
    c = client()
    await c.connect()
    if not await c.is_user_authorized():
        sys.exit("먼저 --login")
    for n in NAMES:
        e = await c.get_entity(n)
        await c(JoinChannelRequest(e))
        await c(UpdateNotifySettingsRequest(await c.get_input_entity(e), InputPeerNotifySettings(mute_until=2 ** 31 - 1)))
        await c(EditPeerFoldersRequest([InputFolderPeer(await c.get_input_entity(e), folder_id=1)]))
        log("가입·알림 끔·보관:", n)
        await asyncio.sleep(3)
    await c.disconnect()


async def _run():
    from telethon import events, errors
    c = client()
    await c.connect()
    if not await c.is_user_authorized():
        log("로그인 전이라 멈춥니다. --login 후 --install 을 다시 실행하세요.")
        await c.disconnect()
        return 0
    lock_session()
    con = db()
    ents = {}
    for n in NAMES:
        try:
            ents[n] = await c.get_entity(n)
        except Exception as e:
            log("채널 못 찾음", n, type(e).__name__)
    by_id = {e.id: n for n, e in ents.items()}
    stat = {"push": 0, "poll": 0, "backfill": 0}

    def keep(n, m, via):
        if save(con, row(n, m, via)):
            stat[via] += 1

    async def on_msg(ev):
        n = by_id.get(getattr(ev.message.peer_id, "channel_id", None))
        if n:
            keep(n, ev.message, "push")

    c.add_event_handler(on_msg, events.NewMessage(chats=list(ents.values())))
    c.add_event_handler(on_msg, events.MessageEdited(chats=list(ents.values())))
    log("수집 시작:", len(ents), "채널, 확인 간격", POLL, "초")

    async def poll():
        last_report = time.time()
        while True:
            seen = last_ids(con)
            for n, e in ents.items():
                try:
                    lo = seen.get(n)
                    ms = await c.get_messages(e, limit=BACKFILL if lo is None else 100, min_id=lo or 0)
                    for m in reversed(ms):
                        if getattr(m, "action", None) is None:
                            keep(n, m, "poll" if lo else "backfill")   # 처음 가져온 지난 글은 속도 통계에서 뺀다
                except errors.FloodWaitError as fw:
                    log("요청 제한, 대기", fw.seconds, "초")
                    await asyncio.sleep(fw.seconds + 1)
                except Exception as ex:
                    log("받기 실패", n, type(ex).__name__, str(ex)[:120])
                await asyncio.sleep(1)
            if time.time() - last_report >= 3600:
                log("지난 1시간 새 글: 즉시", stat["push"], "· 확인", stat["poll"])
                stat.update(push=0, poll=0)
                last_report = time.time()
            await asyncio.sleep(POLL)

    task = asyncio.ensure_future(poll())
    try:
        await asyncio.wait([task, asyncio.ensure_future(c.run_until_disconnected())], return_when=asyncio.FIRST_COMPLETED)
    finally:
        task.cancel()
        con.close()
        await c.disconnect()
    return 1                      # 끊기면 launchd가 다시 띄운다


def run():
    os.makedirs(HOME, exist_ok=True)
    try:
        pid = int(open(LOCK).read().strip())
        if pid <= 0:
            raise ValueError
        os.kill(pid, 0)
        sys.exit(f"이미 도는 중(pid {pid}). 멈추려면: launchctl bootout gui/{os.getuid()}/{LABEL}")
    except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
        pass
    with open(LOCK, "w") as f:
        f.write(str(os.getpid()))
    try:
        sys.exit(asyncio.run(_run()))
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


def install():
    if not os.path.exists(VENV_PY):
        sys.exit("~/.signal/tgvenv 가 없습니다. --init 안내를 보세요.")
    conf()
    dst = os.path.join(HOME, "tg_collect.py")
    if os.path.abspath(__file__) != dst:
        shutil.copy2(os.path.abspath(__file__), dst)
    plist = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LABEL)
    with open(plist, "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array><string>{VENV_PY}</string><string>{dst}</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardOutPath</key><string>{HOME}/tg.log</string>
  <key>StandardErrorPath</key><string>{HOME}/tg.log</string>
</dict></plist>
""")
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", plist], check=True)
    log("설치 완료:", plist, "· 로그", os.path.join(HOME, "tg.log"))


def status():
    con = db()
    now = time.time()
    meta = {c[0]: c for c in CHANNELS}
    print(f"{'채널':<22}{'분류':<14}{'24시간':>6}  {'마지막 글':<12}{'받기까지(중앙값)':>16}")
    for n in NAMES:
        cnt = con.execute("SELECT COUNT(*) FROM msgs WHERE ch=? AND t>=?", (n, now - 86400)).fetchone()[0]
        last = con.execute("SELECT MAX(t) FROM msgs WHERE ch=?", (n,)).fetchone()[0]
        lag = {v: [r[0] for r in con.execute("SELECT got-t FROM msgs WHERE ch=? AND via=? AND got-t<3600 AND t>=?", (n, v, now - 7 * 86400))]
               for v in ("push", "poll")}
        lt = "  ".join(f"{'즉시' if v == 'push' else '확인'} {statistics.median(x):.0f}초" for v, x in lag.items() if x) or "–"
        print(f"{n:<22}{meta[n][1]:<14}{cnt:>6}  {time.strftime('%m-%d %H:%M', time.localtime(last)) if last else '–':<12}{lt:>16}")
    con.close()


def tail(k):
    con = db()
    for ch, t, text in reversed(con.execute("SELECT ch, t, text FROM msgs ORDER BY t DESC LIMIT ?", (k,)).fetchall()):
        print(time.strftime("%m-%d %H:%M:%S", time.localtime(t)), f"[{ch}]", " ".join(text.split())[:140])
    con.close()


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--init" in a:
        init()
    elif "--login" in a:
        with paused():
            asyncio.run(_login())
    elif "--join" in a:
        with paused():
            asyncio.run(_join())
    elif "--install" in a:
        install()
    elif "--status" in a:
        status()
    elif "--tail" in a:
        i = a.index("--tail")
        tail(int(a[i + 1]) if len(a) > i + 1 and a[i + 1].isdigit() else 30)
    else:
        run()
