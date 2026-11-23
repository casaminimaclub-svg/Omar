JSON.stringify({imgs:[...document.images].filter(i=>/adfiles\/m\d+/.test(i.src)).length, at:window.__AT?{g:window.__AT.giri,r:window.__AT.running}:null})
