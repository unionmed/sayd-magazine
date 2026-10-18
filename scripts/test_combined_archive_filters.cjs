#!/usr/bin/env node
/* Execute the real progressive-enhancement script with a small explicit DOM.
   Functional state coverage only; this does not claim rendered browser QA. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const code = fs.readFileSync(path.join(__dirname, '../assets/js/combined-archive.js'), 'utf8');

function fixture(hash = '', invalidData = false, withMarine = false) {
  const buttons = (withMarine ? ['all', 'hunting', 'marine', 'equestrian'] : ['all', 'hunting', 'equestrian']).map(topic => ({
    dataset: {archiveFilter: topic},
    attributes: {'aria-pressed': String(topic === 'all')},
    setAttribute(name, value) { this.attributes[name] = value; },
    closest() { return this; }
  }));
  const makeRow = slug => ({
    slug, hidden: false,
    matches(selector) { return selector === 'article'; },
    querySelector() { return {getAttribute() { return '../../posts/' + encodeURIComponent(slug) + '/index.html'; }}; }
  });
  const rows = [makeRow('hunting-one'), makeRow('فروسية-اختبار'), makeRow('hunting-two')];
  if (withMarine) rows.push(makeRow('marine-only'), makeRow('land-and-marine'));
  const events = {}, windowEvents = {};
  const controls = {
    hidden: true,
    querySelectorAll() { return buttons; },
    addEventListener(name, fn) { events[name] = fn; },
    contains(node) { return buttons.includes(node); }
  };
  const status = {hidden: true, textContent: ''};
  const main = {querySelector(selector) {
    return selector === '.archive-filters' ? controls : selector === '.archive-result-count' ? status : {children: rows};
  }};
  const dataNode = {
    textContent: invalidData ? '{broken' : JSON.stringify({equestrian:['فروسية-اختبار'], marine:withMarine ? ['marine-only','land-and-marine'] : [], landMarine:withMarine ? ['land-and-marine'] : [], countLabel:'stories'}),
    closest() { return main; }
  };
  const window = {
    location: {pathname:'/en/category/hunting/', search:'?source=test', hash},
    history: {replaceState(_data, _title, url) {
      const parsed = new URL(url, 'https://example.test');
      window.location = {pathname:parsed.pathname, search:parsed.search, hash:parsed.hash};
    }},
    addEventListener(name, fn) { windowEvents[name] = fn; }
  };
  vm.runInNewContext(code, {window, document:{getElementById() { return dataNode; }}, Set, Array, JSON, String, decodeURIComponent});
  return {
    rows, buttons, controls, status, window,
    click(topic) { events.click({target:buttons.find(b => b.dataset.archiveFilter === topic)}); },
    changeHash(value) { window.location.hash = value; windowEvents.hashchange(); }
  };
}

function state(view, visible, selected) {
  assert.deepEqual(view.rows.filter(row => !row.hidden).map(row => row.slug), visible);
  assert.equal(view.status.textContent, visible.length + ' stories');
  assert.equal(view.controls.hidden, false);
  assert.equal(view.status.hidden, false);
  view.buttons.forEach(button => assert.equal(button.attributes['aria-pressed'], String(button.dataset.archiveFilter === selected)));
}

const all = ['hunting-one', 'فروسية-اختبار', 'hunting-two'];
const hunting = ['hunting-one', 'hunting-two'];
let view = fixture();
state(view, all, 'all');
view.click('equestrian');
state(view, ['فروسية-اختبار'], 'equestrian');
assert.equal(view.window.location.hash, '#equestrian');
view.click('equestrian');
state(view, ['فروسية-اختبار'], 'equestrian');
view.click('hunting');
state(view, hunting, 'hunting');
view.click('all');
state(view, all, 'all');
assert.equal(view.window.location.hash, '');
assert.equal(view.window.location.search, '?source=test');
assert.equal(view.window.location.pathname, '/en/category/hunting/');

view = fixture('#equestrian');
state(view, ['فروسية-اختبار'], 'equestrian');
view.changeHash('#hunting');
state(view, hunting, 'hunting');
view.changeHash(''); // Browser back/hash restoration returns to All.
state(view, all, 'all');
view.changeHash('#unrelated-anchor');
state(view, all, 'all');
view = fixture('#hunting');
state(view, hunting, 'hunting');
view = fixture('#unknown');
state(view, all, 'all');
view = fixture('', true);
assert.equal(view.controls.hidden, true);
assert.equal(view.status.hidden, true);
assert.deepEqual(view.rows.filter(row => !row.hidden).map(row => row.slug), all);
console.log('PASS: real filter JS covers default All, topic selection, repeat clicks, URL init/hash restoration, aria state and graceful no-data fallback.');

view = fixture('', false, true);
state(view, [...all,'marine-only','land-and-marine'], 'all');
view.click('marine'); state(view,['marine-only','land-and-marine'],'marine');
view.click('marine'); state(view,['marine-only','land-and-marine'],'marine');
view.click('hunting'); state(view,[...hunting,'land-and-marine'],'hunting');
view.changeHash('#marine'); state(view,['marine-only','land-and-marine'],'marine');
view = fixture('#marine'); state(view,all,'all');
console.log('PASS: marine facet, mixed land/sea overlap, single All card, no empty-language facet.');
