import sys, time, os, re
V = time.strftime("%m%d%H%M%S")
T = open("/tmp/concepts/l/page.html").read().replace('<title>Live signals · Delfona — %%TITLE%%</title>', '<title>Brief · Delfona — %%TITLE%%</title>')
CK = open("/tmp/concepts/br/brk.css").read()
for k in sys.argv[1:]:
    css = CK + open(f"/tmp/concepts/br/{k}.css").read()
    s = T.replace("%%TITLE%%", k.upper()).replace("%%CSS%%", css).replace("%%MAIN%%", "").replace("import '../l/%%JS%%?v=%%V%%';", f"import '../br/{k}.js?v={V}';").replace("%%V%%", V).replace("%%BODY%%", k).replace("%%NAV%%", "brief")
    os.makedirs(f"/tmp/concepts/{k}", exist_ok=True); open(f"/tmp/concepts/{k}/index.html", "w").write(s)
# 공통 모듈(lk·yk·tk·ck)은 모든 페이지가 같은 버전 주소로 불러야 한 번만 실행된다
for d in ("l", "t", "y", "c", "br"):
    for f in os.listdir(f"/tmp/concepts/{d}"):
        if f.endswith(".js"):
            p = f"/tmp/concepts/{d}/{f}"; s = open(p).read(); s = re.sub(r"\?v=(%%V%%|\d+)'", f"?v={V}'", s); open(p, "w").write(s)
for d in os.listdir("/tmp/concepts"):
    h = f"/tmp/concepts/{d}/index.html"
    if os.path.exists(h) and any(x in open(h).read() for x in ("../l/", "../t/", "../y/", "../c/", "../br/")):
        s = open(h).read(); s = re.sub(r"(\.(?:js|css))\?v=\d+", lambda m: f"{m.group(1)}?v={V}", s); open(h, "w").write(s)
print("built", V)
