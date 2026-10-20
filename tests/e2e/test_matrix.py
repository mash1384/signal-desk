import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from tests.e2e.conftest import axe_script
from tests.e2e.contrast import ratios, regressions

# From template and render functions: r3.js, y2.js, t2.js, br2.js, c3.js,
# df_landing.html, pipeline/build.py page_daily/page_about.
SELECTORS = {"": ["#hero h1", "#nx"], "live/": ["#ps .pi", "#grid button", "#tt [role=tab]"], "my/": [".wl [data-asset]", "#feed"], "themes/crypto/": [".tsum", "#flow", "#stories"], "brief/": [".lanes .lane", ".dly"], "calendar/": ["#detail", ".schw", ".ins"], "daily/": ["h1", ".ins2"], "about/": ["h1", "main"]}


# Count rendered content, not the container. Sources: yk.js topHTML/row/daySummaryHTML,
# r3.js card, tk.js storyRow, br2.js lane, ck.js cardHTML, build.py page_daily/about.
CONTENT = {
    "": {"#hero h1": 1, "#hero .sub": 1, "#hero .btns a": 1},
    "live/": {"#grid [data-id]": 1, "#lead [data-id]": 1},
    "my/": {"#feed [data-id]": 1, ".top3 [data-id]": 1, ".dsum .lean li": 1},
    "themes/crypto/": {"#stories .srow[data-id]": 1, ".tsum li": 1},
    "brief/": {".lanes .lane[data-pick]": 1},
    "calendar/": {".ics .ic[data-ind]": 1, "#detail tbody tr": 1},
    "daily/": {".ins2 ol > li": 3},
    "about/": {"main p": 1, "main li": 1},
}


def my_fixture_counts(offline):
    doc = json.loads((offline.flash / "flash.json").read_text())
    day = [x for x in doc["items"] if x["t"] >= offline.now - 86400]
    mine = [x for x in day if set(x.get("coins", [])) & {"BTC", "ETH"} or re.search(r"엔비디아|nvidia|\bNVDA\b", x["ko"] + " " + x["en"], re.I)]
    return {"feed": len(mine), "top": sum(x["v"] != "중립" for x in mine)}


def content_checks(page, name, row, offline):
    targets = CONTENT[name]
    # Even if fixture content disappears, these assertions remain enabled.
    if name == "my/":
        row["fixture_content"] = my_fixture_counts(offline)
        if not all(row["fixture_content"].values()):
            row["errors"].append({"kind": "missing-content-fixture", "counts": row["fixture_content"]})
    try:
        page.wait_for_function("targets => Object.entries(targets).every(([s,n]) => document.querySelectorAll(s).length >= n)", arg=targets, timeout=5000)
    except Exception:
        pass  # The per-selector counts below produce an actionable failure.
    row["content"] = {s: page.locator(s).count() for s in targets}
    for selector, minimum in targets.items():
        count = row["content"][selector]
        if count < minimum or (name == "daily/" and count != 3):
            row["errors"].append({"kind": "missing-content", "selector": selector, "count": count, "expected": minimum})
        elif not page.locator(selector).first.inner_text().strip():
            row["errors"].append({"kind": "missing-content", "selector": selector, "reason": "empty text"})


def path_for(name, site):
    if name != "daily/":
        return name
    dates = sorted(p.name for p in (Path(site) / "daily").iterdir() if p.is_dir() and p.name[:4].isdigit())
    if not dates:
        raise FileNotFoundError("no dated daily page built")
    return "daily/" + dates[-1] + "/"


def test_page(case, session_page, qa, site_server, request):
    name, width, lang = case
    page, context, offline = session_page
    page.set_viewport_size({"width": width, "height": 1000})
    theme = request.config.getoption("--theme")
    context.add_init_script("localStorage.setItem('df-lang', %s); localStorage.setItem('df-my', JSON.stringify(['BTC','ETH','NVDA'])); localStorage.setItem('df-theme', %s);"
                            % (json.dumps(lang), json.dumps(theme)))
    key = "%s|%s|%s" % case
    row = {"key": key, "page": name, "width": width, "lang": lang, "bytes": 0, "requests": 0, "errors": [], "warnings": [], "axe": [], "incomplete": True}
    qa["cases"].append(row)
    host = urlsplit(site_server).netloc

    def ours(url):
        u = urlsplit(url)
        return u.netloc == host or (u.hostname == "mash1384.github.io" and u.path.startswith("/signal-desk/"))

    def response(res):
        row["requests"] += 1
        if res.status >= 400:
            (row["errors"] if ours(res.url) else row["warnings"]).append({"kind": "http", "status": res.status, "url": res.url})

    def finished(req):
        try:
            # Playwright reports actual received encoded body/header sizes.
            sizes = req.sizes()
            row["bytes"] += sizes["responseBodySize"] + sizes["responseHeadersSize"]
        except Exception as error:
            row["errors"].append({"kind": "measurement", "error": str(error)})

    page.on("response", response)
    page.on("requestfinished", finished)
    page.on("requestfailed", lambda r: (row["errors"] if ours(r.url) else row["warnings"]).append({"kind": "requestfailed", "url": r.url, "error": r.failure}))
    page.on("pageerror", lambda e: row["errors"].append({"kind": "pageerror", "error": str(e)}))
    page.goto(site_server + path_for(name, request.config.getoption("--site")), wait_until="networkidle", timeout=20000)
    if name == "" and page.locator("#intro .skip").is_visible():
        page.locator("#intro .skip").click()
    page.evaluate("document.fonts.ready")
    # Wait for data-backed elements, collecting all failures for one case.
    for selector in SELECTORS[name]:
        try:
            page.locator(selector).first.wait_for(state="visible", timeout=7000)
        except Exception:
            row["errors"].append({"kind": "missing", "selector": selector})
    content_checks(page, name, row, offline)
    page.wait_for_timeout(500)
    scroll = page.evaluate("document.documentElement.scrollWidth")
    if scroll > width:
        row["errors"].append({"kind": "overflow", "scrollWidth": scroll, "viewport": width})
    if page.locator("html").get_attribute("lang") != lang:
        row["errors"].append({"kind": "language", "expected": lang})
    if (page.locator("html").get_attribute("data-theme") or "light") != theme:
        row["errors"].append({"kind": "theme", "expected": theme})
    # 등장 효과(.reveal 서서히 나타남)가 도는 중이면 반투명 글자로 대비가 낮게 잡힌다 — 끝날 때까지(최대 4초) 기다린 뒤 검사.
    # 무한 반복 애니메이션(라이브 점 등)은 끝나지 않으므로 기다리지 않는다
    page.evaluate("""() => Promise.race([Promise.all(document.getAnimations().filter((a) => { const t = a.effect && a.effect.getComputedTiming(); return t && isFinite(t.endTime); }).map((a) => a.finished.catch(() => null))), new Promise((r) => setTimeout(r, 4000))])""")
    page.add_script_tag(path=axe_script(offline))
    result = page.evaluate("""async () => { const r = await axe.run(document, {runOnly: {type:'tag', values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}}); const pack = vs => vs.map(v=>({id:v.id,impact:v.impact,help:v.help,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary,checks:[...n.any,...n.all,...n.none]}))})); return {violations:pack(r.violations), incomplete:pack(r.incomplete), passes:pack(r.passes)}; }""")
    row["axe_details"] = result["violations"]
    row["axe_incomplete"] = result["incomplete"]
    row["contrast"] = ratios(result)
    row["axe"] = sorted(v["id"] + "|" + json.dumps(n["target"], sort_keys=True) for v in result["violations"] for n in v["nodes"])
    if offline.unmapped:
        row["errors"].append({"kind": "fixture-missing", "urls": offline.unmapped})
    row["incomplete"] = False
    if not qa["capture"]:
        a11y_errors_from = len(row["errors"])
        assert key in qa["baseline"]["axe"], "case missing from accessibility baseline"
        new = set(row["axe"]) - set(qa["baseline"]["axe"][key])
        if "contrast" in qa["baseline"]:
            expected = qa["baseline"]["contrast"][key]
            tolerance = qa["baseline"]["contrast_measurement"]["tolerance"]
            row["errors"].extend(regressions(expected, row["contrast"], tolerance))
            incomplete = {v["id"] + "|" + json.dumps(n["target"], sort_keys=True) for v in result["incomplete"] for n in v["nodes"]}
            missing = (set(expected) & incomplete) - row["contrast"].keys()
            if missing:
                row["errors"].append({"kind": "contrast-unmeasurable", "nodes": sorted(missing)})
        if new:
            row["errors"].append({"kind": "new-accessibility", "violations": sorted(new)})
        if request.config.getoption("--a11y") == "zero":
            del row["errors"][a11y_errors_from:]
            if row["axe"]:
                row["errors"].append({"kind": "accessibility", "violations": row["axe"]})
        if request.config.getoption("--a11y") == "report":
            found = row["errors"][a11y_errors_from:]
            del row["errors"][a11y_errors_from:]
            row["warnings"].extend(found)
            if found:
                print("A11Y-REPORT", key, json.dumps(found, ensure_ascii=False))
        if row["bytes"] > qa["baseline"]["budget_bytes"][name]:
            row["errors"].append({"kind": "performance", "bytes": row["bytes"], "limit": qa["baseline"]["budget_bytes"][name]})
    assert row["requests"] > 0 and row["bytes"] > 0, "nothing measured"
    print("QA", key, "bytes", row["bytes"], "external warnings", json.dumps(row["warnings"], ensure_ascii=False))
    assert not row["errors"], json.dumps(row["errors"], ensure_ascii=False)
