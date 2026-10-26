// A search citation is a lead, not proof of a current legal decision.
import {normalize} from './core.mjs';
export async function verifyLegalNotice(legal,network=fetch,now=new Date()){
 if(!legal||legal.status==='unconfirmed')return false;
 let url;try{url=new URL(legal.source_url);}catch{return false;}
 if(url.protocol!=='https:'||url.username||url.password||url.port||!['moe.gov.lb','www.moe.gov.lb'].includes(url.hostname))return false;
 const year=now.getUTCFullYear();
 if(legal.season_start_year!==year||!/^\d{4}-\d{2}-\d{2}$/.test(legal.publication_date||'')||legal.publication_date>now.toISOString().slice(0,10))return false;
 const quote=normalize(legal.evidence_quote);
 if(quote.length<30||quote.length>900||!quote.includes(`${year} ${year+1}`))return false;
 if(legal.status==='open'&&(!/فتح|افتتاح/.test(quote)||/لم يصدر|لم يفتح|لا يوجد|عدم فتح|ممنوع|محظور/.test(quote)))return false;
 if(legal.status==='closed'&&!/ممنوع|منع|حظر|محظور/.test(quote))return false;
 try{
  const res=await network(url.href,{redirect:'error',signal:AbortSignal.timeout(8000)});
  if(!res.ok||!res.body||!/text\/html|text\/plain/i.test(res.headers.get('content-type')||''))return false;
  const reader=res.body.getReader(),chunks=[];let size=0;
  while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>350000){await reader.cancel();return false;}chunks.push(value);}
  const bytes=new Uint8Array(size);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}
  const html=new TextDecoder().decode(bytes);
  const text=html.replace(/<script\b[^>]*>[\s\S]*?<\/script>|<style\b[^>]*>[\s\S]*?<\/style>/gi,' ').replace(/<[^>]+>/g,' ').replace(/&nbsp;|&#160;/g,' ').replace(/&amp;/g,'&');
  if(!normalize(text).includes(quote))return false;
  const [y,m,d]=legal.publication_date.split('-');
  const months=['كانون الثاني','شباط','آذار','نيسان','أيار','حزيران','تموز','آب','أيلول','تشرين الأول','تشرين الثاني','كانون الأول'];
  const dates=[legal.publication_date,`${y} ${months[Number(m)-1]} ${Number(d)}`,`${Number(d)} ${months[Number(m)-1]} ${y}`];
  return dates.some(date=>normalize(text).includes(normalize(date)));
 }catch{return false;}
}

// Known stable geographic contradictions from the reviewed regional failures.
// This is not a current-access map and unknown places are NOT certified by it.
export function placeConflict(stop,input){
 const target=normalize(input.trip?.destination||'');
 const name=normalize(stop.name+' '+stop.locality),source=stop.source_url||'';
 if(/عكار|akkar/.test(target)&&/oakland|اوكلاند|حاصبيا|hasbaya|جاج|\bjaj\b/.test(name))return true;
 if(/طرابلس|الضنيه|tripoli|dinnieh|danniyeh/.test(target)&&!/الكوره|koura|اهدن|ehden|تنورين|tannourine/.test(target)&&(/talle koura|talle|الكوره|koura|اهدن|ehden|تنورين|tannourine/.test(name)||/horshehden\.org|tannourine/.test(source)))return true;
 return false;
}
