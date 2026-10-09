"""공용 도구: HTTP, 시간, 해시, JSON 입출력, 로그."""

import email.utils
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from . import config

KST = timezone(timedelta(hours=9))
UTC = timezone.utc


def log(*parts):
    print("[signal]", *parts, file=sys.stderr, flush=True)


class FetchError(Exception):
    pass


def http_get(url, timeout=15, retries=2, accept=None):
    """GET 요청. 5xx·네트워크 오류는 재시도하고, 4xx는 바로 실패시킨다."""
    headers = {"User-Agent": config.USER_AGENT, "Accept-Encoding": "gzip"}
    if accept:
        headers["Accept"] = accept
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as res:
                body = res.read()
                if res.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return body
        except urllib.error.HTTPError as e:
            last = e
            if 400 <= e.code < 500 and e.code != 429:
                raise FetchError("HTTP %d %s" % (e.code, url))
        except Exception as e:  # 네트워크 오류, 타임아웃
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise FetchError("%s %s" % (type(last).__name__, url))


def http_json(url, timeout=15, retries=2):
    return json.loads(http_get(url, timeout=timeout, retries=retries, accept="application/json").decode("utf-8"))


def http_post_json(url, payload, timeout=15):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": config.USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8"))


def now_ts():
    return int(time.time())


def iso(ts):
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def kst_to_ts(year, month, day, hour=0, minute=0):
    """한국 시간 날짜·시각을 유닉스 초로."""
    return int(datetime(year, month, day, hour, minute, tzinfo=KST).timestamp())


def datetime_utc_hour(ts):
    """UTC 기준 시(0~23)."""
    return datetime.fromtimestamp(ts, UTC).hour


def kst(ts):
    return datetime.fromtimestamp(ts, KST)


def parse_time(text):
    """RSS(RFC 822)와 ISO 8601 날짜를 유닉스 초로 바꾼다. 실패하면 None."""
    if not text:
        return None
    text = text.strip()
    try:
        dt = email.utils.parsedate_to_datetime(text)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return int(dt.timestamp())
    except (TypeError, ValueError, IndexError):
        pass
    try:
        t = text.replace("Z", "+00:00")
        if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}", t):
            t = t.replace(" ", "T", 1)
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            # 시간대가 없는 국내 매체 날짜는 KST로 본다
            dt = dt.replace(tzinfo=KST)
        return int(dt.timestamp())
    except ValueError:
        return None


def short_hash(text, n=8):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data, pretty=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(data, f, ensure_ascii=False, indent=1)
        else:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def has_hangul(text):
    return bool(re.search(r"[가-힣]", text or ""))
