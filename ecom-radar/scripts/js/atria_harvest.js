(function(){
if(window.__AT&&window.__AT.running) return 'gia in corso';
var H=window.__AT={running:true,done:false,ids:{},giri:0};
function dom(el){var e=el;for(var k=0;k<7&&e;k++){e=e.parentElement;if(!e)break;
  // fuori dalla card (contiene le anteprime di altre ad): ci si ferma, niente dominio indovinato
  var altri=new Set([...e.querySelectorAll('img,video')].map(x=>((x.src||'')+(x.poster||'')).match(/adfiles\/(m\d+)_/)).filter(Boolean).map(m=>m[1]));if(altri.size>1)return '';
  var t=e.innerText||'';if(t.length>3000)return '';var r=t.split('\n').map(x=>x.trim()).find(x=>/^(www\.)?[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$/i.test(x));if(r)return r.toLowerCase()}return ''}
function leggi(){document.querySelectorAll('img,video,source').forEach(e=>{var s=(e.src||'')+' '+(e.poster||'');var re=/adfiles\/(m\d+)_/g,m;while(m=re.exec(s)){if(!H.ids[m[1]])H.ids[m[1]]=dom(e)||1}})}
var fermo=0,prima=0;
(async function(){
  while(fermo<12&&H.giri<900){
    leggi();var n=Object.keys(H.ids).length;
    if(n===0){if(H.giri>8||/no results found/i.test(document.body.innerText))fermo=99}else if(n===prima)fermo++;else{fermo=0;prima=n}
    window.scrollTo(0,document.body.scrollHeight);document.querySelectorAll('*').forEach(e=>{if(e.scrollHeight>e.clientHeight+200&&e.clientHeight>300)e.scrollTop=e.scrollHeight});
    H.giri++;await new Promise(r=>setTimeout(r,2000));
  }
  leggi();H.running=false;H.done=true;
})();return 'partito';})()
