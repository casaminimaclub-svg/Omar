(function(){
if(window.__HV&&window.__HV.running) return 'gia in corso';
var H=window.__HV={running:true,done:false,cards:{},giri:0};
function num(s){s=(s||'').replace(/[^\d]/g,'');return s?parseInt(s):null}
function leggi(b){
  var fb=[...b.querySelectorAll('a[href*="facebook.com"],a[href*="instagram.com"]')].map(a=>a.href).find(h=>/posts|permalink|videos|\/p\/|story_fbid|reel/.test(h));
  var idA=b.querySelector('a[href^="/ads/"]'); var id=idA?idA.getAttribute('href').split('/').pop():null;
  var key=id||fb; if(!key) return;
  var t=b.innerText||'';
  var date=[...b.querySelectorAll('.ad-date span')].map(s=>s.innerText.replace(/\s+/g,' '));
  var body=[...b.querySelectorAll('div')].find(d=>(d.getAttribute('style')||'').indexOf('overflow-wrap')>=0);
  var media=[];b.querySelectorAll('video').forEach(v=>{if(v.poster)media.push(['poster',v.poster]);v.querySelectorAll('source').forEach(s=>media.push(['video',s.src]))});
  b.querySelectorAll('img').forEach(i=>{if(/content\.adspy\.com/.test(i.src)&&!(i.getAttribute('style')||'').match(/width:\s*40px/))media.push(['img',i.src])});
  var tds=b.querySelectorAll('.bottom-table td');
  var paesi=tds.length?[...tds[tds.length-1].querySelectorAll('span')].map(s=>s.innerText.replace(/,\s*$/,'').trim()).filter(Boolean):[];
  var likeEl=b.querySelector('.bottom-table .line');
  var avatar=b.querySelector('img[style*="40px"]');
  var pageA=b.querySelector('a.default-anchor');
  // testo fra media e tabella in fondo: titolo, dominio, CTA
  var dopo=''; var bt=b.querySelector('.bottom-table'); if(bt){var prev=bt.previousElementSibling; if(prev) dopo=prev.innerText||''}
  var shm=t.match(/([\d,]+)\s+Shares/), cm=t.match(/([\d,]+)\s+Comments/);
  H.cards[key]={adspy_id:id,post_url:fb||null,page_name:pageA?pageA.innerText.trim():null,user:pageA?pageA.getAttribute('href'):null,
    avatar:avatar?avatar.src:null,created:date[0]||null,last_seen:date[1]||null,body:body?body.innerText:null,media:media,
    likes:likeEl?num(likeEl.innerText):null,comments:cm?num(cm[1]):null,shares:shm?num(shm[1]):null,countries:paesi,tail:dopo.slice(0,400),text:t.slice(0,6000),links:[...b.querySelectorAll('a[href^="http"]')].map(a=>a.href).filter(h=>!/facebook\.com|instagram\.com|adspy\.com/.test(h)).slice(0,5)};
}
var fermo=0,prima=0;
(async function(){
  while(fermo<5 && H.giri<400){
    document.querySelectorAll('.ad-outer-box').forEach(leggi);
    var n=Object.keys(H.cards).length; if(n===0){ if(H.giri>40 || /no ads found|no results/i.test(document.body.innerText)) fermo=99; } else if(n===prima) fermo++; else {fermo=0;prima=n}
    window.scrollTo(0,document.body.scrollHeight); H.giri++;
    await new Promise(r=>setTimeout(r,1000));
  }
  document.querySelectorAll('.ad-outer-box').forEach(leggi);
  H.running=false; H.done=true;
})();
return 'partito';
})()
