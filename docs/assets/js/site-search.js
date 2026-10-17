/* Local, dependency-free search. Never send queries or put them in URLs/storage. */
(function (root) {
  'use strict';
  function normalize(text) {
    return String(text || '').normalize('NFKD').toLowerCase()
      .replace(/[\u0300-\u036f\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]/g, '')
      .replace(/[أإآٱ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه')
      .replace(/[^\p{L}\p{N}]+/gu, ' ').trim().replace(/\s+/g, ' ');
  }
  function prepare(article) {
    return {article, title: normalize(article.title), body: normalize(article.body), keywords: normalize(article.keywords)};
  }
  function search(rows, query, filters) {
    const phrase = normalize(String(query).slice(0, 200));
    const words = [...new Set(phrase.split(' ').filter(Boolean))].slice(0, 20);
    if (!words.length) return [];
    return rows.map(row => {
      const a = row.article;
      if ((filters.year && !a.date.startsWith(filters.year + '-')) || (filters.category && a.category !== filters.category)) return null;
      let score = row.title === phrase ? 100 : (row.title.includes(phrase) ? 35 : 0);
      for (const word of words) {
        if (row.title.includes(word)) score += 12;
        else if (row.keywords.includes(word)) score += 6;
        else if (row.body.includes(word)) score += 1;
        else return null;
      }
      return {article: a, score};
    }).filter(Boolean).sort((a,b) => b.score-a.score || b.article.date.localeCompare(a.article.date) || a.article.url.localeCompare(b.article.url)).map(row => row.article);
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {normalize, prepare, search};
  if (!root.document) return;
  const doc = root.document;
  const main = doc.querySelector('[data-search-language]');
  if (!main) return;
  const copy = JSON.parse(doc.getElementById('search-copy').textContent);
  const form = doc.getElementById('site-search-form');
  const query = doc.getElementById('search-query');
  const language = doc.getElementById('search-language');
  const year = doc.getElementById('search-year');
  const category = doc.getElementById('search-category');
  const status = doc.getElementById('search-status');
  const results = doc.getElementById('search-results');
  const more = doc.getElementById('search-more');
  const cache = new Map();
  const script = Array.from(doc.scripts).find(s => /\/site-search\.js(?:\?|$)/.test(s.src));
  const assetRoot = new URL('../search/', script.src);
  let active = 0, rows = [], matches = [], shown = 0, loadedLanguage = '';
  function element(tag, text, className) {
    const node = doc.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function localURL(value, image) {
    if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//')) return null;
    const url = new URL(value, root.location.origin);
    if (url.origin !== root.location.origin || url.search || url.hash) return null;
    if (image ? !url.pathname.startsWith('/media/') : !/^\/(?:en\/|fr\/)?posts\/[^/]+\/(?:index\.html)?$/.test(url.pathname)) return null;
    return url.href;
  }
  function appendPage() {
    const batch = doc.createDocumentFragment();
    matches.slice(shown, shown + 20).forEach(a => {
      const url = localURL(a.url, false);
      if (!url) return;
      const card = element('article', undefined, 'search-result');
      card.lang = language.value;
      card.dir = language.value === 'ar' ? 'rtl' : 'ltr';
      const imageURL = localURL(a.image, true);
      if (imageURL) {
        const image = element('img'); image.src = imageURL; image.alt = ''; image.loading = 'lazy'; image.width = 150; image.height = 105;
        image.addEventListener('error', () => image.remove(), {once:true});
        card.append(image);
      }
      const body = element('div'); const heading = element('h2'); const link = element('a', a.title); link.href = url;
      heading.append(link); body.append(heading);
      const meta = element('p', undefined, 'search-result-meta');
      if (a.date) { const time = element('time', a.date); time.dateTime = a.date; meta.append(time); }
      if (a.category) meta.append(doc.createTextNode((a.date ? ' · ' : '') + a.category));
      body.append(meta, element('p', a.excerpt)); card.append(body); batch.append(card);
    });
    results.append(batch); shown = Math.min(shown + 20, matches.length); more.hidden = shown >= matches.length;
  }
  function render() {
    results.replaceChildren(); shown = 0; more.hidden = true;
    if (!normalize(query.value)) { status.textContent = copy.empty; return; }
    matches = search(rows, query.value, {year:year.value, category:category.value});
    status.textContent = matches.length ? matches.length + ' ' + copy.results : copy.none;
    appendPage();
  }
  function fill(select, values) {
    select.replaceChildren(new Option(copy.all, ''));
    values.forEach(value => select.add(new Option(value, value)));
  }
  async function load() {
    const revision = ++active, lang = language.value;
    status.textContent = copy.loading; results.replaceChildren(); more.hidden = true;
    form.setAttribute('aria-busy', 'true');
    try {
      if (!cache.has(lang)) {
        const promise = fetch(new URL('index-' + lang + '.json', assetRoot), {credentials:'omit', referrerPolicy:'no-referrer'})
          .then(response => { if (!response.ok) throw new Error('index'); return response.json(); })
          .then(data => { if (data.version !== 1 || data.lang !== lang || !Array.isArray(data.articles)) throw new Error('format'); return data.articles.map(prepare); });
        cache.set(lang, promise);
        promise.catch(() => cache.delete(lang));
      }
      const loaded = await cache.get(lang);
      if (revision !== active) return;
      rows = loaded;
      if (loadedLanguage !== lang) {
        fill(year, [...new Set(rows.map(row => row.article.date.slice(0,4)).filter(Boolean))].sort().reverse());
        fill(category, [...new Set(rows.map(row => row.article.category).filter(Boolean))].sort((a,b)=>a.localeCompare(b,lang)));
        loadedLanguage = lang;
      }
      render();
    } catch (_) {
      if (revision === active) { rows = []; status.textContent = copy.error; }
    } finally { if (revision === active) form.removeAttribute('aria-busy'); }
  }
  form.addEventListener('submit', event => { event.preventDefault(); load(); });
  language.addEventListener('change', load);
  year.addEventListener('change', render); category.addEventListener('change', render);
  query.addEventListener('input', () => { if (!query.value) render(); });
  more.addEventListener('click', appendPage);
  load();
}(typeof window === 'undefined' ? globalThis : window));
