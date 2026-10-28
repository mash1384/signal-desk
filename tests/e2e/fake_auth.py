"""회원 서버(api.delfona.com/auth/*, worker/src/auth.js)의 가짜 — 화면 시험용. 오류 이름 · 응답 모양은 진짜와 같게 둔다.

진짜 서버의 규칙 자체(해시 · 속도 제한 · Gmail 점 등)는 tests/worker/auth.test.mjs 가 진짜 SQLite 로 시험한다.
여기서는 화면이 각 답을 맞게 보여 주는지만 본다. 인증번호는 항상 CODE, 로그인 상태는 이 가짜가 기억한다(브라우저 문맥 하나 = 사람 하나).
"""
import json
import re
import time

CODE = "246810"
PW_OK = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,128}$")


class FakeAuth:
    def __init__(self):
        self.users = {}          # 이메일 → 정보
        self.codes = {}          # (이메일, 목적) → {"tries": n, "ok": bool}
        self.session = None      # 로그인한 이메일
        self.calls = []          # (경로, 본문) — 시험이 무엇을 보냈는지 본다
        self.fail = {}           # 경로 → (상태, 본문): 다음 한 번 그 답을 낸다
        self.mail_ready = True   # False 면 /auth/code 가 not_configured(키를 아직 안 넣은 운영 상태)

    def add(self, email, password="abcd1234", marketing=False):
        self.users[email] = {"email": email, "pw": password, "created": int(time.time()) - 86400 * 3, "marketing": marketing,
                             "marketing_at": int(time.time()) - 86400 * 3 if marketing else None, "lang": "ko"}

    def pub(self, u):
        return {k: u[k] for k in ("email", "created", "marketing", "marketing_at", "lang")}

    def handle(self, route):
        req = route.request
        origin = req.headers.get("origin")
        cors = {"access-control-allow-origin": origin or "", "access-control-allow-credentials": "true", "vary": "Origin",
                "access-control-allow-methods": "GET, POST", "access-control-allow-headers": "Content-Type", "cache-control": "no-store"}
        if req.method == "OPTIONS":
            route.fulfill(status=204, headers=cors, body=b"")
            return
        path = req.url.split("api.delfona.com", 1)[1].split("?")[0] if "api.delfona.com" in req.url else req.url.split(".dev", 1)[1].split("?")[0]
        body = json.loads(req.post_data or "{}") if req.method == "POST" else {}
        self.calls.append((path, body))
        status, out = self.answer(path, req.method, body)
        route.fulfill(status=status, headers={**cors, "content-type": "application/json"}, body=json.dumps(out))

    def answer(self, path, method, b):
        if path in self.fail:
            return self.fail.pop(path)
        if path == "/auth/me":
            u = self.users.get(self.session)
            return (200, {"user": self.pub(u)}) if u else (401, {"error": "signed_out"})
        email = str(b.get("email", "")).strip().lower()
        if path == "/auth/logout":
            self.session = None
            return 200, {"ok": True}
        if path in ("/auth/code", "/auth/code/check", "/auth/signup", "/auth/reset", "/auth/login"):
            if not re.match(r"^[^\s@]+@[^\s@]+\.[a-z]{2,}$", email):
                return 400, {"error": "email"}
            purpose = "signup" if path == "/auth/signup" else "reset" if path == "/auth/reset" else b.get("purpose")
            if path == "/auth/login":
                u = self.users.get(email)
                if not u or u["pw"] != b.get("password"):
                    return 401, {"error": "login"}
                self.session = email
                return 200, {"user": self.pub(u)}
            if purpose == "signup" and email in self.users:
                return 409, {"error": "exists"}
            if purpose == "signup" and email.endswith("@mailinator.com"):
                return 400, {"error": "disposable"}
            if purpose == "reset" and email not in self.users:
                return 404, {"error": "not_found"}
            if path == "/auth/code":
                if not self.mail_ready:
                    return 503, {"error": "not_configured"}
                self.codes[(email, purpose)] = {"tries": 0, "ok": False}
                return 200, {"ok": True, "ttl": 180, "gap": 30}
            c = self.codes.get((email, purpose))
            if not c:
                return 400, {"error": "code_expired"}
            if c["tries"] >= 5:
                return 400, {"error": "code_locked"}
            if str(b.get("code", "")).replace(" ", "") != CODE:
                c["tries"] += 1
                return 400, ({"error": "code_locked"} if c["tries"] >= 5 else {"error": "code_wrong", "left": 5 - c["tries"]})
            if path == "/auth/code/check":
                c["ok"] = True
                return 200, {"ok": True}
            if not PW_OK.match(str(b.get("password", ""))):
                return 400, {"error": "password"}
            del self.codes[(email, purpose)]
            if path == "/auth/signup":
                a = b.get("agree") or {}
                if not (a.get("age14") is True and a.get("terms") is True and a.get("privacy") is True):
                    return 400, {"error": "agree"}
                self.add(email, b["password"], a.get("marketing") is True)
                now = int(time.time())
                self.users[email].update(created=now, marketing_at=now if a.get("marketing") is True else None)
            else:
                self.users[email]["pw"] = b["password"]
            self.session = email
            return 200, {"user": self.pub(self.users[email])}
        u = self.users.get(self.session)
        if not u:
            return 401, {"error": "signed_out"}
        if path == "/auth/marketing":
            u["marketing"], u["marketing_at"] = b.get("on") is True, int(time.time())
            return 200, {"user": self.pub(u)}
        if path == "/auth/password":
            if b.get("current") != u["pw"]:
                return 401, {"error": "login"}
            if not PW_OK.match(str(b.get("password", ""))):
                return 400, {"error": "password"}
            u["pw"] = b["password"]
            return 200, {"ok": True}
        if path == "/auth/delete":
            if b.get("password") != u["pw"]:
                return 401, {"error": "login"}
            del self.users[self.session]
            self.session = None
            return 200, {"ok": True}
        return 404, {"error": "not_found"}
