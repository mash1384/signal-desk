import sys, time, os, re
V = time.strftime("%m%d%H%M%S")
T = open("/tmp/concepts/l/page.html").read()
for k in sys.argv[1:]:
    css = open(f"/tmp/concepts/l/{k}.css").read() if os.path.exists(f"/tmp/concepts/l/{k}.css") else ""
    s = T.replace("%%TITLE%%", k.upper()).replace("%%CSS%%", css).replace("%%MAIN%%", "").replace("%%JS%%", f"{k}.js").replace("%%V%%", V).replace("%%BODY%%", k).replace("%%NAV%%", "live")
    os.makedirs(f"/tmp/concepts/{k}", exist_ok=True); open(f"/tmp/concepts/{k}/index.html", "w").write(s)
# lk.js import 버전
for f in os.listdir("/tmp/concepts/l"):
    if f.endswith(".js") and f != "lk.js":
        p = f"/tmp/concepts/l/{f}"; s = open(p).read()
        import re; s = re.sub(r"from './lk\.js(\?v=\w+)?'", f"from './lk.js?v={V}'", s); open(p, "w").write(s)
# 공통 모듈(lk·yk·tk)은 모든 페이지가 같은 버전 주소로 불러야 한 번만 실행된다
for d in ("l", "t", "y"):
    for f in os.listdir(f"/tmp/concepts/{d}"):
        if f.endswith(".js"):
            p = f"/tmp/concepts/{d}/{f}"; s = open(p).read(); s = re.sub(r"\?v=(%%V%%|\d+)'", f"?v={V}'", s); open(p, "w").write(s)
for d in os.listdir("/tmp/concepts"):
    h = f"/tmp/concepts/{d}/index.html"
    if os.path.exists(h) and ("../l/" in open(h).read() or "../t/" in open(h).read() or "../y/" in open(h).read()):
        s = open(h).read(); s = re.sub(r"(\.(?:js|css))\?v=\d+", lambda m: f"{m.group(1)}?v={V}", s); open(h, "w").write(s)
print("built", V)
