"""텔레그램 채널 알림. TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID가 있을 때만 보낸다.

규칙: 하루 최대 12건, 같은 키는 30분 안에 한 번, 01~07시(KST)에는 urgent만.
"""

import html
import os

from . import config, util


def enabled():
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def _send(text):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    res = util.http_post_json(
        "https://api.telegram.org/bot%s/sendMessage" % token,
        {"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text, "parse_mode": "HTML", "disable_web_page_preview": False},
    )
    return bool(res.get("ok"))


def dispatch(alerts, state, now):
    """alerts: [{key, text, urgent}] → 보낸 건수. 보낸 기록은 state['alerts']에 남긴다."""
    log = state.setdefault("alerts", {"sent": {}, "day": "", "count": 0})
    day = util.kst(now).strftime("%Y-%m-%d")
    if log["day"] != day:
        log["day"], log["count"] = day, 0
    # 하루 지난 기록은 정리
    log["sent"] = {k: t for k, t in log["sent"].items() if now - t < 86400 * 2}
    if not enabled():
        return 0
    hour = util.kst(now).hour
    quiet = config.QUIET_HOURS_KST[0] <= hour < config.QUIET_HOURS_KST[1]
    sent = 0
    for al in alerts:
        if log["count"] >= config.ALERT_DAILY_CAP:
            break
        if al["key"] in log["sent"] and now - log["sent"][al["key"]] < config.ALERT_DEDUPE_SECONDS:
            continue
        if al["key"] in log["sent"] and al.get("once"):
            continue
        if quiet and not al.get("urgent"):
            continue
        try:
            if _send(al["text"]):
                log["sent"][al["key"]] = now
                log["count"] += 1
                sent += 1
        except Exception as e:
            util.log("telegram failed", e)
            break
    return sent


def esc(text):
    return html.escape(text or "", quote=False)
