export function start(api, FLASH, on) {   // on(소식들, 문서 시각): lk.js 가 합친다
  const URL_WS = FLASH.replace('https:', 'wss:').replace('/flash', '/ws'), QUIET = 150000;
  let ws = null, synced = false, seq = 0, lastMsg = 0, fails = 0, waitUntil = 0, pauseUntil = 0, timer = null, watch = null, mk = null, wasOk = false, downAt = 0;
  const healthy = () => !!ws && ws.readyState === 1 && synced && Date.now() - lastMsg < QUIET;
  const part = (o) => (o && Date.now() / 1000 - (o.at || 0) < 150 ? o : null);
  const market = (i) => part(mk && mk.market && mk.market[i]);
  const indices = () => (mk && mk.indices && part(mk.indices.nq) && part(mk.indices.es) ? mk.indices : null);
  const degraded = () => { if (healthy()) downAt = 0; else if (wasOk && !downAt) downAt = Date.now(); return !!downAt && Date.now() - downAt > 300000; };
  function schedule() {
    clearTimeout(timer);
    const ms = fails >= 5 ? 300000 : fails === 0 ? 1000 + Math.random() * 29000 : Math.min(60000, 2000 * 2 ** (fails - 1)) * (1 + Math.random());
    if (fails >= 5) { fails = 0; pauseUntil = Date.now() + ms; }
    waitUntil = Date.now() + ms; timer = setTimeout(() => { waitUntil = 0; connect(); }, ms);
  }
  function onMsg(me, m) {
    if (!m || typeof m.t !== 'string') return;
    if (m.t === 'hello') {
      if (m.v !== 2 || !Number.isInteger(m.seq)) { drop(me, true); return; }
      synced = true; seq = m.seq; fails = 0; wasOk = true; lastMsg = Date.now();
      if (m.market) mk = m.market;
      if (m.doc && Array.isArray(m.doc.items)) on(m.doc.items, m.doc.at);
      return;
    }
    if (!synced) return;
    if (m.seq !== seq + 1) { drop(me, false); return; }
    seq = m.seq; lastMsg = Date.now();
    if (m.t === 'market') mk = { market: m.market, indices: m.indices };
    on(Array.isArray(m.items) ? m.items : [], m.at);   // market 도 문서 시각(at)을 실어 '업데이트 지연'을 판단(R25-F2)
  }
  function drop(me, failed) { ws = null; synced = false; if (failed) fails++; try { me.close(); } catch (e) {} degraded(); schedule(); }
  function connect() {
    if (typeof WebSocket !== 'function' || ws || Date.now() < waitUntil) return;
    clearTimeout(timer); synced = false; lastMsg = Date.now();
    let me; try { me = ws = new WebSocket(URL_WS); } catch (e) { ws = null; fails++; schedule(); return; }
    me.onmessage = (e) => { if (ws !== me) return; let m; try { m = JSON.parse(e.data); } catch (x) { return; } onMsg(me, m); };   // 살아 있음은 hello 와 그 뒤 이어진 메시지로만
    me.onclose = () => { if (ws !== me) return; ws = null; if (!synced) fails++; synced = false; degraded(); schedule(); };
    me.onerror = () => {};
    if (!watch) {
      watch = setInterval(() => { degraded(); if (ws && Date.now() - lastMsg >= QUIET) drop(ws, !synced); }, 15000);
      document.addEventListener('visibilitychange', () => { if (!document.hidden && !ws && Date.now() >= pauseUntil) { waitUntil = 0; connect(); } });
    }
  }
  const bundle = (lv) => { const h = market('1h'), f = market('5m'), ix = indices(); return h && f && ix ? { ...lv, market: { '1h': h, '5m': f }, indices: ix } : null; };
  const quiet = () => healthy() || degraded();   // 속보 5초 확인을 쉬는가
  Object.assign(api, { healthy, quiet, degraded, market, bundle });
  connect();
}
