const assert = require('node:assert/strict');
const {normalize, prepare, search} = require('../assets/js/site-search.js');
assert.equal(normalize('أَبُو ـ إبرَاهيم آى'), normalize('ابو ابراهيم اي'));
assert.equal(normalize('ÉQUItation'), 'equitation');
const rows = [
 {title:'Body match',body:'Phoenicurus phoenicurus migration',keywords:'',url:'/posts/body/',date:'2026-01-01',category:'Birds'},
 {title:'Phoenicurus phoenicurus',body:'A bird',keywords:'',url:'/posts/title/',date:'2020-01-01',category:'Birds'},
 {title:'Other bird',body:'migration',keywords:'Phoenicurus phoenicurus',url:'/posts/keywords/',date:'2025-01-01',category:'Birds'},
].map(prepare);
assert.deepEqual(search(rows,'Phoenicurus phoenicurus',{}).map(a=>a.url),['/posts/title/','/posts/keywords/','/posts/body/']);
assert.equal(search(rows,'phoenicurus migration',{}).length,2);
assert.equal(search(rows,'phoenicurus',{year:'2020'})[0].title,'Phoenicurus phoenicurus');
assert.equal(search(rows,'bird',{category:'Missing'}).length,0);
assert.equal(search(rows,'',{}).length,0);
assert.equal(search(rows,'!!!',{}).length,0);
assert.equal(search(rows,'<img src=x onerror=alert(1)>',{}).length,0);
assert.equal(search(rows,'no-such-word',{}).length,0);
console.log('Search ranking, normalization, AND keywords, scientific names, filters and hostile input: PASS');
// Facets are independent: one interview retains its subject and year filters.
const facets = [
 {title:'Alexandra CABS',body:'bird protection',keywords:'',url:'/posts/alex/',date:'2026-10-11',categories:['Hunting & Equestrian','Interviews']},
 {title:'Older interview',body:'bird hunting',keywords:'',url:'/posts/old/',date:'2024-09-10',categories:['Hunting & Equestrian','Interviews']},
 {title:'Marine fish',body:'fish',keywords:'',url:'/posts/fish/',date:'2026-01-01',categories:['Hunting & Equestrian']},
].map(prepare);
assert.equal(search(facets,'',{category:'Interviews'}).length,2);
assert.equal(search(facets,'',{category:'Interviews',year:'2026'}).length,1);
assert.equal(search(facets,'bird',{category:'Interviews'}).length,2);
assert.equal(search(facets,'',{category:'Hunting & Equestrian'}).length,3);
assert.equal(search(facets,'',{category:'Hunting & Equestrian · Interviews'}).length,0);
const fs = require('node:fs');
for (const [lang,label,total] of [['ar','مقابلات',70],['en','Interviews',2],['fr','Entretiens',2]]) {
 const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../docs/assets/search/index-'+lang+'.json')));
 const rows=data.articles.map(prepare);
 assert.equal(data.version,2);
 assert.equal(search(rows,'',{category:label}).length,total);
 assert.equal(search(rows,'CABS',{category:label,year:'2026'}).length,2);
 assert.equal(data.categories.length,11);
 assert(data.categories.every(value=>!value.includes(' · ')));
}
console.log('Canonical multi-facets, topic+interview membership, year and all language corpora: PASS');
