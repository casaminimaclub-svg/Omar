// Raccoglitore per l'Ad Library aperta nel Chrome dell'utente: aggancia le risposte GraphQL, scorre fino
// in fondo e salva tutto come download er_<pagina>_<stato>.json (lo legge scripts/chrome_ingest.py).
window.__ER = {gql: [], done: false, msg: 'avvio'};
(() => {
  const oo = XMLHttpRequest.prototype.open, os_ = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(m, u){ this.__u = u; return oo.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function(){ this.addEventListener('load', () => { try { if (String(this.__u||'').includes('graphql') && this.responseText.includes('search_results_connection')) __ER.gql.push(this.responseText); } catch(e){} }); return os_.apply(this, arguments); };
})();
(async () => {
  for (let k = 0; k < 20 && !/(risultati|results)/.test(document.body.innerText); k++) await new Promise(r => setTimeout(r, 500));
  const m = document.body.innerText.match(/~?([\d.,]+) (risultati|results)/); const declared = m ? parseInt(m[1].replace(/[.,]/g,'')) : 0;
  const cnt = () => (document.body.innerText.match(/(ID libreria|Library ID): ?\d+/g)||[]).length;
  let last = 0, still = 0;
  for (let i = 0; i < 3000; i++) {
    if (declared && cnt() >= declared) break;
    window.scrollTo(0, document.body.scrollHeight); await new Promise(r => setTimeout(r, 1500));
    const n = cnt(); __ER.msg = n + '/' + declared;
    if (n === last) { if (++still >= 7) break; } else { still = 0; last = n; }
  }
  const h = document.documentElement.outerHTML; const i = h.indexOf('search_results_connection');
  const a = h.lastIndexOf('<script', i), b = h.indexOf('</script>', i);
  const u = new URL(location.href); const pid = u.searchParams.get('view_all_page_id'); const active = u.searchParams.get('active_status') || 'active';
  const blob = new Blob([JSON.stringify({page_id: pid, active, declared, html: (i>0&&a>0&&b>0) ? h.slice(a, b+9) : '', gql: __ER.gql})], {type: 'application/json'});
  const el = document.createElement('a'); el.href = URL.createObjectURL(blob); el.download = `er_${pid}_${active}.json`; document.body.appendChild(el); el.click(); el.remove();
  __ER.msg = cnt() + '/' + declared + ' salvato'; __ER.done = true;
})();
'avviato';
