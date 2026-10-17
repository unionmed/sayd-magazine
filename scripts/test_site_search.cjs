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
