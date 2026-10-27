(() => {
  const fmt = (t, lang, mode) => {
    const d = new Date(t * 1000), o = mode === 'hm' ? { hour: '2-digit', minute: '2-digit', hour12: false } : { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false };
    try { return new Intl.DateTimeFormat(lang === 'ko' ? 'ko-KR' : 'en-US', o).format(d); } catch (e) { return d.toISOString().slice(0, 16).replace('T', ' '); }
  };
  const times = (lang) => document.querySelectorAll('time[data-ts]').forEach((el) => {
    const t = +el.dataset.ts; if (!t) return;
    el.textContent = fmt(t, lang, el.dataset.f);
    if (!el.title) el.title = new Date(t * 1000).toISOString().replace('.000', '');
  });
  const lang = () => (window.DFI ? DFI.lang() : document.documentElement.lang);
  times(lang());
  if (window.DFI) DFI.onLang(times);
  document.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-copy]'); if (!b) return;
    const url = location.href.split('#')[0], title = document.title;
    if (navigator.share && matchMedia('(pointer: coarse)').matches) { try { await navigator.share({ title, url }); return; } catch (x) { if (x && x.name === 'AbortError') return; } }
    try { await navigator.clipboard.writeText(url); b.classList.add('done'); setTimeout(() => b.classList.remove('done'), 1800); } catch (x) { prompt('', url); }
  });
})();
