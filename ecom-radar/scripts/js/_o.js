JSON.stringify([...document.querySelectorAll("[role=option],li,label")].map(e=>e.innerText.trim()).filter(t=>t&&t.length<25).slice(0,15))
