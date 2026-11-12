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
    if (!words.length && !filters.year && !filters.category) return [];
    return rows.map(row => {
      const a = row.article;
      if ((filters.year && !a.date.startsWith(filters.year + '-')) || (filters.category && !(a.categories || [a.category]).includes(filters.category))) return null;
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
  function strictJSON(text) {
    let position = 0;
    function space() { while (/[\t\n\r ]/.test(text[position] || '!')) position++; }
    function string() {
      const start = position++;
      for (;;) {
        if (position >= text.length) throw new Error('JSON string');
        const c = text[position++];
        if (c === '"') return JSON.parse(text.slice(start, position));
        if (c === '\\') position++;
      }
    }
    function value(depth) {
      if (depth > 32) throw new Error('JSON nesting');
      space(); const c = text[position];
      if (c === '"') { string(); return; }
      if (c === '{' || c === '[') {
        const object = c === '{', end = object ? '}' : ']', keys = new Set();
        position++; space();
        if (text[position] === end) { position++; return; }
        for (;;) {
          space();
          if (object) {
            if (text[position] !== '"') throw new Error('JSON key');
            const key = string();
            if (keys.has(key)) throw new Error('duplicate JSON key');
            keys.add(key); space();
            if (text[position++] !== ':') throw new Error('JSON colon');
          }
          value(depth + 1); space();
          const separator = text[position++];
          if (separator === end) return;
          if (separator !== ',') throw new Error('JSON separator');
        }
      }
      const token = /^(?:true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)/.exec(text.slice(position));
      if (!token) throw new Error('JSON value');
      position += token[0].length;
    }
    value(0); space();
    if (position !== text.length) throw new Error('JSON trailing content');
    return JSON.parse(text);
  }
  function exactKeys(value, names) {
    return value && typeof value === 'object' && !Array.isArray(value) &&
      Object.keys(value).sort().join(',') === names.slice().sort().join(',');
  }
  function validArticle(a, lang) {
    const fields = ['url','title','body','keywords','date','category','categories','image','excerpt'];
    if (!exactKeys(a, fields) || fields.filter(k => k !== 'categories').some(k => typeof a[k] !== 'string') ||
        !Array.isArray(a.categories) || a.categories.some(v => typeof v !== 'string')) return false;
    const prefix = lang === 'ar' ? '' : lang + '/';
    return new RegExp('^/' + prefix + 'posts/[^/?#]+/$').test(a.url);
  }
  async function boundedBytes(response, limit) {
    if (!response.body || !response.body.getReader) {
      const bytes = await response.arrayBuffer();
      if (bytes.byteLength > limit) throw new Error('response size');
      return bytes;
    }
    const reader = response.body.getReader(), chunks = [];
    let total = 0;
    try {
      for (;;) {
        const {done, value} = await reader.read();
        if (done) break;
        total += value.byteLength;
        if (total > limit) { await reader.cancel(); throw new Error('response size'); }
        chunks.push(value);
      }
    } finally { reader.releaseLock(); }
    const bytes = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    return bytes.buffer;
  }
  async function loadIndex(lang, assetRoot, fetcher = root.fetch.bind(root), crypto = root.crypto) {
    if (!['ar','en','fr'].includes(lang)) throw new Error('language');
    const options = {credentials:'omit', referrerPolicy:'no-referrer', redirect:'error'};
    const response = await fetcher(new URL('manifest-' + lang + '.json?v=3', assetRoot), {...options, cache:'no-cache'});
    if (!response.ok) throw new Error('manifest');
    const data = strictJSON(new TextDecoder('utf-8', {fatal:true}).decode(await boundedBytes(response, 512 * 1024)));
    if (!exactKeys(data, ['version','lang','categories','article_count','shards']) || data.version !== 3 || data.lang !== lang ||
        !Array.isArray(data.categories) || data.categories.some(v => typeof v !== 'string') ||
        !Number.isSafeInteger(data.article_count) || data.article_count < 0 || !Array.isArray(data.shards) || !data.shards.length || data.shards.length > 2048) throw new Error('format');
    const paths = new Set();
    let declared = 0;
    for (const shard of data.shards) {
      if (!exactKeys(shard, ['path','sha256','bytes','count']) || typeof shard.sha256 !== 'string' ||
          !/^[a-f0-9]{64}$/.test(shard.sha256) || shard.path !== 'shards/' + lang + '-' + shard.sha256 + '.json' ||
          !Number.isSafeInteger(shard.bytes) || shard.bytes <= 0 || shard.bytes > 512 * 1024 || !Number.isSafeInteger(shard.count) || shard.count < 0 || paths.has(shard.path)) throw new Error('shard descriptor');
      paths.add(shard.path); declared += shard.count;
    }
    if (!Number.isSafeInteger(declared) || declared !== data.article_count) throw new Error('article count');
    const parts = new Array(data.shards.length);
    let cursor = 0;
    async function worker() {
      while (cursor < data.shards.length) {
        const position = cursor++, shard = data.shards[position];
        const response = await fetcher(new URL(shard.path, assetRoot), options);
        if (!response.ok) throw new Error('shard');
        const bytes = await boundedBytes(response, shard.bytes);
        if (bytes.byteLength !== shard.bytes) throw new Error('shard size');
        const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('');
        if (digest !== shard.sha256) throw new Error('shard digest');
        const part = strictJSON(new TextDecoder('utf-8', {fatal:true}).decode(bytes));
        if (!exactKeys(part, ['version','lang','articles']) || part.version !== 3 || part.lang !== lang ||
            !Array.isArray(part.articles) || part.articles.length !== shard.count || part.articles.some(a => !validArticle(a, lang))) throw new Error('shard format');
        parts[position] = part.articles;
      }
    }
    await Promise.all(Array.from({length:Math.min(4, data.shards.length)}, worker));
    const articles = parts.flat(), urls = new Set(articles.map(a => a.url));
    if (articles.length !== data.article_count || urls.size !== articles.length) throw new Error('duplicate article');
    articles.sort((a,b) => a.url < b.url ? -1 : a.url > b.url ? 1 : 0);
    return {rows:articles.map(prepare), categories:data.categories};
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {normalize, prepare, search, loadIndex, strictJSON};
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
  let active = 0, rows = [], matches = [], shown = 0, loadedLanguage = '', ready = false;
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
    if (!ready) return;
    results.replaceChildren(); shown = 0; more.hidden = true;
    if (!normalize(query.value) && !year.value && !category.value) { status.textContent = copy.empty; return; }
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
    ready = false; rows = []; matches = [];
    status.textContent = copy.loading; results.replaceChildren(); more.hidden = true;
    form.setAttribute('aria-busy', 'true');
    try {
      if (!cache.has(lang)) {
        const promise = loadIndex(lang, assetRoot);
        cache.set(lang, promise);
        promise.catch(() => cache.delete(lang));
      }
      const loaded = await cache.get(lang);
      if (revision !== active) return;
      rows = loaded.rows; ready = true;
      if (loadedLanguage !== lang) {
        fill(year, [...new Set(rows.map(row => row.article.date.slice(0,4)).filter(Boolean))].sort().reverse());
        fill(category, loaded.categories);
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
