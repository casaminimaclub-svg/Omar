(function(){window.__cap=[];var f=window.fetch;window.fetch=function(u,i){try{var s=String(u&&u.url||u);if(/ads\/search/.test(s))window.__cap.push({u:s,b:i&&String(i.body).slice(0,3000)})}catch(e){};return f.apply(this,arguments)};
var o=XMLHttpRequest.prototype.open,se=XMLHttpRequest.prototype.send;XMLHttpRequest.prototype.open=function(m,u){this.__u=u;return o.apply(this,arguments)};XMLHttpRequest.prototype.send=function(b){if(/ads\/search/.test(this.__u||''))window.__cap.push({x:this.__u,b:String(b).slice(0,3000)});return se.apply(this,arguments)};
var el=[...document.querySelectorAll('span,div,button')].find(e=>e.children.length<3&&/^Status/.test(e.innerText||''));
if(el){el.click();return 'clicked '+el.tagName}return 'no el'})()
