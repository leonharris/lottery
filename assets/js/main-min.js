!function(){"use strict";var t=document.getElementById("lotto"),e=document.getElementById("btn_spin_lotto"),n=!!document.getElementById("sort-toggle-switch").checked;document.getElementById("sort-toggle-switch").addEventListener("change",(function(){n=!!this.checked}));var o=document.getElementById("draw-type-toggle-switch").checked?"euromillions":"lotto";function c(){if(document.getElementsByClassName("ball").length){document.querySelectorAll(".ball").forEach((function(t){return t.remove()}))}}function a(e,n,o){for(var c=[];c.length<e;){var a=Math.floor(Math.random()*n)+1;-1===c.indexOf(a)&&c.push(a);for(var r=0;r<n;r++)c[r]}1==o?[].concat(c).sort((function(t,e){return t-e})).forEach((function(e){var n=document.createElement("div"),o=document.createElement("span"),c="range-"+Math.ceil(e/10+.01);n.setAttribute("class","ball"),n.setAttribute("data-range",c),o.setAttribute("class","number"),o.textContent=e,n.append(o),t.append(n)})):c.forEach((function(e){var n=document.createElement("div"),o=document.createElement("span"),c="range-"+Math.ceil(e/10+.01);n.setAttribute("class","ball"),n.setAttribute("data-range",c),o.setAttribute("class","number"),o.textContent=e,n.append(o),t.append(n)}))}document.getElementById("draw-type-toggle-switch").addEventListener("change",(function(){c(),o=this.checked?"euromillions":"lotto",t.setAttribute("data-draw-type",o)})),e.addEventListener("click",(function(t){c(),"lotto"==o?a(6,59,n):(a(5,50,n),a(2,12,n))}))}();