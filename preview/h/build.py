import sys, os, time
VER = time.strftime("%Y%m%d%H%M")
T=open("/tmp/concepts/h/template.html").read(); COPY=open("/tmp/concepts/h/copy.html").read()
def build(name, title, css, hero_extra, js_import, pos="left", after="", nxt=None):
    hero = '<canvas class="gl" id="gl" aria-hidden="true"></canvas>\n' + COPY.replace("%%POS%%", pos) + hero_extra
    s = T.replace("%%TITLE%%", title).replace("%%CSS%%", css).replace("%%HERO%%", hero).replace("%%JS%%", f"import './{js_import}?v={VER}';" + (f"\nimport '{nxt}?v={VER}';" if nxt else "")).replace("%%AFTER%%", after).replace("%%S5%%", "" if nxt else '<script src="../s/s5.js"></script>')
    os.makedirs(f"/tmp/concepts/{name}", exist_ok=True); open(f"/tmp/concepts/{name}/index.html","w").write(s)
CSS_LEFT = """.copy.left { left: 0; right: 0; top: 50%; transform: translateY(-50%); max-width: 1240px; margin: 0 auto; padding-inline: 36px; }
.copy.left h1 { max-width: 42rem; } .copy.left .sub { max-width: 30rem; }
.hero::after { content: ''; position: absolute; inset: 0; z-index: 2; pointer-events: none; background: linear-gradient(90deg, #f7f9fc 18%, rgb(247 249 252 / .7) 42%, transparent 62%); }
@media (max-width: 899px) { .hero::after { background: linear-gradient(0deg, #f7f9fc 40%, rgb(247 249 252 / .6) 58%, transparent 75%); } }
@media (max-width: 899px) { .copy.left { top: auto; bottom: 7svh; transform: none; padding-inline: 20px; } .copy .sub { font-size: 16px; } }
.hud { left: 50%; bottom: 24px; transform: translateX(-50%); opacity: 0; white-space: nowrap; }
@media (max-width: 899px) { .hud { display: none; } }"""
CSS_TIP = """.tip { position: fixed; z-index: 40; max-width: 320px; padding: 10px 12px; border-radius: 12px; background: rgb(13 31 54 / .94); color: #eef3fa; font-size: 13.5px; line-height: 1.45; pointer-events: none; opacity: 0; transform: translateY(4px); transition: opacity 150ms ease, transform 150ms ease; }
.tip.on { opacity: 1; transform: none; } .tip b { font-size: 12px; margin-right: 4px; } .tip small { display: block; margin-top: 4px; font-family: var(--mono); font-size: 10.5px; color: #8fa3bd; }
.tip b.up { color: #4fe0ab; } .tip b.down { color: #ff9b8c; }"""

N3_CSS = """
.nx { position: relative; height: 100vh; height: 100svh; min-height: 620px; overflow: hidden; background: #f7f9fc; --cp: 0; --ep: 0; }
.nx-gl { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
.nx-copy { position: absolute; z-index: 3; left: max(36px, calc(50% - 584px)); top: 50%; transform: translateY(calc(-50% + (1 - var(--cp)) * 24px)); width: min(400px, 33vw); opacity: var(--cp); }
.nx-k { font-family: var(--mono); font-size: 12px; letter-spacing: .14em; text-transform: uppercase; color: var(--primary); }
.nx-steps { list-style: none; padding: 0; margin-top: 18px; }
.nx-steps li { position: relative; display: grid; grid-template-columns: 40px 1fr; padding: 16px 0; border-top: 1px solid var(--line); color: #8a96aa; transition: color 300ms ease; }
.nx-steps li .n { font-family: var(--mono); font-size: 12px; padding-top: 6px; }
.nx-steps li b { display: block; font-size: 21px; font-weight: 400; letter-spacing: -0.02em; line-height: 1.3; transition: font-size 300ms var(--ease); }
:lang(ko) .nx-steps li b { font-weight: 500; }
.nx-steps li p { max-height: 0; opacity: 0; overflow: hidden; font-size: 15.5px; line-height: 1.5; color: var(--mute); transition: max-height 400ms var(--ease), opacity 300ms ease, margin 300ms ease; }
.nx-steps li.on { color: var(--ink); } .nx-steps li.on b { font-size: 30px; } .nx-steps li.on p { max-height: 90px; opacity: 1; margin-top: 8px; }
.nx-steps li i { position: absolute; left: 0; right: 0; top: -1px; height: 2px; background: var(--ink); transform-origin: left; transform: scaleX(0); }
.nx-end { position: absolute; inset: 0; z-index: 3; display: grid; place-content: center; padding: 20px; text-align: center; opacity: var(--ep); pointer-events: none; }
.nx-end .box { padding: 34px 44px 38px; border-radius: 28px; background: rgb(247 249 252 / .86); backdrop-filter: blur(18px) saturate(1.2); -webkit-backdrop-filter: blur(18px) saturate(1.2); box-shadow: 0 30px 80px -30px rgb(13 37 61 / .45), 0 0 0 1px rgb(13 37 61 / .06); transform: translateY(calc((1 - var(--ep)) * 30px)) scale(calc(.96 + var(--ep) * .04)); }
.nx-end b { display: block; max-width: 13em; font-size: clamp(30px, 4.2vw, 58px); font-weight: 300; letter-spacing: -0.045em; line-height: 1.08; } :lang(ko) .nx-end b { font-weight: 500; }
.nx-end em { font-style: normal; color: var(--primary); font-variant-numeric: tabular-nums; }
.nx-end .btn { margin-top: 24px; pointer-events: auto; }
@media (max-width: 899px) {
  .nx-copy { left: 20px; right: 20px; top: 84px; width: auto; transform: translateY(calc((1 - var(--cp)) * 20px)); }
  .nx-steps { margin-top: 10px; } .nx-steps li { display: none; border: 0; padding: 0; } .nx-steps li.on { display: grid; }
  .nx-steps li.on b { font-size: 28px; } .nx-steps li i { display: none; }
  .nx-end .box { padding: 26px 22px 28px; } }"""
N3_HTML = """<section class="nx" id="nx" aria-label="Inside one signal"><canvas class="nx-gl" id="nxgl" aria-hidden="true"></canvas>
<div class="nx-copy"><p class="nx-k"></p><ol class="nx-steps"></ol></div>
<div class="nx-end"><div class="box"><b></b><a class="btn p" href="#" data-t="cta">Open live signals</a></div></div></section>
"""

N5_CSS = """
.nx { position: relative; height: 100vh; height: 100svh; min-height: 620px; overflow: hidden; background: #f7f9fc; --cap: 0; --hud: 0; --end: 0; }
.nx-gl { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
.rv-lay { position: absolute; inset: 0; z-index: 2; pointer-events: none; overflow: hidden; }
.rv-tick { position: absolute; left: 0; top: 0; padding: 3px 7px; border-radius: 6px; background: rgb(247 249 252 / .82); font-family: var(--mono); font-size: 11px; letter-spacing: .08em; color: var(--mute); white-space: nowrap; opacity: 0; }
.rv-card { position: absolute; left: 0; top: 0; width: 300px; padding: 14px 16px 15px; border-radius: 16px; background: rgb(255 255 255 / .88); backdrop-filter: blur(14px) saturate(1.3); -webkit-backdrop-filter: blur(14px) saturate(1.3); box-shadow: 0 22px 50px -22px rgb(13 37 61 / .4), 0 0 0 1px rgb(13 37 61 / .06); transform-origin: 50% 100%; opacity: 0; }
.rv-card .m { display: flex; align-items: center; gap: 8px; font-family: var(--mono); font-size: 11.5px; color: var(--mute); }
.rv-card .m b { font-family: var(--sans); font-size: 11px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; }
.rv-card .t { margin-top: 6px; font-size: 15.5px; font-weight: 500; line-height: 1.42; letter-spacing: -0.01em; color: var(--ink); }
.rv-cap { position: absolute; z-index: 3; left: 0; right: 0; top: 11vh; padding: 0 20px; text-align: center; opacity: var(--cap); transform: translateY(calc((1 - var(--cap)) * 20px)); pointer-events: none; }
.rv-cap b { display: block; font-size: clamp(30px, 4.4vw, 60px); font-weight: 300; letter-spacing: -0.045em; line-height: 1.08; } :lang(ko) .rv-cap b { font-weight: 500; }
.rv-cap span { display: block; max-width: 34rem; margin: 12px auto 0; font-size: 16px; color: var(--mute); }
.rv-cap .lg { display: inline-flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 8px 16px; margin-top: 18px; font-family: var(--mono); font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--mute); }
.rv-cap .lg i { display: inline-block; width: 20px; height: 7px; margin-right: 6px; border-radius: 4px; vertical-align: middle; }
.rv-cap .lg i.w { background: linear-gradient(90deg, #533afd, #0d253d); height: 11px; } .rv-cap .lg i.g { background: #12b07c; } .rv-cap .lg i.r { background: #e5533f; } .rv-cap .lg i.dt { width: 9px; height: 9px; border-radius: 50%; background: #fff; box-shadow: inset 0 0 0 2.5px #12b07c; }
.rv-hud { position: absolute; z-index: 3; top: 92px; left: 50%; transform: translateX(-50%); padding: 9px 16px 11px; border-radius: 99px; background: rgb(255 255 255 / .84); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); box-shadow: 0 0 0 1px rgb(13 37 61 / .07), 0 10px 30px -16px rgb(13 37 61 / .3); font-family: var(--mono); font-size: 12.5px; color: var(--ink2); white-space: nowrap; opacity: var(--hud); --fu: 0; }
.rv-hud::after { content: ''; position: absolute; left: 16px; right: 16px; bottom: 4px; height: 2px; border-radius: 2px; background: linear-gradient(90deg, var(--ink) calc(var(--fu) * 100%), rgb(13 37 61 / .12) 0); }
.rv-end { position: absolute; z-index: 3; left: 0; right: 0; bottom: 7vh; display: flex; justify-content: center; align-items: stretch; gap: 16px; padding: 0 20px; opacity: var(--end); transform: translateY(calc((1 - var(--end)) * 30px)); pointer-events: none; }
.rv-now, .rv-next { width: min(380px, 44vw); padding: 22px 24px 24px; border-radius: 22px; background: rgb(255 255 255 / .9); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); box-shadow: 0 30px 70px -30px rgb(13 37 61 / .45), 0 0 0 1px rgb(13 37 61 / .06); }
.rv-next { background: #0d1f36; color: #fff; }
.rv-end .k { font-family: var(--mono); font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: var(--primary); } .rv-next .k { color: #a9b3ff; }
.rv-end b { display: block; margin-top: 8px; font-size: 26px; font-weight: 400; letter-spacing: -0.03em; line-height: 1.15; } :lang(ko) .rv-end b { font-weight: 500; }
.rv-end .br { margin-top: 12px; font-size: 14.5px; line-height: 1.5; color: var(--ink2); } .rv-end .br span { display: block; margin-bottom: 4px; font-family: var(--mono); font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--mute); }
.rv-end .cd { margin-top: 6px; font-size: 44px; font-weight: 300; letter-spacing: -0.04em; line-height: 1; font-variant-numeric: tabular-nums; }
.rv-end .s { margin-top: 10px; font-size: 14px; color: rgb(255 255 255 / .7); } .rv-end em { font-style: normal; color: #c9ccff; }
@media (max-width: 899px) {
  .rv-card { width: 236px; padding: 12px 13px; } .rv-card .t { font-size: 14px; }
  .rv-cap { top: 84px; } .rv-cap span { font-size: 15px; } .rv-hud { top: 78px; font-size: 11px; padding: 8px 12px 10px; }
  .rv-end { flex-direction: column; align-items: center; bottom: 16px; gap: 10px; } .rv-now, .rv-next { width: 100%; max-width: 420px; padding: 16px 18px 18px; }
  .rv-end b { font-size: 21px; } .rv-end .cd { font-size: 34px; } }"""
N5_HTML = """<section class="nx rv" id="nx" aria-label="The last 24 hours"><canvas class="nx-gl" id="nxgl" aria-hidden="true"></canvas><div class="rv-lay"></div>
<div class="rv-cap"></div><p class="rv-hud"></p><div class="rv-end"></div></section>
"""

if __name__ == "__main__":
    which = sys.argv[1:]
    if "h2" in which: build("h2", "H2 · Price terrain", CSS_LEFT.replace("rgb(247 249 252 / .7) 42%, transparent 62%", "rgb(247 249 252 / .55) 38%, transparent 55%") + CSS_TIP, '<p class="hud" id="hud"></p><div class="tip" id="tip"></div>', "../h/h2.js")
    H3_CSS = CSS_LEFT.replace("rgb(247 249 252 / .7) 42%, transparent 62%", "rgb(247 249 252 / .4) 40%, transparent 55%") + """
.sc { position: absolute; z-index: 4; left: 0; right: 0; top: 12vh; text-align: center; padding: 0 20px; opacity: 0; pointer-events: none; }
.sc b { display: block; font-size: clamp(30px, 4.4vw, 58px); font-weight: 300; letter-spacing: -0.045em; line-height: 1.08; color: var(--ink); }
:lang(ko) .sc b { font-weight: 500; } .sc span { display: block; margin-top: 10px; font-size: 16px; color: var(--mute); }
.bl { position: absolute; z-index: 4; transform: translate(-50%, -100%); text-align: center; opacity: 0; pointer-events: none; }
.bl b { display: block; font-size: clamp(40px, 5vw, 72px); font-weight: 300; letter-spacing: -0.05em; line-height: 1; font-variant-numeric: tabular-nums; }
.bl span { display: block; margin-top: 4px; font-family: var(--mono); font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--mute); }
body .hero { position: relative; } body .hero::after { opacity: var(--wm, 1); }"""
    H3_HERO = '<p class="hud" id="hud"></p><div class="sc" id="sc"><b></b><span></span></div><p class="bl up" id="nL"><b>0</b><span data-t="bl1">Bullish · 24h</span></p><p class="bl down" id="nR"><b>0</b><span data-t="bl2">Bearish · 24h</span></p>'
    if "h3" in which: build("h3", "H3 · Particle mark", H3_CSS + N3_CSS, H3_HERO, "../h/h3.js", after=N3_HTML, nxt="../n/n3.js")
    for k in ("p1", "p2", "p3", "p4", "p5"):
        if k in which: build(k, "H3 + " + k.upper(), H3_CSS + open("/tmp/concepts/p/px.css").read(), H3_HERO, "../h/h3.js", after=open("/tmp/concepts/p/px.html").read(), nxt="../p/%s.js" % k)
    E_CSS = open("/tmp/concepts/e/e.css").read() + open("/tmp/concepts/p/px.css").read()
    for k, nm in (("e1", "E1 · Eclipse"), ("e2", "E2 · Construction"), ("e3", "E3 · Signal")):
        if k in which: build(k, nm, E_CSS, "", "../e/%s.js" % k, after=open("/tmp/concepts/p/px.html").read(), nxt="../p/p5.js")
    V_CSS = open("/tmp/concepts/v/v.css").read() + open("/tmp/concepts/p/px.css").read()
    for k, nm in (("v1", "V1 · Totality"), ("v2", "V2 · Rim light"), ("v3", "V3 · Decode")):
        if k in which: build(k, nm, V_CSS, "", "../v/%s.js" % k, after=open("/tmp/concepts/p/px.html").read(), nxt="../p/p5.js")
    B_CSS = open("/tmp/concepts/b/b.css").read() + open("/tmp/concepts/p/px.css").read()
    for k, nm in (("b1", "B1 · Studio orbit"), ("b2", "B2 · Eclipse light"), ("b3", "B3 · Assembly")):
        if k in which: build(k, nm, B_CSS, "", "../b/%s.js" % k, after=open("/tmp/concepts/p/px.html").read(), nxt="../p/p5.js")
    M_CSS = open("/tmp/concepts/mo/mo.css").read() + open("/tmp/concepts/p/px.css").read()
    for k, nm in (("m1", "M1 · Totality"), ("m2", "M2 · One stroke"), ("m3", "M3 · Orbit snap")):
        if k in which: build(k, nm, M_CSS, "", "../mo/%s.js" % k, pos="center", after=open("/tmp/concepts/p/px.html").read(), nxt="../p/p5.js")
    if "h4" in which: build("h4", "H4 · Card constellation", CSS_LEFT.replace("rgb(247 249 252 / .7) 42%, transparent 62%", "rgb(247 249 252 / .5) 40%, transparent 56%"), '<p class="hud" id="hud"></p>', "../h/h4.js")
    if "h5" in which: build("h5", "H5 · Liquid ink", CSS_LEFT.replace(".hero::after", ".hero::before").replace("rgb(247 249 252 / .7) 42%, transparent 62%", "rgb(247 249 252 / .0) 40%, transparent 55%") + """
.tk { position: absolute; z-index: 4; left: 0; right: 0; bottom: 0; height: 52px; overflow: hidden; opacity: 0; background: rgb(255 255 255 / .55); backdrop-filter: blur(16px) saturate(1.4); -webkit-backdrop-filter: blur(16px) saturate(1.4); border-top: 1px solid rgb(255 255 255 / .6); }
.tk-row { display: flex; gap: 44px; width: max-content; height: 100%; align-items: center; padding-left: 24px; animation: tk 90s linear infinite; font-size: 14px; font-weight: 500; white-space: nowrap; color: var(--ink); }
.tk-row b { font-size: 11px; font-weight: 700; margin-right: 8px; letter-spacing: .04em; text-transform: uppercase; }
@keyframes tk { to { transform: translateX(-50%); } }
@media (prefers-reduced-motion: reduce) { .tk-row { animation: none; } }
@media (max-width: 899px) { .copy.left { bottom: calc(7svh + 52px); } }
body .hero { position: relative; } body .hero::before { opacity: var(--wm, 1); }
.hd .logo, .hd .nav, .lang button { transition: color 300ms ease, background-color 300ms ease; }
body.ink .hd .logo, body.ink .hd .nav { color: #fff; } body.ink .lang { background: rgb(255 255 255 / .12); box-shadow: inset 0 0 0 1px rgb(255 255 255 / .2); }
body.ink .lang button { color: #dfe4ff; } body.ink .lang button[aria-pressed='true'] { background: #fff; color: var(--ink); }
.st { position: absolute; z-index: 4; inset: 0; display: grid; place-content: center; text-align: center; padding: 0 24px; opacity: 0; pointer-events: none; color: #fff; }
.st-l { max-width: 15em; margin: 0 auto; font-size: clamp(34px, 5.4vw, 80px); font-weight: 300; letter-spacing: -0.045em; line-height: 1.06; }
:lang(ko) .st-l { font-weight: 500; letter-spacing: -0.04em; } .st-row { display: block; } .st-row.em { margin-top: .12em; color: #c9ccff; } .st-l .w { display: inline-block; opacity: .14; }
.st-n { margin-top: 28px; font-family: var(--mono); font-size: 13px; letter-spacing: .04em; color: rgb(255 255 255 / .72); opacity: 0; }
.st-n b { color: #fff; font-weight: 600; } .st-n b.up { color: #5ee6b4; } .st-n b.down { color: #ff9d8e; }""" + N5_CSS, '<div class="tk" id="tk" aria-label="Live headlines"></div><div class="st" id="st"><p class="st-l"></p><p class="st-n"></p></div>', "../h/h5.js", after=N5_HTML, nxt="../n/n5.js")
    if "h1" in which: build("h1", "H1 · Glass orb", CSS_LEFT, '<p class="hud" id="hud"></p>', "../h/h1.js")
