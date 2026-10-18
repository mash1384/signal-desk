import json
from pathlib import Path
from urllib.parse import urlsplit
import pytest
from tests.e2e.conftest import axe_script

# From template and render functions: r3.js, y2.js, t2.js, br2.js, c3.js,
# df_landing.html, pipeline/build.py page_daily/page_about.
SELECTORS = {"": ["#hero h1", "#nx"], "live/": ["#ps .pi", "#grid button", "#tt [role=tab]"], "my/": [".wl [data-asset]", "#feed"], "themes/crypto/": [".tsum", "#flow", "#stories"], "brief/": [".lanes .lane", ".dly"], "calendar/": ["#detail", ".schw", ".ins"], "daily/": ["h1", ".ins2"], "about/": ["h1", "main"]}


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
    context.add_init_script("localStorage.setItem('df-lang', %s); localStorage.setItem('df-my', JSON.stringify(['BTC','ETH','NVDA']));" % json.dumps(lang))
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
    page.wait_for_timeout(500)
    scroll = page.evaluate("document.documentElement.scrollWidth")
    if scroll > width:
        row["errors"].append({"kind": "overflow", "scrollWidth": scroll, "viewport": width})
    if page.locator("html").get_attribute("lang") != lang:
        row["errors"].append({"kind": "language", "expected": lang})
    page.add_script_tag(path=axe_script(offline))
    result = page.evaluate("""async () => { const r = await axe.run(document, {runOnly: {type:'tag', values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}}); return {violations:r.violations.map(v=>({id:v.id,impact:v.impact,help:v.help,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})), incomplete:r.incomplete.map(v=>v.id)}; }""")
    row["axe_details"] = result["violations"]
    row["axe_incomplete"] = result["incomplete"]
    row["axe"] = sorted(v["id"] + "|" + json.dumps(n["target"], sort_keys=True) for v in result["violations"] for n in v["nodes"])
    if offline.unmapped:
        row["errors"].append({"kind": "fixture-missing", "urls": offline.unmapped})
    row["incomplete"] = False
    if not qa["capture"]:
        assert key in qa["baseline"]["axe"], "case missing from accessibility baseline"
        new = set(row["axe"]) - set(qa["baseline"]["axe"][key])
        if new:
            row["errors"].append({"kind": "new-accessibility", "violations": sorted(new)})
        if row["bytes"] > qa["baseline"]["budget_bytes"][name]:
            row["errors"].append({"kind": "performance", "bytes": row["bytes"], "limit": qa["baseline"]["budget_bytes"][name]})
    assert row["requests"] > 0 and row["bytes"] > 0, "nothing measured"
    print("QA", key, "bytes", row["bytes"], "external warnings", json.dumps(row["warnings"], ensure_ascii=False))
    assert not row["errors"], json.dumps(row["errors"], ensure_ascii=False)
