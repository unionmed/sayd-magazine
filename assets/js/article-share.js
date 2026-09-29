document.querySelectorAll(".article-share").forEach((bar) => {
  const url = document.querySelector('link[rel="canonical"]')?.href || location.href;
  const title = document.querySelector('meta[property="og:title"]')?.content || document.title;
  const copy = bar.querySelector("[data-share-copy]");
  const native = bar.querySelector("[data-share-native]");
  const status = bar.querySelector(".article-share-status");

  copy?.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(url);
      status.textContent = bar.dataset.copied;
      window.setTimeout(() => { status.textContent = ""; }, 3000);
    } catch {
      // Some browsers require a secure context for clipboard access.
      window.prompt(copy.dataset.defaultLabel, url);
    }
  });

  if (native && navigator.share) {
    native.hidden = false;
    native.addEventListener("click", async () => {
      try {
        await navigator.share({ title, url });
      } catch (error) {
        if (error.name !== "AbortError") status.textContent = error.message;
      }
    });
  }
});
