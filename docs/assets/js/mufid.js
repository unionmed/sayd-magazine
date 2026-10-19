/* Internal pilot. No cookies, storage, URL questions, analytics or persistent history. */
(()=>{
'use strict';
const $=id=>document.getElementById(id), main=document.querySelector('[data-mufid-language]');if(!main)return;
const c=JSON.parse($('mufid-copy').textContent),lang=main.dataset.mufidLanguage;
let mode='search',endpoint='',token='',revision=0,controller;
const status=$('mufid-status'),answer=$('mufid-answer'),results=$('mufid-results'),sources=$('mufid-sources');
function node(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;}
function clearOutput(){answer.textContent='';answer.hidden=true;results.replaceChildren();sources.replaceChildren();}
function safe(value,local=false){try{const u=new URL(value,location.origin);if(local){if(u.origin!==location.origin || !/^\/(?:en\/|fr\/)?posts\/[^/]+\/$/.test(u.pathname) || u.search || u.hash)return null;}else if(u.protocol!=='https:' || u.username || u.password)return null;return u.href;}catch{return null;}}
function render(data){
 if(data.answer){answer.textContent=data.answer;answer.hidden=false;}
 if(data.sources?.length){sources.append(node('h2',c.sources));const list=node('ol');for(const s of data.sources){const url=safe(s.url);if(!url)continue;const li=node('li'),a=node('a',s.title);a.href=url;a.target='_blank';a.rel='noopener noreferrer';li.append(a);list.append(li);}sources.append(list);}
 if(data.verified && data.checked_at)sources.append(node('p',c.checked+': '+data.checked_at));
 if(data.articles?.length){results.append(node('h2',c.articles));data.articles.forEach((a,i)=>{const url=safe(a.url,true);if(!url)return;const row=node('article');row.className='mufid-result';
 if(typeof a.image==='string' && a.image.startsWith('/media/') && !a.image.includes('\\')){const img=node('img');img.src=a.image;img.alt='';img.loading='lazy';img.addEventListener('error',()=>img.remove(),{once:true});row.append(img);}
 const body=node('div'),h=node('h3'),link=node('a',`[${i+1}] ${a.title}`);link.href=url;h.append(link);body.append(h,node('p',[a.date,a.category].filter(Boolean).join(' · ')),node('p',a.excerpt));row.append(body);results.append(row);});}
}
function reset(){revision++;controller?.abort();clearOutput();$('mufid-query').value='';$('mufid-consent').checked=false;status.textContent=c.ready;$('mufid-form').removeAttribute('aria-busy');$('mufid-form').querySelector('[type=submit]').disabled=false;}
document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>{reset();mode=b.dataset.mode;document.querySelectorAll('[data-mode]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));$('mufid-consent-row').hidden=mode!=='suggest';$('mufid-fresh').disabled=['search','suggest','verify'].includes(mode);$('mufid-query').focus();}));
$('mufid-connect').addEventListener('click',()=>{
 try{const u=new URL($('mufid-endpoint').value);if((u.protocol!=='https:' && !(u.protocol==='http:' && ['localhost','127.0.0.1'].includes(u.hostname))) || u.username || u.password || u.search || u.hash)throw new Error();reset();endpoint=u.origin;token=$('mufid-token').value;$('mufid-token').value='';status.textContent=c.ready;}catch{status.textContent=c.error;}
});
$('mufid-clear').addEventListener('click',()=>{reset();token='';endpoint='';$('mufid-token').value='';$('mufid-endpoint').value='';});
$('mufid-form').addEventListener('submit',async e=>{
 e.preventDefault();if(!endpoint || !token){status.textContent=c.unavailable;return;}
 if(mode==='suggest' && !$('mufid-consent').checked){status.textContent=c.consent_required;return;}
 const id=++revision;controller?.abort();controller=new AbortController();clearOutput();status.textContent=c.loading;
 const button=e.target.querySelector('[type=submit]');button.disabled=true;e.target.setAttribute('aria-busy','true');
 try{const r=await fetch(endpoint+(mode==='suggest'?'/v1/suggestions':'/v1/ask'),{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},body:JSON.stringify({lang,mode,query:$('mufid-query').value,fresh:$('mufid-fresh').checked,consent:$('mufid-consent').checked}),credentials:'omit',referrerPolicy:'no-referrer',signal:controller.signal});
 const data=await r.json();if(id!==revision)return;render(data);status.textContent=r.ok?(data.received?c.received:(data.articles?.length || data.answer?'':c.none)):(c[data.error] || c.error);
 }catch{if(id===revision)status.textContent=c.error;}finally{if(id===revision){button.disabled=false;e.target.removeAttribute('aria-busy');}}
});
$('mufid-fresh').disabled=true;
})();
