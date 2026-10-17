/* Progressive enhancement: the complete combined archive works without JS. */
(function () {
  'use strict';
  const dataNode = document.getElementById('combined-archive-data');
  if (!dataNode) return;
  const main = dataNode.closest('main');
  const controls = main.querySelector('.archive-filters');
  const status = main.querySelector('.archive-result-count');
  const listing = main.querySelector('.post-list, .home-door-grid');
  if (!controls || !status || !listing) return;
  let data;
  try { data = JSON.parse(dataNode.textContent); } catch (_) { return; }
  const equestrian = new Set(data.equestrian);
  const rows = Array.from(listing.children).filter(row => row.matches('article'));
  const buttons = Array.from(controls.querySelectorAll('[data-archive-filter]'));
  const topics = new Set(['all', 'hunting', 'equestrian']);
  function topicFor(row) {
    const link = row.querySelector('h2 a, h3 a');
    const match = link && decodeURIComponent(link.getAttribute('href')).match(/posts\/([^/]+)/);
    return match && equestrian.has(match[1]) ? 'equestrian' : 'hunting';
  }
  function selectedTopic() {
    const hash = window.location.hash.slice(1);
    return topics.has(hash) ? hash : 'all';
  }
  function apply(topic) {
    let count = 0;
    rows.forEach(row => {
      const visible = topic === 'all' || topicFor(row) === topic;
      row.hidden = !visible;
      if (visible) count += 1;
    });
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.archiveFilter === topic)));
    status.textContent = count + ' ' + data.countLabel;
  }
  controls.hidden = false;
  status.hidden = false;
  controls.addEventListener('click', function (event) {
    const button = event.target.closest('[data-archive-filter]');
    if (!button || !controls.contains(button)) return;
    const topic = button.dataset.archiveFilter;
    if (!topics.has(topic)) return;
    // Replace the hash without scrolling away from the keyboard focus.
    window.history.replaceState(null, '', window.location.pathname + window.location.search + (topic === 'all' ? '' : '#' + topic));
    apply(topic);
  });
  window.addEventListener('hashchange', () => apply(selectedTopic()));
  apply(selectedTopic());
}());
