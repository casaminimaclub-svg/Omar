(function(){var c=[...document.querySelectorAll('a[href*="facebook.com"]')].filter(a=>/posts|permalink|videos|\/p\//.test(a.href));
var card=null,e=c[0];for(var i=0;i<10&&e;i++){e=e.parentElement;if(e&&e.innerText&&e.innerText.indexOf('Comments')>0){card=e;break}}
return JSON.stringify({n:c.length,href:c[0]&&c[0].href,loc:location.href.slice(0,80),tag:card&&(card.tagName+'.'+card.className),html:card&&card.outerHTML.slice(0,2500)})})()
