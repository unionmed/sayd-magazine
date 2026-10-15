document.querySelectorAll(".article-share").forEach((bar) => {
  let url = document.querySelector('link[rel="canonical"]')?.href || location.href;
  const title = document.querySelector('meta[property="og:title"]')?.content || document.title;
  // Fetch once on page load; clicks keep their native user activation.
  const script = [...document.scripts].find(s => s.src.includes('/assets/js/article-share.js'));
  if (script) {
    const manifestURL = new URL('../../s/links.json', script.src);
    fetch(manifestURL).then(r => { if (!r.ok) throw new Error('links unavailable'); return r.json(); })
      .then(links => {
        const key = decodeURIComponent(new URL(url).pathname).replace(/index\.html$/, '');
        const short = links[key];
        if (!/^\/s\/[a-z0-9-]+\/$/.test(short || '')) return;
        url = new URL(short, manifestURL.origin).href;
        for (const a of bar.querySelectorAll('a')) {
          const target = new URL(a.href);
          const parameter = target.hostname === 'wa.me' ? 'text'
            : target.hostname.includes('facebook.com') ? 'u' : 'url';
          target.searchParams.set(parameter, url);
          a.href = target.href;
        }
      }).catch(() => {}); // Keep the working canonical links on failure.
  }
  const share = bar.querySelector("[data-share-native]");
  const status = bar.querySelector(".article-share-status");

  share?.addEventListener("click", async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title, url });
        return;
      } catch (error) {
        if (error.name === "AbortError") return;
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      status.textContent = bar.dataset.copied;
      window.setTimeout(() => { status.textContent = ""; }, 3000);
    } catch {
      window.prompt(share.getAttribute("aria-label"), url);
    }
  });
});


// Record clicks on existing related-reading links without intercepting navigation.
// GA4 is already configured by each article. No cookies, URLs with query strings,
// or visitor identifiers are collected by this additional event.
document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;
  const link = target.closest("a[href]");
  if (!link) return;
  const section = link.closest(".article-more, .editorial-background");
  if (!section || typeof window.gtag !== "function") return;
  let destination;
  try {
    destination = new URL(link.href, location.href);
  } catch {
    return;
  }
  if (destination.origin !== location.origin) return;
  if (!/^\/(?:en\/|fr\/)?posts\//.test(destination.pathname)) return;
  window.gtag("event", "sayd_read_next_click", {
    link_type: section.classList.contains("article-more") ? "reading_card" : "editorial_context",
    source_path: location.pathname,
    destination_path: destination.pathname
  });
});
